"""Select the local tool Python consistently without modifying system PATH."""
import json
import os
from pathlib import Path
import subprocess
import sys
import shutil


def npm_cli(node):
    node = Path(node).resolve()
    choices = (node.parent / 'node_modules/npm/bin/npm-cli.js',
               node.parent.parent / 'lib/node_modules/npm/bin/npm-cli.js')
    for path in choices:
        if path.is_file():
            return path
    raise ValueError('node_npm_missing; use a complete Node distribution')


def select_node(root, explicit=None):
    """Explicit > environment > project configuration > PATH; never replace a broken pin silently."""
    root = Path(root).resolve()
    settings = root / 'config/agent_tools.local.json'
    configured = json.loads(settings.read_text(encoding='utf-8')).get('browser_toolchain', {}).get('node_executable') if settings.is_file() else None
    value = explicit or os.environ.get('SPIDER_NODE') or configured or shutil.which('node')
    if not value or not Path(value).is_file():
        raise ValueError('node_executable_missing; run scripts/setup_runtime.ps1 or select --node')
    selected = Path(value).resolve()
    result = subprocess.run([str(selected), '--version'], capture_output=True, text=True, check=True, timeout=15)
    if int(result.stdout.strip().lstrip('v').split('.')[0]) < 24:
        raise ValueError('node_version_too_old; Node 24+ required; run scripts/setup_runtime.ps1')
    npm_cli(selected)
    return selected


def select_python(root, explicit=None):
    explicit = explicit or os.environ.get('SPIDER_PYTHON')
    root = Path(root).resolve()
    config = root / 'config/agent_tools.local.json'
    if explicit:
        selected = Path(explicit)
    elif config.is_file():
        settings = json.loads(config.read_text(encoding='utf-8'))
        configured = settings.get('browser_toolchain', {}).get('python_executable')
        selected = Path(configured) if configured else Path(sys.executable)
    else:
        candidate = root / '.venv-toolchain' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        selected = candidate if candidate.is_file() else Path(sys.executable)
    selected = selected.resolve()
    if not selected.is_file():
        raise ValueError('configured project Python is missing; preserve configuration and select Python 3.11 explicitly')
    version = subprocess.run([str(selected), '-c', 'import sys; print("%d.%d" % sys.version_info[:2])'],
                             capture_output=True, text=True, check=True, timeout=15).stdout.strip()
    if version != '3.11':
        raise ValueError('selected project Python must be 3.11')
    return selected


def reexec_project(root):
    if os.environ.get('SPIDER_PROJECT_PYTHON_SELECTED') == '1':
        return
    selected = select_python(root)
    if os.path.normcase(str(selected)) != os.path.normcase(str(Path(sys.executable).resolve())):
        environment = dict(os.environ, SPIDER_PROJECT_PYTHON_SELECTED='1', PYTHONIOENCODING='utf-8')
        raise SystemExit(subprocess.call([str(selected), *sys.argv], env=environment))
