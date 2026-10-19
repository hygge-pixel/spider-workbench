"""Plan or install isolated browser tooling. Explicit --apply is required for installation."""
from pathlib import Path
import argparse
import json
import os
import shutil
import subprocess
import sys
import hashlib
import platform
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from spider_core.project_runtime import select_node, npm_cli


def plans(component, node):
    tasks = []
    if component in ('python', 'all'):
        if sys.version_info[:2] != (3, 11):
            raise ValueError('Python 3.11 is required; select a side-by-side 3.11 executable without replacing existing runtimes')
        venv = ROOT / '.venv-toolchain'
        python = venv / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        if python.is_file():
            try:
                version = subprocess.run(
                    [str(python), '-c', 'import sys; print("%d.%d" % sys.version_info[:2])'],
                    capture_output=True, text=True, check=True, timeout=15,
                ).stdout.strip()
            except (OSError, subprocess.SubprocessError):
                raise ValueError('existing .venv-toolchain Python cannot be checked; preserve and review it before installation') from None
            if version != '3.11':
                raise ValueError('existing .venv-toolchain does not use Python 3.11; preserve it and rebuild a reviewed environment')
        else:
            if venv.exists() and any(venv.iterdir()):
                raise ValueError('existing incomplete .venv-toolchain requires manual review')
            tasks.append((ROOT, [sys.executable, '-m', 'venv', str(venv)]))
        tasks.append((ROOT, [str(python), '-m', 'pip', 'install', '-r', 'requirements-collection.txt']))
        tasks.append((ROOT, [str(python), '-m', 'pip', 'check']))
    if component in ('mcp', 'cli', 'ast', 'all'):
        node = select_node(ROOT, node)
        npm = npm_cli(node)
        version = subprocess.run([str(node), '--version'], text=True, capture_output=True, check=True, timeout=15).stdout.strip()
        if int(version.lstrip('v').split('.')[0]) < 24:
            raise ValueError('Node 24+ required by the tested MCP build')
        if component in ('mcp', 'all'):
            cwd = ROOT / 'vendor/js-reverse-mcp'
            tasks.extend([(cwd, [str(node), str(npm), 'ci', '--ignore-scripts', '--no-audit', '--no-fund']),
                          (cwd, [str(node), str(npm), 'run', 'prepare']),
                          (cwd, [str(node), str(npm), 'run', 'build'])])
        if component in ('cli', 'all'):
            cwd = ROOT / 'toolchain/playwright-cli'
            tasks.append((cwd, [str(node), str(npm), 'ci', '--ignore-scripts', '--no-audit', '--no-fund']))
            tasks.append((cwd, [str(node), str(cwd / 'node_modules/@playwright/cli/playwright-cli.js'), '--version']))
        if component in ('ast', 'all'):
            tasks.append((ROOT, [str(node), str(npm), 'ci', '--ignore-scripts', '--no-audit', '--no-fund']))
    return tasks


def component_fingerprint(component, node):
    paths = [ROOT / 'scripts/install_browser_toolchain.py']
    if component == 'python':
        paths += [ROOT / 'requirements-collection.txt']
        runtime = [sys.executable, sys.version]
    else:
        node = Path(node or shutil.which('node') or '').resolve()
        version = subprocess.run([str(node), '--version'], capture_output=True, text=True, check=True, timeout=15).stdout.strip()
        runtime = [str(node), version]
        folder = ROOT / {'mcp': 'vendor/js-reverse-mcp', 'cli': 'toolchain/playwright-cli', 'ast': '.'}[component]
        paths += [folder / 'package.json', folder / 'package-lock.json']
        if component == 'mcp':
            paths += [folder / 'tsconfig.json']
            paths += [p for part in ('src', 'scripts') for p in (folder / part).rglob('*') if p.is_file()]
    inventory = [(str(p.relative_to(ROOT)), hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(set(paths)) if p.is_file()]
    return hashlib.sha256(json.dumps([platform.system(), platform.machine(), runtime, inventory], sort_keys=True).encode()).hexdigest()


def component_ready(component, node):
    try:
        if component == 'python':
            python = ROOT / '.venv-toolchain' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
            commands = [[str(python), '-m', 'pip', 'check'], [str(python), '-c',
                        'import requests,httpx,curl_cffi,bs4,playwright.sync_api']]
            cwd = ROOT
        elif component == 'cli':
            cwd = ROOT / 'toolchain/playwright-cli'
            commands = [[str(node), str(cwd / 'node_modules/@playwright/cli/playwright-cli.js'), '--version']]
        else:
            cwd = ROOT / 'vendor/js-reverse-mcp' if component == 'mcp' else ROOT
            imports = "await import('@modelcontextprotocol/sdk/server/mcp.js'); await import('puppeteer')" if component == 'mcp' else "await import('@babel/parser'); await import('@babel/traverse'); await import('@babel/generator'); await import('@babel/types')"
            commands = [[str(node), '--input-type=module', '-e', imports]]
            if component == 'mcp':
                commands.append([str(node), '--check', str(cwd / 'build/src/index.js')])
        return all(subprocess.run(command, cwd=cwd, capture_output=True, timeout=60).returncode == 0 for command in commands)
    except (OSError, subprocess.SubprocessError):
        return False


def install_component(component, node):
    fingerprint = component_fingerprint(component, node)
    marker = ROOT / f'runs/_deployment/components/{component}.json'
    try:
        prior = json.loads(marker.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        prior = {}
    if prior.get('fingerprint') == fingerprint and component_ready(component, node):
        return {'component': component, 'action': 'reused'}
    marker.unlink(missing_ok=True)
    tasks = plans(component, node)
    environment = dict(os.environ, PUPPETEER_SKIP_DOWNLOAD='true', PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD='1', PYTHONIOENCODING='utf-8')
    if node:
        environment['PATH'] = str(Path(node).resolve().parent) + os.pathsep + environment.get('PATH', '')
    for cwd, command in tasks:
        subprocess.run(command, cwd=cwd, env=environment, check=True, timeout=1800, stdout=sys.stderr)
    if not component_ready(component, node):
        raise RuntimeError('component probe failed: ' + component)
    marker.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=marker.parent, delete=False) as stream:
        temporary = Path(stream.name)
        json.dump({'fingerprint': fingerprint, 'passed': True}, stream)
    try:
        os.replace(temporary, marker)
    finally:
        temporary.unlink(missing_ok=True)
    return {'component': component, 'action': 'installed'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--component', choices=('python', 'mcp', 'cli', 'ast', 'all'), default='all')
    parser.add_argument('--node', type=Path)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    try:
        tasks = plans(args.component, args.node)
        if not args.apply:
            print(json.dumps({'mode': 'plan', 'commands': [{'cwd': str(cwd), 'argv': command} for cwd, command in tasks]}, indent=2))
            return 0
        components = ('python', 'mcp', 'cli', 'ast') if args.component == 'all' else (args.component,)
        results = [install_component(component, args.node or shutil.which('node')) for component in components]
        print(json.dumps({'passed': True, 'installed_component': args.component, 'components': results,
                          'scope': 'packages/build only; browser, CDP and MCP require separate checks'}))
        return 0
    except Exception as error:
        print(json.dumps({'passed': False, 'error_type': type(error).__name__,
                          'error': str(error) if isinstance(error, ValueError) else 'installation_failed; inspect installer output'}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
