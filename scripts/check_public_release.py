"""Read-only public source release checks; reports locations, never secret values."""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import os
import re
import subprocess
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = {
    '.gitignore', '.gitattributes', '.editorconfig', 'LICENSE', 'NOTICE',
    'README.md', 'README.en.md', 'AGENTS.md', 'CLAUDE.md', 'GEMINI.md',
    'CONTRIBUTING.md', 'SECURITY.md', 'CODE_OF_CONDUCT.md', 'CHANGELOG.md',
    'THIRD_PARTY_NOTICES.md', 'SOURCE_PROVENANCE.json', 'FRAMEWORK_RELEASE.json',
    'MANIFEST.sha256.json', 'spider.py', 'bootstrap.py', 'pyproject.toml', 'package.json', 'package-lock.json',
    'requirements-collection.txt',
}
AGENT_ENTRY_FILES = {
    '.github/copilot-instructions.md', '.clinerules/00-spider-workbench.md',
    '.roo/rules/00-spider-workbench.md', '.trae/rules/project_rules.md',
}
SOURCE_DIRS = {'spider_core', 'scripts', 'skills', 'docs',
               'requirements-backends', '.github', 'upgrade', '.clinerules', '.roo', '.trae'}
LOCAL_DIRS = {'.git', 'node_modules', '__pycache__', '.venv', '.venv-toolchain',
              '.pytest_cache', 'selftest_tmp', 'build', '.cache', 'debugger-sessions'}
EXTENSIONS = {'.py', '.js', '.mjs', '.cjs', '.ts', '.json', '.md', '.txt', '.toml',
              '.ps1', '.yaml', '.yml', '.gitkeep', '.lock'}
REQUIRED = {'README.md', 'README.en.md', 'bootstrap.py', 'docs/USER_GUIDE.md', 'docs/INSTALL_WITH_AGENT.md',
            'LICENSE', 'NOTICE', 'THIRD_PARTY_NOTICES.md',
            'SOURCE_PROVENANCE.json', 'spider.py', 'platforms/registry.json',
            '.github/workflows/ci.yml', 'docs/QUICKSTART.md', 'docs/OPEN_SOURCE_RELEASE.md',
            'vendor/js-reverse-mcp/LICENSE', 'skills/playwright-cli/LICENSE'}
REQUIRED |= AGENT_ENTRY_FILES | {'docs/AGENT_COMPATIBILITY.md'}

# High-confidence formats only; no claim of exhaustive credential detection.
SECRET = re.compile(r'gh[pousr]_[A-Za-z0-9]{30,255}|github_pat_[A-Za-z0-9_]{40,255}|'
                    r'AKIA[0-9A-Z]{16}|(?:sk-proj-|sk-ant-api03-)[A-Za-z0-9_-]{20,}|'
                    r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')
PRIVATE_PATH = re.compile(r'(?i)[A-Z]:[/\\]Users[/\\](?!Public(?:[/\\]|$)|USERNAME(?:[/\\]|$))'
                          r'[A-Za-z0-9_.-]+[/\\]|[A-Z]:[/\\]py_code[/\\]')


def public_path(name):
    p = PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts or not p.parts or ':' in name or '\\' in name:
        return False
    if any(part in LOCAL_DIRS for part in p.parts):
        return False
    if ('tests' in p.parts or p.name in {'test-prompts.json', 'selftest.py'}
            or re.search(r'\.(?:test|spec)\.(?:js|mjs|cjs|ts|py)$', p.name)):
        return False
    if p.name == 'cookies.json' or p.name.startswith('.env') or p.suffix.lower() in {'.env', '.log', '.har', '.sqlite', '.sqlite3'}:
        return False
    if len(p.parts) == 1:
        return name in ROOT_FILES
    if p.parts[0] in {'.clinerules', '.roo', '.trae'}:
        return name in AGENT_ENTRY_FILES
    if p.parts[0] in {'runs', 'outputs', 'tmp', 'tools'}:
        return len(p.parts) == 2 and p.name == '.gitkeep'
    if name == 'platforms/registry.json':
        return True
    if p.parts[0] == 'experiments':
        return len(p.parts) >= 3 and p.parts[1] == 'example_local' and p.suffix in EXTENSIONS
    if p.parts[0] == 'config':
        return (len(p.parts) == 2 and (p.name.endswith('.example.json') or p.name == 'README.md')) or name == 'config/local_credentials/.gitkeep'
    if p.parts[0] in {'vendor', 'toolchain'}:
        expected = 'js-reverse-mcp' if p.parts[0] == 'vendor' else 'playwright-cli'
        return len(p.parts) >= 3 and p.parts[1] == expected and (p.suffix in EXTENSIONS or p.name.startswith(('LICENSE', 'NOTICE')))
    return p.parts[0] in SOURCE_DIRS and (p.suffix in EXTENSIONS or p.name.startswith(('LICENSE', 'NOTICE')) or p.name == '.gitkeep')


def is_linked(root, path):
    root = root.resolve()
    try:
        path.resolve().relative_to(root)
    except ValueError:
        return True
    return os.path.normcase(os.path.realpath(path)) != os.path.normcase(str(path.absolute()))


def tracked_files(root):
    # Do not inspect a parent workspace repository when auditing an extracted ZIP.
    if not (root / '.git').exists():
        return []
    result = subprocess.run(['git', 'ls-files', '-z', '--cached'], cwd=root,
                            capture_output=True, check=True)
    return result.stdout.decode('utf-8').split('\0')[:-1]


def scan(root, *, require_structure=True):
    root = Path(root).resolve()
    issues = []
    def issue(path, rule, line=None):
        item = {'path': path, 'rule': rule}
        if line is not None:
            item['line'] = line
        issues.append(item)
    try:
        data = json.loads((root/'MANIFEST.sha256.json').read_text(encoding='utf-8'))
        files = data['files']
        if data.get('schema_version') != 1 or not isinstance(files, dict) or not files:
            raise ValueError('invalid_manifest')
        tracked = set(tracked_files(root))
        expected = set(files) | {'MANIFEST.sha256.json'}
        for name in sorted(tracked - expected):
            issue(name, 'unmanifested_tracked_file')
        for name in sorted(expected | tracked):
            if not public_path(name):
                issue(name, 'forbidden_path')
                continue
            path = root / name
            if is_linked(root, path):
                issue(name, 'linked_source')
                continue
            if not path.is_file():
                issue(name, 'missing_file')
                continue
            raw = path.read_bytes()
            if name in files:
                digest = files[name]
                if not isinstance(digest, str) or not re.fullmatch('[a-f0-9]{64}', digest):
                    issue(name, 'invalid_digest')
                elif hashlib.sha256(raw).hexdigest() != digest:
                    issue(name, 'hash_mismatch')
            try:
                content = raw.decode('utf-8-sig')
            except UnicodeDecodeError:
                issue(name, 'unexpected_binary')
                continue
            for n, line in enumerate(content.splitlines(), 1):
                if SECRET.search(line):
                    issue(name, 'known_secret', n)
                if PRIVATE_PATH.search(line):
                    issue(name, 'private_machine_path', n)
            if path.suffix == '.md':
                markdown = re.sub(r'```.*?```', '', content, flags=re.S)
                markdown = re.sub(r'`[^`]*`', '', markdown)
                for target in re.findall(r'\]\(([^)]+)\)', markdown):
                    if target.startswith(('https:', 'http:', '#', 'mailto:')):
                        continue
                    target = unquote(target.split('#', 1)[0].strip('<>'))
                    if target and not (path.parent/target).is_file():
                        issue(name, 'broken_local_link')
        if require_structure:
            for name in sorted(REQUIRED - expected):
                issue(name, 'required_file_missing')
            registry = json.loads((root/'platforms/registry.json').read_text(encoding='utf-8'))
            if registry.get('platforms') != []:
                issue('platforms/registry.json', 'nonempty_initial_registry')
            skills = [n for n in files if n.startswith('skills/') and n.count('/') == 2 and n.endswith('/SKILL.md')]
            if len(skills) != 13:
                issue('skills', 'initial_skill_set_changed')
        return {'passed': not issues, 'checked_files': len(expected | tracked),
                'issues': issues, 'scope': 'public source manifest, tracked files, known secret formats and release structure'}
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        return {'passed': False, 'issues': issues + [{'path':'MANIFEST.sha256.json', 'rule':'invalid_manifest_or_repository'}]}


def refresh_manifest(root):
    root = Path(root).resolve()
    files = {}
    for directory, dirs, names in os.walk(root, followlinks=False):
        parent = Path(directory)
        dirs[:] = sorted(d for d in dirs if d not in LOCAL_DIRS and
                         (parent != root or d in SOURCE_DIRS | {'vendor','toolchain','config','platforms','experiments','runs','outputs','tmp','tools'}))
        for name in sorted(names):
            path = parent/name
            relative = path.relative_to(root).as_posix()
            if relative == 'MANIFEST.sha256.json' or not public_path(relative):
                continue
            if is_linked(root, path):
                raise ValueError('linked source requires review: ' + relative)
            files[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    data = {'schema_version':1, 'edition':'spider-workbench-public-source', 'files':dict(sorted(files.items()))}
    (root/'MANIFEST.sha256.json').write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    result = scan(args.root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
