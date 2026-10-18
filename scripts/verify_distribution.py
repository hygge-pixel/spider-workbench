"""Check original distribution file hashes without following escaping paths."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import re


ROOT = Path(__file__).resolve().parents[1]


def verify(root: Path) -> dict:
    root = Path(root).resolve()
    try:
        data = json.loads((root / 'MANIFEST.sha256.json').read_text(encoding='utf-8'))
        if not isinstance(data, dict) or data.get('schema_version') != 1:
            raise ValueError('invalid manifest schema')
        files = data.get('files')
        if not isinstance(files, dict) or not files:
            raise ValueError('manifest files must be a non-empty object')
        validated = []
        for name, digest in files.items():
            path = PurePosixPath(name)
            if (path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name
                    or not path.parts or not isinstance(digest, str)
                    or not re.fullmatch('[0-9a-f]{64}', digest)):
                raise ValueError('unsafe path or digest in manifest')
            absolute = root.joinpath(*path.parts)
            absolute.resolve().relative_to(root)
            validated.append((name, absolute, digest))
        missing, changed = [], []
        for name, path, digest in validated:
            if not path.is_file():
                missing.append(name)
            elif hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                changed.append(name)
        return {'passed': not missing and not changed, 'checked_files': len(files),
                'missing': sorted(missing), 'changed': sorted(changed)}
    except (OSError, ValueError, TypeError) as error:
        return {'passed': False, 'error': str(error)}


if __name__ == '__main__':
    result = verify(ROOT)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result['passed'] else 1)
