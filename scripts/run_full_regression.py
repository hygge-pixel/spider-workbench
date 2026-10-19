"""Verify delivery and, in a source checkout, run maintained developer suites."""
from pathlib import Path
import argparse
import json
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def verify_source(root):
    from scripts.check_public_release import scan
    root = Path(root)
    report = scan(root)
    if not report['passed']:
        raise ValueError('source_release_checks_failed; run scripts/check_public_release.py for locations')
    manifest = json.loads((root / 'MANIFEST.sha256.json').read_text(encoding='utf-8'))
    python_count = json_count = 0
    for name in manifest['files']:
        path = root / name
        if path.suffix == '.py':
            compile(path.read_text(encoding='utf-8-sig'), name, 'exec')
            python_count += 1
        elif path.suffix == '.json':
            json.loads(path.read_text(encoding='utf-8-sig'))
            json_count += 1
    return {'passed': True, 'source_files': len(manifest['files']) + 1,
            'python_sources': python_count, 'json_files': json_count}


def verify_workspace(root, node=None):
    from spider_core.project_runtime import select_node
    from scripts.browser_toolchain import stdio_smoke
    from bootstrap import onboard
    root = Path(root).resolve()
    source = verify_source(root)
    selected = select_node(root, node)
    environment = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1')
    manifest = json.loads((root / 'MANIFEST.sha256.json').read_text(encoding='utf-8'))
    javascript_count = 0
    for name in manifest['files']:
        if Path(name).suffix in {'.js', '.mjs', '.cjs'}:
            result = subprocess.run([str(selected), '--check', str(root / name)], cwd=root, env=environment,
                                    capture_output=True, timeout=30)
            if result.returncode:
                raise ValueError('javascript_syntax_failed: ' + name)
            javascript_count += 1
    demo = onboard(root)
    if demo.get('demo', {}).get('records') != 3 or demo['demo'].get('validation_passed') is not True:
        raise ValueError('offline_example_validation_failed')
    entry = root / 'vendor/js-reverse-mcp/build/src/index.js'
    if entry.is_file():
        mcp = stdio_smoke(root, selected)
    else:
        mcp = {'status': 'not_installed', 'passed': None,
               'next_action': 'Agent installs the MCP component, then repeats deployment acceptance'}
    return {'passed': True, 'scope': 'delivered source, syntax, metadata, Skill discovery and offline runner contract',
            'source': source, 'javascript_sources': javascript_count,
            'offline_records': 3, 'offline_validation_passed': True,
            'skill_discovery_created': demo['skill_discovery_links_created'], 'mcp_stdio': mcp,
            'developer_test_suite_distributed': (root / 'tests/test_framework_contract.py').is_file(),
            'developer_tests_run': False,
            'browser_connection_verified': False, 'host_tool_call_passed': None,
            'external_targets_tested': False}


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--node', help='optional runtime override; defaults to the project configuration')
    parser.add_argument('--delivery-only', action='store_true',
                        help='deployment acceptance without contributor test suites')
    args = parser.parse_args()
    try:
        result = verify_workspace(ROOT, args.node)
        manifest = json.loads((ROOT/'MANIFEST.sha256.json').read_text(encoding='utf-8'))
        is_source = manifest.get('distribution_kind', 'source') == 'source'
        if is_source and not args.delivery_only:
            from spider_core.project_runtime import select_node
            subprocess.run([sys.executable, str(ROOT/'scripts/run_developer_tests.py'),
                            '--node', str(select_node(ROOT, args.node))], cwd=ROOT, check=True)
            result['developer_tests_run'] = True
            result['scope'] += '; maintained developer regression suites'
    except Exception as error:
        from scripts.deploy import diagnostic
        print(json.dumps({'passed': False, **diagnostic(error)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    from spider_core.project_runtime import reexec_project
    reexec_project(ROOT)
    raise SystemExit(main())
