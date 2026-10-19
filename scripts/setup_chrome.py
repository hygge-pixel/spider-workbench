"""Install official Stable Chrome for Testing on Windows, without touching profiles."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlparse
from urllib.request import HTTPSHandler, HTTPRedirectHandler, build_opener
from urllib.error import URLError
import zipfile

METADATA = 'https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json'


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def installation_lock(root):
    path = Path(root) / 'runs/_deployment/install.lock'
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        stream = path.open('x', encoding='utf-8')
    except FileExistsError:
        raise ValueError('installation_lock_exists; review recorded PID before removing a stale lock') from None
    try:
        with stream:
            json.dump({'pid': os.getpid(), 'created_at': datetime.now(timezone.utc).isoformat()}, stream)
        yield
    finally:
        path.unlink(missing_ok=True)


class OfficialRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def validate_url(url):
    parsed = urlparse(url)
    if (parsed.scheme != 'https' or parsed.hostname not in {'googlechromelabs.github.io', 'storage.googleapis.com'}
            or parsed.username or parsed.password or parsed.port not in (None, 443) or parsed.query or parsed.fragment):
        raise ValueError('official_https_url_required')
    return url


class OfficialDownloadError(RuntimeError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def curl_fetch(url, validator=validate_url):
    """Use platform curl TLS/proxy support without redirects or insecure flags."""
    validator(url)
    curl = shutil.which('curl.exe' if os.name == 'nt' else 'curl')
    if not curl:
        raise OfficialDownloadError('official_download_failed_no_curl_fallback')
    stream = tempfile.TemporaryFile('w+b')
    try:
        result = subprocess.run([curl, '--silent', '--show-error', '--fail', '--proto', '=https',
                                 '--max-redirs', '0', '--connect-timeout', '20', '--max-time', '300',
                                 '--retry', '2', '--retry-delay', '1', '--write-out', '%{stderr}\nSTATUS:%{http_code}', url],
                                stdout=stream, stderr=subprocess.PIPE, timeout=950,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        diagnostic = result.stderr.decode('utf-8', errors='replace')
        if result.returncode or not diagnostic.rstrip().endswith('STATUS:200'):
            code = 'official_download_tls_failed' if result.returncode in (51, 60) else 'official_download_failed_after_fallback'
            raise OfficialDownloadError(code)
        stream.seek(0)
        return stream
    except BaseException:
        stream.close()
        raise


def fetch(url):
    validate_url(url)
    for attempt in range(3):
        try:
            return build_opener(HTTPSHandler(), OfficialRedirects()).open(url, timeout=60)
        except (URLError, TimeoutError, OSError):
            if attempt < 2:
                time.sleep(attempt + 1)
    print('[official-download] Python transport failed; trying validated HTTPS curl', file=sys.stderr, flush=True)
    return curl_fetch(url)


def select_asset(metadata, target):
    stable = metadata['channels']['Stable']
    version = stable['version']
    if not re.fullmatch(r'\d+\.\d+\.\d+\.\d+', version):
        raise ValueError('invalid_stable_version')
    entries = [item for item in stable['downloads']['chrome'] if item['platform'] == target]
    if len(entries) != 1:
        raise ValueError('official_asset_not_available_for_platform')
    url = validate_url(entries[0]['url'])
    expected = f'https://storage.googleapis.com/chrome-for-testing-public/{version}/{target}/chrome-{target}.zip'
    if url != expected:
        raise ValueError('unexpected_official_asset_path')
    return {'version': version, 'platform': target, 'url': url}


def latest_asset():
    if sys.platform != 'win32' or platform.machine().lower() not in ('amd64', 'x86_64', 'x86', 'i386', 'i686'):
        raise ValueError('automated_browser_identity_baseline_requires_windows_x64_or_x86; see docs/CHROME_FOR_TESTING.md')
    target = 'win64' if platform.machine().lower() in ('amd64', 'x86_64') else 'win32'
    with fetch(METADATA) as response:
        metadata = json.load(response)
    asset = select_asset(metadata, target)
    return dict(asset, metadata_url=METADATA, metadata_timestamp=metadata.get('timestamp'),
                queried_at=datetime.now(timezone.utc).isoformat())


def download(url, destination):
    """Bounded whole-file retries; .partial is never a completed cache entry."""
    for attempt in range(3):
        try:
            with fetch(url) as response, Path(destination).open('wb') as stream:
                count = 0
                while chunk := response.read(1024 * 1024):
                    stream.write(chunk)
                    count += len(chunk)
                    if count % (16 * 1024 * 1024) == 0:
                        print(f'[chrome-download] {count // (1024 * 1024)} MiB', file=sys.stderr, flush=True)
            return
        except (OSError, TimeoutError):
            if attempt == 2:
                raise RuntimeError('official_download_failed_after_3_attempts') from None
            time.sleep(attempt + 1)


def checked_members(bundle, destination):
    members = bundle.infolist()
    if not members or sum(item.file_size for item in members) > 4 * 1024 ** 3:
        raise ValueError('invalid_zip_size')
    seen = set()
    for item in members:
        name = item.filename
        path = PurePosixPath(name)
        if (path.is_absolute() or '..' in path.parts or ':' in name or '\\' in name
                or not path.parts or stat.S_ISLNK(item.external_attr >> 16)):
            raise ValueError('unsafe_zip_member')
        key = name.rstrip('/').casefold()
        if key in seen:
            raise ValueError('duplicate_zip_member')
        seen.add(key)
        (destination / name).resolve().relative_to(destination.resolve())
    if bundle.testzip() is not None:
        raise ValueError('zip_crc_failed')
    return members


def extract_checked(archive, destination):
    destination = Path(destination)
    with zipfile.ZipFile(archive) as bundle:
        checked_members(bundle, destination)
        if destination.exists():
            raise ValueError('extraction_destination_exists')
        destination.mkdir(parents=True)
        bundle.extractall(destination)


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def program_version(executable):
    # Windows GUI chrome.exe does not reliably emit --version to redirected stdout.
    path = str(Path(executable).resolve()).replace("'", "''")
    script = "[Console]::OutputEncoding=New-Object System.Text.UTF8Encoding($false); (Get-Item -LiteralPath '" + path + "').VersionInfo.ProductVersion"
    return subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', script],
                          capture_output=True, text=True, encoding='utf-8', check=True, timeout=15,
                          creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)).stdout.strip()


def install(root, asset):
    root = Path(root).resolve()
    # Validate even callers supplying a persisted selection, without trusting path components.
    select_asset({'channels': {'Stable': {'version': asset['version'], 'downloads': {'chrome': [asset]}}}}, asset['platform'])
    if asset['platform'] not in ('win64', 'win32'):
        raise ValueError('automated_browser_install_requires_windows')
    version, target = asset['version'], asset['platform']
    archive = root / f'tmp/downloads/chrome-{version}-{target}.zip'
    receipt = archive.with_suffix('.json')
    destination = root / f'tmp/browsers/chrome-for-testing/{version}/{target}'
    executable = destination / f'chrome-{target}/chrome.exe'
    record_path = destination / 'installation.json'
    archive.parent.mkdir(parents=True, exist_ok=True)
    if archive.exists():
        try:
            prior = json.loads(receipt.read_text(encoding='utf-8'))
            if prior['url'] != asset['url'] or prior['archive_sha256'] != sha256(archive):
                raise ValueError('cached_archive_changed')
        except (OSError, KeyError):
            raise ValueError('unreviewed_browser_cache; preserve it and review its provenance') from None
    else:
        temporary = archive.with_suffix('.zip.partial')
        download(asset['url'], temporary)
        with zipfile.ZipFile(temporary) as bundle:
            checked_members(bundle, destination)
        digest = sha256(temporary)
        os.replace(temporary, archive)
        atomic_json(receipt, dict(asset, archive_sha256=digest))
    with zipfile.ZipFile(archive) as bundle:
        checked_members(bundle, destination)
    digest = sha256(archive)
    if destination.exists():
        prior = json.loads(record_path.read_text(encoding='utf-8')) if record_path.is_file() else {}
        if (not executable.is_file() or prior.get('archive_sha256') != digest
                or prior.get('executable_sha256') != sha256(executable) or program_version(executable) != version):
            raise ValueError('existing_browser_install_requires_review; no files overwritten')
        return dict(prior, action='reused')
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='chrome-', dir=destination.parent))
    # extract_checked expects a new destination below our owned staging directory.
    extracted = staging / 'content'
    try:
        extract_checked(archive, extracted)
        program = extracted / f'chrome-{target}/chrome.exe'
        if not program.is_file() or program_version(program) != version:
            raise ValueError('downloaded_browser_version_mismatch')
        record = dict(asset, archive_sha256=digest, executable_sha256=sha256(program), executable=str(executable),
                      hash_type='local_sha256_not_official_checksum', action='installed')
        atomic_json(extracted / 'installation.json', record)
        os.replace(extracted, destination)
        return record
    finally:
        # Only remove this function's verified temporary subtree, never an existing install/profile.
        staging.resolve().relative_to(destination.parent.resolve())
        shutil.rmtree(staging)
