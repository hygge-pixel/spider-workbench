"""Build a reproducible manifest-only public source ZIP; no upload or Git mutation."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.check_public_release import developer_path, refresh_manifest, scan


def build_release(root, output, *, require_structure=True, kind='source'):
    if kind not in {'source', 'install'}:
        raise ValueError('invalid release kind')
    root, output = Path(root).resolve(), Path(output).resolve()
    result = scan(root, require_structure=require_structure)
    if not result['passed']:
        raise ValueError('public release checks failed; run check_public_release.py for locations')
    metadata_path = root/'FRAMEWORK_RELEASE.json'
    version = json.loads(metadata_path.read_text(encoding='utf-8'))['version'] if metadata_path.is_file() else '0.1.0'
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?', version):
        raise ValueError('invalid source release version')
    data = json.loads((root/'MANIFEST.sha256.json').read_text(encoding='utf-8'))
    names = sorted({name for name in data['files'] if kind == 'source' or not developer_path(name)}
                   | {'MANIFEST.sha256.json'})
    install_manifest = dict(data, edition='spider-workbench-install', distribution_kind='install',
                            files={name: data['files'][name] for name in names if name != 'MANIFEST.sha256.json'})
    output.mkdir(parents=True, exist_ok=True)
    archive = output/f'spider-workbench-{version}-{kind}.zip'
    temporary = archive.with_suffix('.zip.tmp')
    try:
        with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
            for name in names:
                # Recheck bytes to catch source edits between initial validation and packaging.
                content = ((json.dumps(install_manifest, ensure_ascii=False, indent=2)+'\n').encode('utf-8')
                           if kind == 'install' and name == 'MANIFEST.sha256.json' else (root/name).read_bytes())
                if name in data['files'] and hashlib.sha256(content).hexdigest() != data['files'][name]:
                    raise ValueError('source changed during release: ' + name)
                entry = zipfile.ZipInfo('spider-workbench/'+name, date_time=(2026,1,1,0,0,0))
                entry.compress_type = zipfile.ZIP_DEFLATED
                entry.create_system = 3
                entry.external_attr = 0o100644 << 16
                bundle.writestr(entry, content, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        with zipfile.ZipFile(temporary) as bundle:
            if bundle.testzip() is not None:
                raise ValueError('ZIP integrity check failed')
        temporary.replace(archive)
    finally:
        temporary.unlink(missing_ok=True)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (output/'SHA256SUMS.txt').write_text(digest+'  '+archive.name+'\n', encoding='utf-8')
    return {'passed':True, 'kind':kind, 'archive':str(archive), 'sha256':digest,
            'files':len(names), 'bytes':archive.stat().st_size}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh-manifest', action='store_true', help='maintainer operation: inventory reviewed public files')
    parser.add_argument('--output', type=Path, default=ROOT/'outputs/releases')
    parser.add_argument('--kind', choices=['source', 'install', 'both'], default='both')
    args = parser.parse_args()
    try:
        if args.refresh_manifest:
            data = refresh_manifest(ROOT)
            result = {'passed':True, 'manifest_files':len(data['files']), 'mode':'refresh-manifest'}
        else:
            kinds = ['source', 'install'] if args.kind == 'both' else [args.kind]
            bundles = [build_release(ROOT, args.output, kind=kind) for kind in kinds]
            (args.output/'SHA256SUMS.txt').write_text(''.join(
                item['sha256']+'  '+Path(item['archive']).name+'\n' for item in bundles), encoding='utf-8')
            result = {'passed': True, 'bundles': bundles}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({'passed':False, 'error':str(error)}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
