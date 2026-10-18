"""Plan or install isolated browser tooling. Explicit --apply is required for installation."""
from pathlib import Path
import argparse
import json
import os
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


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
        tasks.append((ROOT, [str(python), '-m', 'pip', 'install', '-r', 'requirements-collection.txt', '-r', 'requirements-dev.txt']))
        tasks.append((ROOT, [str(python), '-m', 'pip', 'check']))
    if component in ('mcp', 'cli', 'ast', 'all'):
        node = Path(node or shutil.which('node') or '').resolve()
        if not node.is_file():
            raise ValueError('provide an existing Node 24+ executable with --node')
        npm = node.parent / 'node_modules/npm/bin/npm-cli.js'
        if not npm.is_file():
            raise ValueError('npm-cli.js missing next to the supplied Node; use a complete Node installation')
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
        environment = dict(os.environ, PUPPETEER_SKIP_DOWNLOAD='true', PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD='1', PYTHONIOENCODING='utf-8')
        if args.node:
            environment['PATH'] = str(args.node.resolve().parent) + os.pathsep + environment['PATH']
        for cwd, command in tasks:
            subprocess.run(command, cwd=cwd, env=environment, check=True)
        print(json.dumps({'passed': True, 'installed_component': args.component,
                          'scope': 'packages/build only; browser, CDP and MCP require separate checks'}))
        return 0
    except Exception as error:
        print(json.dumps({'passed': False, 'error_type': type(error).__name__,
                          'error': str(error) if isinstance(error, ValueError) else 'installation_failed; inspect installer output'}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
