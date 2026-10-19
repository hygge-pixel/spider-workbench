"""Portable Skill discovery setup; optional browser configuration is explicit."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
PLATFORM_SKILL_PATHS = ('.agents/skills', '.claude/skills', '.gemini/skills')
RULE_FILES = ('AGENTS.md', 'CLAUDE.md', 'GEMINI.md')
AGENT_RULE_ENTRIES = {
    'codex': 'AGENTS.md',
    'claude-code': 'CLAUDE.md',
    'gemini-cli': 'GEMINI.md',
    'cursor': 'AGENTS.md',
    'copilot': '.github/copilot-instructions.md',
    'windsurf': 'AGENTS.md',
    'cline': '.clinerules/00-spider-workbench.md',
    'roo-code': '.roo/rules/00-spider-workbench.md',
    'kiro': 'AGENTS.md',
    'opencode': 'AGENTS.md',
    'trae': '.trae/rules/project_rules.md',
}


def ensure_junction(link: Path, target: Path) -> dict:
    """Create a Windows junction or POSIX symlink; never replace existing content."""
    link, target = Path(link).absolute(), Path(target).resolve()
    if not target.is_dir():
        return {'ok': False, 'status': 'target_missing', 'path': str(link)}
    if os.path.lexists(link):
        is_link = link.is_symlink() or os.path.normcase(os.path.realpath(link)) != os.path.normcase(str(link))
        same = is_link and os.path.normcase(os.path.realpath(link)) == os.path.normcase(str(target))
        return {'ok': same, 'status': 'reused' if same else 'conflict', 'path': str(link)}
    link.parent.mkdir(parents=True, exist_ok=True)
    try:
        if os.name == 'nt':
            env = dict(os.environ, SPIDER_LINK_PATH=str(link), SPIDER_LINK_TARGET=str(target))
            result = subprocess.run(
                ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
                 "$ErrorActionPreference = 'Stop'; New-Item -ItemType Junction -Path $env:SPIDER_LINK_PATH -Value $env:SPIDER_LINK_TARGET | Out-Null"],
                env=env, capture_output=True, timeout=30, check=False,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            if result.returncode:
                return {'ok': False, 'status': 'create_failed', 'path': str(link)}
        else:
            link.symlink_to(target, target_is_directory=True)
    except (OSError, subprocess.TimeoutExpired):
        return {'ok': False, 'status': 'create_failed', 'path': str(link)}
    return {'ok': link.is_dir(), 'status': 'created', 'path': str(link)}


def setup(root: Path) -> dict:
    root = Path(root).resolve()
    canonical = root / 'skills'
    if not canonical.is_dir():
        return {'ok': False, 'error': 'canonical_skills_missing', 'skills': []}
    links = [ensure_junction(root / relative, canonical) for relative in PLATFORM_SKILL_PATHS]
    return {'ok': all(item['ok'] for item in links), 'skills': links}


def configure_browser(root: Path, candidate: str, executable: Path, *, merge: bool = False) -> dict:
    root = Path(root).resolve()
    if candidate != 'chrome':
        raise ValueError('only the chrome candidate is supported')
    executable = Path(executable).expanduser()
    if not executable.is_absolute() or not executable.is_file():
        raise ValueError('browser executable must be an existing absolute file path')
    path = root / 'config/workspace_browser.json'
    item = {
        'executable': str(executable.resolve()),
        'cdp_url': 'http://127.0.0.1:9222',
        'user_data_dir': str(root / 'tmp' / f'{candidate}-mcp'),
        'startup_timeout_seconds': 15,
        'launch_args': [],
        'environment': {},
    }
    if path.exists():
        data = json.loads(path.read_text(encoding='utf-8'))
        if data.get('schema_version') != 2 or not isinstance(data.get('candidates'), dict):
            raise ValueError('existing browser config is invalid; preserve and review it manually')
        if set(data['candidates']) != {'chrome'} or data.get('default_candidate') != 'chrome':
            raise ValueError('legacy browser config requires backup and explicit migration; see docs/MIGRATION.md')
        if data['candidates'].get(candidate) == item:
            return {'ok': True, 'status': 'reused', 'path': str(path)}
        if not merge:
            raise FileExistsError('browser config exists; review it and explicitly use --merge')
        placeholder = str(root / 'tmp' / f'unconfigured-{candidate}-browser')
        if candidate in data['candidates'] and data['candidates'][candidate].get('executable') != placeholder:
            raise FileExistsError('candidate exists with different settings; preserve and review manually')
        data['candidates'][candidate] = item
    else:
        data = {'schema_version': 2, 'default_candidate': candidate,
                'candidates': {candidate: item}}
    path.parent.mkdir(parents=True, exist_ok=True)
    # Validate before writing and use a same-directory temporary file for atomic replace.
    import tempfile
    from spider_core.browser import load_workspace_browser_configs
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent,
                                     suffix='.json', delete=False) as stream:
        temporary = Path(stream.name)
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    try:
        load_workspace_browser_configs(root, config_path=temporary)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return {'ok': True, 'status': 'configured', 'path': str(path)}


def set_default_browser(root: Path, candidate: str) -> dict:
    from spider_core.browser import load_workspace_browser_configs
    root = Path(root).resolve()
    pool = load_workspace_browser_configs(root)
    if candidate not in pool.candidates or not pool.candidates[candidate].executable.is_file():
        raise ValueError('default candidate requires an existing configured executable')
    path = root / 'config/workspace_browser.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    data['default_candidate'] = candidate
    import tempfile
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    try:
        load_workspace_browser_configs(root, config_path=temporary)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return {'ok': True, 'status': 'default_updated', 'default_candidate': candidate}


def doctor(root: Path) -> dict:
    """Report local resources only: no browser launch, MCP launch or live requests."""
    root = Path(root).resolve()
    canonical = root / 'skills'
    names = sorted(p.parent.name for p in canonical.glob('*/SKILL.md'))
    rules = {name: (root / name).is_file() for name in RULE_FILES}
    discovery = {}
    for relative in PLATFORM_SKILL_PATHS:
        link = root / relative
        discovery[relative] = {'ready': link.is_dir() and link.resolve() == canonical.resolve()}
    try:
        data = json.loads((root / 'platforms/registry.json').read_text(encoding='utf-8'))
        registry_ok = data.get('schema_version') == 1 and isinstance(data.get('platforms'), list)
    except (OSError, ValueError, AttributeError):
        registry_ok = False
    browser = {'status': 'not_configured', 'required_for_offline': False}
    if (root / 'config/workspace_browser.json').is_file():
        from spider_core.browser import WorkspaceBrowserError, load_workspace_browser_configs
        try:
            pool = load_workspace_browser_configs(root)
            browser = {'status': 'configured', 'required_for_offline': False,
                       'default_candidate': pool.default_candidate,
                       'executables_exist': {name: item.executable.is_file() for name, item in pool.candidates.items()},
                       'live_verified': False}
        except (WorkspaceBrowserError, OSError):
            browser = {'status': 'config_invalid', 'required_for_offline': False}
    return {
        'ok': sys.version_info >= (3, 11) and all(rules.values()) and bool(names)
              and all(item['ready'] for item in discovery.values()) and registry_ok,
        'scope': 'offline framework readiness; browser and MCP are optional and separately accepted',
        'python': {'version': sys.version.split()[0], 'executable': sys.executable},
        'rules': rules, 'skills': {'count': len(names), 'canonical': names, 'discovery': discovery},
        'agent_entries': {
            host: {'path': relative, 'entry_present': (root / relative).is_file(),
                   'host_loaded_verified': False}
            for host, relative in AGENT_RULE_ENTRIES.items()
        },
        'registry_valid': registry_ok, 'browser': browser,
        'optional_tools': {name: {'in_path': shutil.which(name) is not None}
                           for name in ('node', 'npm', 'playwright-cli')},
        'mcp': {'status': 'configure_in_target_agent', 'live_verified': False},
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True)
    for name in ('setup', 'doctor', 'configure-browser', 'set-default'):
        command = commands.add_parser(name)
        command.add_argument('--root', type=Path, default=ROOT)
        command.add_argument('--json', action='store_true')
        if name == 'configure-browser':
            command.add_argument('--candidate', choices=('chrome',), required=True)
            command.add_argument('--executable', type=Path, required=True)
            command.add_argument('--merge', action='store_true')
        if name == 'set-default':
            command.add_argument('--candidate', choices=('chrome',), required=True)
    args = parser.parse_args(argv)
    try:
        if args.action == 'set-default':
            report = set_default_browser(args.root, args.candidate)
        elif args.action == 'configure-browser':
            report = configure_browser(args.root, args.candidate, args.executable, merge=args.merge)
        else:
            report = setup(args.root) if args.action == 'setup' else doctor(args.root)
    except (OSError, ValueError) as error:
        report = {'ok': False, 'error': str(error)}
    print(json.dumps(report, ensure_ascii=False, indent=2 if args.json else None))
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
