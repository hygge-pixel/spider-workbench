"""Run every packaged test suite without installing dependencies or launching browsers."""
from pathlib import Path
import argparse
import ast
import importlib.util
import json
import os
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
EXCLUDED = {'node_modules', '.venv', '__pycache__', '.git', 'tmp', 'runs', 'outputs'}


def files(directory, pattern):
    return sorted(p for p in (ROOT / directory).rglob(pattern)
                  if not EXCLUDED.intersection(p.relative_to(ROOT).parts))


def requires_pytest(path):
    tree = ast.parse(Path(path).read_text(encoding='utf-8-sig'))
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    unittest_names = {'TestCase', 'IsolatedAsyncioTestCase'}
    for _ in classes:
        for node in classes:
            bases = {getattr(base, 'attr', getattr(base, 'id', '')) for base in node.bases}
            if bases.intersection(unittest_names):
                unittest_names.add(node.name)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith('test_'):
            return True
        if isinstance(node, ast.ClassDef) and node.name not in unittest_names:
            if any(isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                   and child.name.startswith('test_') for child in node.body):
                return True
        if isinstance(node, ast.ImportFrom) and (node.module or '').startswith('pytest'):
            return True
        if isinstance(node, ast.Import) and any(item.name == 'pytest' for item in node.names):
            return True
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--node', help='existing Node executable for discovered Node tests')
    args = parser.parse_args()
    environment = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1')
    from spider_core.project_runtime import select_node
    try:
        selected_node = select_node(ROOT, args.node)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        parser.error(str(error))
    args.node = str(selected_node)
    environment['PATH'] = str(selected_node.parent) + os.pathsep + environment.get('PATH', '')
    def stage(label, command, env=None):
        print(f'[{label}]', flush=True)
        subprocess.run(command, cwd=ROOT, env=env or environment, check=True)
    def suite(label, directory, paths, env=None):
        if any(requires_pytest(path) for path in paths):
            if importlib.util.find_spec('pytest') is None:
                raise ValueError('pytest-style tests discovered; install pytest in the selected Python environment; no tests were silently omitted')
            stage(label, [sys.executable, '-m', 'pytest', '--import-mode=importlib', '-p', 'no:cacheprovider', '-v', *map(str, paths)], env)
        else:
            stage(label, [sys.executable, '-m', 'unittest', 'discover', '-s', str(directory), '-v'], env)
    try:
        suite('framework-tests', ROOT / 'tests', files('tests', 'test_*.py'))
        groups = sorted({p.parent for p in files('experiments', 'test_*.py')})
        for group in groups:
            env = dict(environment)
            env['PYTHONPATH'] = os.pathsep.join([str(group), str(ROOT), environment.get('PYTHONPATH', '')])
            suite('experiment-tests', group, sorted(group.glob('test_*.py')), env)
        selftest = ROOT / 'skills/web-reverse-master/scripts/selftest.py'
        if selftest.is_file():
            stage('skill-selftest', [sys.executable, str(selftest)])
        node_tests = files('skills', '*.test.js') + files('experiments', '*.test.js')
        if node_tests:
            node = args.node or shutil.which('node')
            if not node:
                raise ValueError('Node tests discovered but Node is missing')
            stage('node-tests', [node, '--test', *map(str, node_tests)])
        else:
            print('[node-tests] no Node test files in this framework edition', flush=True)
        if (ROOT / 'vendor/js-reverse-mcp/build/src/McpContext.js').is_file():
            stage('mcp-lifecycle', [args.node, '--test', str(ROOT / 'tests/mcp_lifecycle.test.mjs')])
        else:
            print('[mcp-lifecycle] build not installed; covered by separate mcp-build CI job', flush=True)
        count = 0
        for directory in ('spider_core', 'scripts', 'tools', 'tests', 'experiments', 'platforms', 'skills'):
            for path in files(directory, '*.py'):
                compile(path.read_text(encoding='utf-8-sig'), str(path), 'exec')
                count += 1
        compile((ROOT / 'spider.py').read_text(encoding='utf-8-sig'), str(ROOT / 'spider.py'), 'exec')
        bootstrap = ROOT / 'bootstrap.py'
        if bootstrap.is_file():
            compile(bootstrap.read_text(encoding='utf-8-sig'), str(bootstrap), 'exec')
            count += 1
        print(f'[compile] {count + 1} Python sources passed', flush=True)
        # An archive has no .git. Do not accidentally inspect a parent repository.
        if (ROOT / '.git').exists() and shutil.which('git'):
            stage('whitespace', ['git', 'diff', '--check'])
        else:
            print('[whitespace] archive has no local Git metadata; Git check not applicable', flush=True)
    except (subprocess.CalledProcessError, OSError, ValueError, SyntaxError) as error:
        print(json.dumps({'passed': False, 'error': str(error)}, ensure_ascii=False), flush=True)
        return 1
    print(json.dumps({'passed': True, 'scope': 'packaged offline framework suites'}, ensure_ascii=False), flush=True)
    return 0


if __name__ == '__main__':
    from spider_core.project_runtime import reexec_project
    reexec_project(ROOT)
    raise SystemExit(main())
