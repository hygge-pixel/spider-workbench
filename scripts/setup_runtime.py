"""Install a checked, isolated Windows Node; preserve system runtimes and local settings."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.setup_chrome import atomic_json, curl_fetch, extract_checked, installation_lock, sha256
from spider_core.project_runtime import select_node, select_python


def validate_node_url(url):
    parts = urlparse(url)
    if (parts.scheme != 'https' or parts.hostname != 'nodejs.org' or parts.port not in (None, 443)
            or parts.username or parts.password or parts.query or parts.fragment
            or not re.fullmatch(r'/dist/v24\.\d+\.\d+/(?:SHASUMS256\.txt|node-v24\.\d+\.\d+-win-(?:x64|x86|arm64)\.zip)', parts.path)):
        raise ValueError('official_node_url_required')
    return url


def transfer(url, path):
    with curl_fetch(url, validate_node_url) as response, Path(path).open('wb') as stream:
        shutil.copyfileobj(response, stream)


def official_checksum(version, filename):
    url = f'https://nodejs.org/dist/v{version}/SHASUMS256.txt'
    with curl_fetch(url, validate_node_url) as response:
        lines = response.read(1024 * 1024).decode('utf-8').splitlines()
    matches = [line.split()[0] for line in lines if len(line.split()) == 2 and line.split()[1] == filename]
    if len(matches) != 1 or not re.fullmatch('[a-f0-9]{64}', matches[0]):
        raise ValueError('official_node_checksum_missing')
    return matches[0]


def probe_node(node):
    node = Path(node)
    version = subprocess.run([str(node), '--version'], capture_output=True, text=True, check=True, timeout=15).stdout.strip()
    if int(version.lstrip('v').split('.')[0]) < 24:
        raise ValueError('node_version_too_old')
    subprocess.run([str(node), str(node.parent / 'node_modules/npm/bin/npm-cli.js'), '--version'],
                   capture_output=True, check=True, timeout=20)
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / 'probe.ts'
        source.write_text('const n: number = 42; console.log(n);')
        result = subprocess.run([str(node), '--experimental-strip-types', str(source)], capture_output=True, text=True, timeout=20)
        if result.returncode or result.stdout.strip() != '42':
            raise ValueError('node_typescript_probe_failed')
    return version


def install_node(root, version='24.22.0', architecture='x64'):
    root = Path(root).resolve()
    if not re.fullmatch(r'24\.\d+\.\d+', version) or architecture not in ('x64', 'x86', 'arm64'):
        raise ValueError('unsupported_node_selection')
    filename = f'node-v{version}-win-{architecture}.zip'
    url = f'https://nodejs.org/dist/v{version}/{filename}'
    destination = root / f'tmp/runtimes/node/v{version}-{architecture}'
    node = destination / 'node.exe'
    receipt = destination / 'installation.json'
    if destination.exists():
        prior = json.loads(receipt.read_text('utf-8')) if receipt.is_file() else {}
        if not node.is_file() or prior.get('node_sha256') != sha256(node) or probe_node(node) != f'v{version}':
            raise ValueError('existing_node_requires_review; no files overwritten')
        return dict(prior, action='reused')
    cache = root / 'tmp/downloads'
    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / filename
    expected = official_checksum(version, filename)
    if archive.exists() and sha256(archive) != expected:
        raise ValueError('cached_node_checksum_mismatch; preserve_and_review')
    if not archive.exists():
        partial = archive.with_suffix('.zip.partial')
        transfer(url, partial)
        if sha256(partial) != expected:
            raise ValueError('node_checksum_mismatch')
        os.replace(partial, archive)
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='node-', dir=destination.parent))
    try:
        extract_checked(archive, staging / 'content')
        content = staging / 'content' / filename[:-4]
        if probe_node(content / 'node.exe') != f'v{version}':
            raise ValueError('node_version_mismatch')
        record = {'node': str(node), 'version': f'v{version}', 'url': url, 'archive_sha256': expected,
                  'node_sha256': sha256(content / 'node.exe'), 'action': 'installed'}
        atomic_json(content / 'installation.json', record)
        os.replace(content, destination)
        return record
    finally:
        staging.resolve().relative_to(destination.parent.resolve())
        shutil.rmtree(staging)


def setup(root, python=None, node=None, architecture='x64'):
    root = Path(root).resolve()
    base = select_python(root, python)
    with installation_lock(root):
        try:
            chosen = select_node(root, node)
            probe_node(chosen)
            node_result = {'node': str(chosen), 'action': 'reused'}
        except (ValueError, OSError, subprocess.SubprocessError):
            config = root / 'config/agent_tools.local.json'
            pinned = json.loads(config.read_text('utf-8')).get('browser_toolchain', {}).get('node_executable') if config.is_file() else None
            if node or os.environ.get('SPIDER_NODE') or pinned:
                raise  # A broken explicit/project pin requires review; never silently switch it.
            node_result = install_node(root, architecture=architecture)
        path = root / 'config/agent_tools.local.json'
        settings = json.loads(path.read_text('utf-8')) if path.is_file() else {}
        toolchain = settings.setdefault('browser_toolchain', {})
        toolchain.update(python_executable=str(base), node_executable=node_result['node'])
        settings['runtime_bootstrap'] = {'python': str(base), 'node': node_result['node'],
                                         'toolchain_pending': not bool(toolchain.get('js_reverser_entry'))}
        atomic_json(path, settings)
    return {'passed': True, 'python': str(base), **node_result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python', type=Path)
    parser.add_argument('--node', type=Path)
    parser.add_argument('--architecture', choices=('x64', 'x86', 'arm64'), default='x64')
    args = parser.parse_args()
    from scripts.deploy import diagnostic
    try:
        result = setup(ROOT, args.python, args.node, args.architecture)
    except Exception as error:
        print(json.dumps({'passed': False, **diagnostic(error)}))
        return 1
    print(json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
