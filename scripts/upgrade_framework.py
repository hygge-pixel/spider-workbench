"""Three-way, hash-checked framework upgrade. Default is a read-only plan."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile
import uuid


ROOT = Path(__file__).resolve().parents[1]
PROTECTED_PREFIXES = ('runs/', 'tmp/', 'outputs/', 'experiments/', 'config/local_credentials/')
PROTECTED_FILES = {'platforms/registry.json', 'config/workspace_browser.json', 'config/agent_tools.local.json',
                   '.mcp.json', '.agents/mcp_config.json', '.gemini/settings.json'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def safe(root, name):
    relative = PurePosixPath(name)
    if relative.is_absolute() or '..' in relative.parts or not relative.parts or ':' in name or '\\' in name:
        raise ValueError('unsafe release path')
    path = Path(root).resolve().joinpath(*relative.parts)
    path.resolve().relative_to(Path(root).resolve())
    if os.path.normcase(os.path.realpath(path)) != os.path.normcase(str(path.absolute())):
        raise ValueError('linked update path requires manual review: ' + name)
    return path


def manifest(root, relative='MANIFEST.sha256.json'):
    data = json.loads((Path(root) / relative).read_text(encoding='utf-8'))
    if data.get('schema_version') != 1 or not isinstance(data.get('files'), dict):
        raise ValueError('invalid distribution manifest')
    for name, digest in data['files'].items():
        safe(root, name)
        if not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest):
            raise ValueError('invalid manifest digest')
    return data


def make_plan(release, target, *, accept_local=()):
    release, target = Path(release).resolve(), Path(target).resolve()
    if release == target or release in target.parents or target in release.parents:
        raise ValueError('release and target must be separate non-nested directories')
    current = manifest(release)
    baseline_path = safe(target, 'MANIFEST.sha256.json')
    if baseline_path.exists():
        # A malformed installed manifest is an error, never permission to use
        # an unrelated historical baseline and overwrite local work.
        baseline = manifest(target)
        baseline_source = 'target_manifest'
    else:
        baseline_path = release / 'upgrade/v1_manifest.sha256.json'
        baseline = manifest(release, 'upgrade/v1_manifest.sha256.json')
        baseline_source = 'legacy_v1_manifest'
    accepted = set(accept_local)
    changes, conflicts, preserved = [], [], []
    expected = dict(current['files'])
    for name, digest in expected.items():
        path = safe(release, name)
        if not path.is_file() or sha(path) != digest:
            raise ValueError('release integrity failure: ' + name)
    expected['MANIFEST.sha256.json'] = sha(release / 'MANIFEST.sha256.json')
    old = dict(baseline['files'], **{'MANIFEST.sha256.json': sha(baseline_path)})
    for name, digest in expected.items():
        if name in PROTECTED_FILES or name.startswith(PROTECTED_PREFIXES):
            preserved.append(name)
            continue
        path = safe(target, name)
        # A directory at a file destination, or a file in its parent chain,
        # is a local path conflict. Catch it during the read-only plan so
        # apply never starts replacing other files before discovering it.
        if ((path.exists() and not path.is_file()) or
                any(parent.exists() and not parent.is_dir()
                    for parent in path.parents if parent != target and target in parent.parents)):
            conflicts.append(name)
            continue
        actual = sha(path) if path.is_file() else None
        if name in accepted:
            if actual is None:
                raise ValueError('accept-local requires an existing reviewed file: ' + name)
            preserved.append(name)
        elif actual == digest:
            continue
        elif actual is None or actual == old.get(name):
            changes.append({'path': name, 'before': actual, 'after': digest})
        elif name in old and old[name] == digest:
            preserved.append(name)
        else:
            conflicts.append(name)
    return {'target': str(target), 'changes': changes, 'conflicts': sorted(conflicts),
            'preserved': sorted(preserved), 'accept_local': sorted(accepted),
            'baseline_source': baseline_source,
            'obsolete_framework_files': sorted(name for name in baseline['files']
                if name not in expected and name not in PROTECTED_FILES and not name.startswith(PROTECTED_PREFIXES)),
            'scope': 'framework-owned changed/new files only; local tasks, registry, state and configs preserved'}


def atomic_copy(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as handle:
        temporary = Path(handle.name)
    try:
        shutil.copyfile(source, temporary)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def apply_plan(release, target, plan):
    release, target = Path(release).resolve(), Path(target).resolve()
    latest = make_plan(release, target, accept_local=plan.get('accept_local', ()))
    if latest['conflicts']:
        raise ValueError('conflicts require review; no update files written: ' + ', '.join(latest['conflicts']))
    if latest['changes'] != plan['changes']:
        raise ValueError('target changed after planning; re-run plan')
    if not latest['changes']:
        return {'passed': True, 'status': 'already_current', 'backup': None, 'updated': 0}
    backup = target / 'outputs/framework-upgrade' / uuid.uuid4().hex
    backup.mkdir(parents=True, exist_ok=False)
    record = {'target': str(target), 'changes': latest['changes'], 'accept_local': latest['accept_local']}
    for item in latest['changes']:
        destination = safe(target, item['path'])
        if item['before'] is not None:
            saved = safe(backup / 'original', item['path'])
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(destination, saved)
    (backup / 'rollback.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
    completed = []
    try:
        for item in latest['changes']:
            destination = safe(target, item['path'])
            actual = sha(destination) if destination.is_file() else None
            if actual != item['before']:
                raise ValueError('concurrent target change: ' + item['path'])
            atomic_copy(safe(release, item['path']), destination)
            completed.append(item)
    except Exception:
        # Restore only bytes this invocation just installed; preserve concurrent changes.
        for item in reversed(completed):
            destination = safe(target, item['path'])
            if destination.is_file() and sha(destination) == item['after']:
                if item['before'] is None:
                    destination.unlink()
                else:
                    atomic_copy(safe(backup / 'original', item['path']), destination)
        raise
    return {'passed': True, 'status': 'updated', 'backup': str(backup), 'updated': len(completed),
            'accepted_local': latest['accept_local']}


def rollback(target, backup):
    target, backup = Path(target).resolve(), Path(backup).resolve()
    backup.relative_to(target / 'outputs/framework-upgrade')
    record = json.loads((backup / 'rollback.json').read_text(encoding='utf-8'))
    if Path(record['target']).resolve() != target:
        raise ValueError('rollback target mismatch')
    for item in record['changes']:
        path = safe(target, item['path'])
        if not path.is_file() or sha(path) != item['after']:
            raise ValueError('changed since upgrade; preserve newer work: ' + item['path'])
        if item['before'] is not None and sha(safe(backup / 'original', item['path'])) != item['before']:
            raise ValueError('backup integrity failure')
    for item in reversed(record['changes']):
        path = safe(target, item['path'])
        if item['before'] is None:
            path.unlink()
        else:
            atomic_copy(safe(backup / 'original', item['path']), path)
    return {'passed': True, 'status': 'rolled_back', 'files': len(record['changes'])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--accept-local', action='append', default=[])
    parser.add_argument('--rollback', type=Path)
    args = parser.parse_args()
    try:
        if args.rollback:
            if not args.apply:
                raise ValueError('rollback requires explicit --apply')
            result = rollback(args.target, args.rollback)
        else:
            result = make_plan(ROOT, args.target, accept_local=args.accept_local)
            if args.apply:
                result = apply_plan(ROOT, args.target, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result.get('conflicts') else 0
    except (OSError, ValueError) as error:
        print(json.dumps({'passed': False, 'error': str(error)}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
