"""Agent-operated, resumable deployment. No Git operations or user-global configuration edits."""
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import socket
import subprocess
import sys
import tempfile
import uuid
import time
import re
from urllib.error import URLError, HTTPError
import ssl

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.setup_chrome import atomic_json, installation_lock, OfficialDownloadError
from scripts.verify_distribution import verify_installation
from spider_core.project_runtime import select_python, npm_cli
from spider_core.browser import WorkspaceBrowserError

TECHNICAL_STAGES = ('preflight', 'core', 'dependencies', 'browser_install', 'configuration',
                    'browser_connection', 'mcp_stdio', 'mcp_read_only', 'playwright_cdp', 'regression')


class StageFailure(RuntimeError):
    def __init__(self, code, exit_code=None):
        super().__init__(code)
        self.code, self.exit_code = code, exit_code


def diagnostic(error):
    if isinstance(error, (StageFailure, WorkspaceBrowserError, OfficialDownloadError)):
        code = error.code
    elif isinstance(error, HTTPError):
        code = 'official_http_error_' + str(error.code)
    elif isinstance(error, URLError):
        code = 'network_tls_verification_failed' if isinstance(error.reason, ssl.SSLError) else 'network_connection_failed'
    elif isinstance(error, ValueError) and str(error).split(';')[0] in {'node_executable_missing', 'node_version_too_old', 'node_npm_missing'}:
        code = str(error).split(';')[0]
    elif isinstance(error, subprocess.TimeoutExpired):
        code = 'command_timeout'
    elif isinstance(error, subprocess.CalledProcessError):
        code = 'command_failed'
    else:
        code = 'stage_failed; review_preserved_configuration_and_stage_guide'
    return {'error_type': type(error).__name__, 'code': code,
            'exit_code': getattr(error, 'exit_code', getattr(error, 'returncode', None))}


def command(root, argv, *, json_result=True, timeout=120):
    env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1')
    process = subprocess.run(list(map(str, argv)), cwd=root, env=env, capture_output=True,
                             text=True, encoding='utf-8', errors='replace', timeout=timeout,
                             creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if process.returncode:
        category = 'command_failed'
        try:
            child = json.loads(process.stdout)
            known = {'MCP read-only browser call failed; raw payload withheld': 'mcp_read_only_tool_failed',
                     'MCP response timeout': 'mcp_response_timeout',
                     'MCP process ended before response': 'mcp_process_ended',
                     'expected browser tool list missing': 'mcp_expected_tools_missing'}
            if isinstance(child, dict):
                category = known.get(child.get('error'), category)
        except (ValueError, TypeError):
            pass
        raise StageFailure(category, process.returncode)
    if not json_result:
        output = process.stdout + '\n' + process.stderr
        result = {'passed': True, 'exit_code': 0}
        # Persist counts only, not arbitrary output from tests or tools.
        for label, pattern in [('python_tests', r'Ran (\d+) tests'), ('python_sources', r'\[compile\] (\d+)'),
                               ('skill_cases', r'\[SUMMARY\] all (\d+) cases passed')]:
            match = re.search(pattern, output)
            if match:
                result[label] = int(match[1])
        return result
    try:
        result = json.loads(process.stdout)
    except ValueError:
        raise StageFailure('expected_json_missing') from None
    if not isinstance(result, dict) or result.get('passed', result.get('ok', True)) is False:
        raise StageFailure('command_reported_failure')
    return result


class Deployment:
    def __init__(self, root, *, existing=None):
        self.root = Path(root).resolve()
        if existing is not None:
            self.report = existing
            return
        previous = self.root / 'outputs/deployment_acceptance.json'
        if previous.is_file():
            prior = json.loads(previous.read_text(encoding='utf-8'))
            if prior.get('schema_version') != 1 or not isinstance(prior.get('stages'), dict):
                raise StageFailure('legacy_deployment_report_requires_backup_and_review')
            identifier = str(uuid.UUID(prior['attempt_id']))
            atomic_json(self.root / f'runs/_deployment/attempts/{identifier}.json', prior)
        self.report = {'schema_version': 1, 'attempt_id': str(uuid.uuid4()),
                       'started_at': datetime.now(timezone.utc).isoformat(), 'passed': False,
                       'status': 'running', 'stages': {}, 'host_tool_call_passed': None,
                       'external_targets_tested': False, 'next_action': 'continue deployment stages'}

    def save(self):
        output = self.root / 'outputs/deployment_acceptance.json'
        atomic_json(output, self.report)
        lines = ['# 本机部署验收', '', f"状态：{self.report['status']}；完整通过：{self.report['passed']}", '',
                 '| 阶段 | 状态 |', '|---|---|']
        lines += [f"| {name} | {item['status']} |" for name, item in self.report['stages'].items()]
        lines += ['', '下一步：' + self.report['next_action'], '',
                  '宿主实际调用：' + str(self.report['host_tool_call_passed']), '',
                  '本报告不包含真实网站采集验收。详细版本、路径和脱敏诊断见同名 JSON。', '']
        text = '\n'.join(lines)
        md = output.with_suffix('.md')
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=md.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(text)
        try:
            os.replace(temporary, md)
        finally:
            temporary.unlink(missing_ok=True)

    def stage(self, name, operation):
        started = time.monotonic()
        print('[deployment] ' + name, file=sys.stderr, flush=True)
        self.report['stages'][name] = {'status': 'running'}
        self.save()
        try:
            result = operation()
            if not isinstance(result, dict) or result.get('passed', result.get('ok', True)) is False:
                raise StageFailure('stage_reported_failure')
            self.report['stages'][name] = {'status': 'passed', 'result': result, 'elapsed_seconds': round(time.monotonic() - started, 3)}
            self.save()
            return result
        except Exception as error:
            self.report['stages'][name] = dict(status='failed', elapsed_seconds=round(time.monotonic() - started, 3), **diagnostic(error))
            self.report.update(status='failed', passed=False, next_action=f'resolve {name}; rerun apply to reuse verified components')
            self.save()
            raise

    def finish(self):
        technical = all(self.report['stages'].get(name, {}).get('status') == 'passed' for name in TECHNICAL_STAGES)
        self.report.update(technical_passed=technical, passed=False, status='host_pending' if technical else 'incomplete',
                           next_action='host: merge generated definition, verify effective config and call list_pages in the actual session; then accept-host')
        self.save()


def host_definition_matches(transport, expected, root):
    return (transport.get('command') == expected['command'] and transport.get('args') == expected['args']
            and transport.get('cwd') in (None, str(root)))


def preflight(root, node=None, codex=None):
    root = Path(root).resolve()
    if sys.version_info[:2] != (3, 11):
        raise StageFailure('python_311_required; select_or_install_side_by_side')
    integrity = verify_installation(root)
    if not integrity['passed']:
        raise StageFailure('source_integrity_failed; review_exact_local_patches')
    from bootstrap import resolve_node
    selected = resolve_node(node, root)
    npm = npm_cli(selected)
    version = subprocess.run([str(selected), '--version'], capture_output=True, text=True, check=True, timeout=15).stdout.strip()
    with tempfile.TemporaryDirectory(prefix='spider-node-preflight-') as directory:
        probe = Path(directory) / 'probe.ts'
        probe.write_text('const value: number = 42; console.log(value);', encoding='utf-8')
        result = subprocess.run([str(selected), '--experimental-strip-types', str(probe)],
                                capture_output=True, text=True, timeout=20)
        if result.returncode or result.stdout.strip() != '42':
            raise StageFailure('node_typescript_probe_failed; select_another_compatible_node', result.returncode)
    command(root, [selected, npm, '--version'], json_result=False, timeout=20)
    python = select_python(root)
    if platform.system() != 'Windows':
        raise StageFailure('windows_browser_identity_baseline_required; offline_bootstrap_remains_available')
    config = root / 'config/workspace_browser.json'
    occupied = False
    for address in ('127.0.0.1', '::1'):
        try:
            with socket.create_connection((address, 9222), timeout=.3):
                occupied = True
        except OSError:
            pass
    if occupied:
        if not config.is_file():
            raise StageFailure('cdp_port_9222_owned_by_other_session; preserve_it')
        from spider_core.browser import status_browser_candidate
        status_browser_candidate(root, 'chrome')
    host = {'status': 'agent_must_check_native_host_config_and_trust', 'effective_config_passed': None}
    if codex:
        # This checks CLI compatibility/effective config, never edits trust, models or approval settings.
        cli_version = command(root, [codex, '--version'], json_result=False, timeout=20)
        result = subprocess.run([str(codex), 'mcp', 'get', 'js-reverse', '--json'], cwd=root,
                                capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30)
        host.update(cli=str(Path(codex).resolve()), cli_launch_passed=cli_version['passed'])
        if result.returncode:
            # mcp list validates host config even when this project's service has not been added yet.
            command(root, [codex, 'mcp', 'list', '--json'], json_result=False, timeout=30)
            host['status'] = 'project_mcp_missing_or_not_trusted; agent_must_resolve'
        else:
            data = json.loads(result.stdout)
            transport = data.get('transport', data)
            from scripts.browser_toolchain import build_definitions
            from bootstrap import tool_python
            expected = build_definitions(root, tool_python(root), node=selected)['js-reverse']
            matches = host_definition_matches(transport, expected, root)
            host.update(status='project_launcher_visible' if matches else 'other_mcp_definition_visible; check_project_trust',
                        effective_config_passed=matches)
    return {'passed': True, 'python': str(python), 'python_version': '3.11', 'node': str(selected),
            'node_version': version, 'native_typescript_probe': True, 'source': integrity,
            'host': host, 'cdp_port_occupied': occupied, 'system': platform.system(), 'architecture': platform.machine()}


def ensure_browser_install(root):
    from scripts import setup_chrome
    from spider_core.browser import load_workspace_browser_configs
    config = root / 'config/workspace_browser.json'
    if config.exists():
        pool = load_workspace_browser_configs(root)
        browser = pool.candidates['chrome']
        if not browser.executable.is_file():
            raise StageFailure('configured_browser_missing; preserve_and_review_configuration')
        version = setup_chrome.program_version(browser.executable)
        return {'passed': True, 'action': 'reused_configured_browser', 'executable': str(browser.executable),
                'version': version, 'source': 'existing_configuration; provenance_requires_existing_receipt',
                'auto_upgraded': False}
    asset = setup_chrome.latest_asset()
    result = setup_chrome.install(root, asset)
    from scripts.agent_platform_compat import configure_browser
    configure_browser(root, 'chrome', Path(result['executable']))
    return dict(result, passed=True)


def apply(root, node=None, codex=None):
    root = Path(root).resolve()
    with installation_lock(root):
        deployment = Deployment(root)
        checked = deployment.stage('preflight', lambda: preflight(root, node, codex))
        from bootstrap import onboard, tool_python
        deployment.stage('core', lambda: onboard(root))
        selected = Path(checked['node'])
        from scripts import install_browser_toolchain as installer
        def dependencies():
            # This module is also importable from tests; retain the explicit caller workspace.
            previous = installer.ROOT
            try:
                installer.ROOT = root
                return {'passed': True, 'components': [installer.install_component(name, selected) for name in ('python', 'mcp', 'cli', 'ast')]}
            finally:
                installer.ROOT = previous
        deployment.stage('dependencies', dependencies)
        python = tool_python(root)
        deployment.stage('browser_install', lambda: ensure_browser_install(root))
        deployment.stage('configuration', lambda: command(root, [python, 'scripts/browser_toolchain.py', 'configure', '--python', python, '--node', selected]))
        generated = root / 'runs/_mcp/generated/mcp_config.json'
        deployment.report['configuration_sha256'] = hashlib.sha256(generated.read_bytes()).hexdigest()
        deployment.report['source_sha256'] = source_fingerprint(root)
        steps = [
            ('browser_connection', [python, 'spider.py', 'browser', 'ensure', '--json']),
            ('mcp_stdio', [python, 'scripts/browser_toolchain.py', 'mcp-smoke', '--candidate', 'chrome', '--stdio-only']),
            ('mcp_read_only', [python, 'scripts/browser_toolchain.py', 'mcp-smoke', '--candidate', 'chrome']),
            ('playwright_cdp', [python, 'scripts/browser_toolchain.py', 'cdp-smoke', '--candidate', 'chrome']),
            ('regression', [python, 'scripts/run_full_regression.py', '--delivery-only', '--node', selected])]
        for name, argv in steps:
            deployment.stage(name, lambda argv=argv, name=name: command(root, argv, timeout=1800 if name == 'regression' else 150))
        deployment.finish()
        return deployment.report


def source_fingerprint(root):
    manifest = json.loads((root / 'MANIFEST.sha256.json').read_text(encoding='utf-8'))
    digest = hashlib.sha256()
    digest.update((root / 'MANIFEST.sha256.json').read_bytes())
    for name in sorted(manifest['files']):
        digest.update(name.encode())
        digest.update(hashlib.sha256((root / name).read_bytes()).digest())
    for name in ('config/agent_tools.local.json', 'config/workspace_browser.json', 'config/source_patches.local.json'):
        path = root / name
        digest.update(name.encode())
        digest.update(hashlib.sha256(path.read_bytes()).digest() if path.is_file() else b'missing')
    return digest.hexdigest()


def accept_host(root, evidence_path):
    """Consume a sanitized Agent-observed call attestation, not a bare success switch."""
    report = json.loads((root / 'outputs/deployment_acceptance.json').read_text(encoding='utf-8'))
    evidence = json.loads(Path(evidence_path).read_text(encoding='utf-8'))
    required = {'attempt_id', 'configuration_sha256', 'host', 'host_version', 'session_id', 'tool_name',
                'observed_at', 'tool_call_passed', 'effective_config_passed', 'provenance'}
    if set(evidence) != required or not report.get('technical_passed'):
        raise StageFailure('host_attestation_schema_or_technical_checks_incomplete')
    if (evidence['attempt_id'] != report['attempt_id'] or evidence['configuration_sha256'] != report['configuration_sha256']
            or evidence['tool_call_passed'] is not True or evidence['effective_config_passed'] is not True
            or evidence['tool_name'] != 'list_pages' or evidence['provenance'] != 'agent_observed_call'
            or not all(isinstance(evidence[key], str) and 0 < len(evidence[key]) <= 256 for key in required - {'tool_call_passed', 'effective_config_passed'})):
        raise StageFailure('host_attestation_does_not_match_current_deployment')
    observed = datetime.fromisoformat(evidence['observed_at'])
    started = datetime.fromisoformat(report['started_at'])
    now = datetime.now(timezone.utc)
    if observed.tzinfo is None or not started <= observed <= now or (now - started).total_seconds() > 86400:
        raise StageFailure('host_evidence_expired; rerun_apply')
    generated = root / 'runs/_mcp/generated/mcp_config.json'
    if (hashlib.sha256(generated.read_bytes()).hexdigest() != report['configuration_sha256']
            or source_fingerprint(root) != report['source_sha256']):
        raise StageFailure('deployment_changed_since_checks; rerun_apply')
    from spider_core.browser import status_browser_candidate
    status_browser_candidate(root, 'chrome')
    deployment = Deployment(root, existing=report)
    deployment.report.update(host_tool_call_passed=True, host_evidence=evidence,
                             host_evidence_scope='attestation recorded by the Agent that observed the actual host call',
                             passed=True, status='completed', next_action='deployment accepted; run business tasks through spider.py run')
    deployment.save()
    return deployment.report


def deployment_status(root):
    """Read-only live check; immutable saved acceptance remains explicitly historical."""
    root = Path(root)
    path = root / 'outputs/deployment_acceptance.json'
    historical = json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {'passed': False, 'status': 'not_deployed'}
    from spider_core.browser import status_browser_candidate
    try:
        browser = status_browser_candidate(root, 'chrome')
        runtime_python = select_python(root)
        from spider_core.project_runtime import select_node
        runtime_node = select_node(root)
        mcp = command(root, [runtime_python, 'scripts/browser_toolchain.py', 'mcp-smoke', '--candidate', 'chrome'], timeout=70)
        live = {'passed': True, 'browser': browser, 'mcp_read_only': mcp, 'python': str(runtime_python),
                'node': str(runtime_node), 'mcp_host_call': 'not_retested'}
        if historical.get('source_sha256') and source_fingerprint(root) != historical['source_sha256']:
            live.update(passed=False, code='deployment_changed_since_acceptance')
    except (WorkspaceBrowserError, StageFailure, OSError, ValueError, subprocess.SubprocessError) as error:
        live = {'passed': False, **diagnostic(error), 'mcp_host_call': 'not_retested'}
    live['checked_at'] = datetime.now(timezone.utc).isoformat()
    next_action = (historical.get('next_action', 'run apply') if live['passed'] else
                   'run spider.py browser ensure --json; reconnect host MCP; call list_pages')
    if live.get('code') in {'browser_ownership_permission_denied', 'browser_ownership_unverified'}:
        next_action = ('verify process-inspection permissions in the intended host context, then rerun status; '
                       'ownership is unverified; preserve browser and ACL; do not bypass checks or reinstall')
    return {'passed': bool(historical.get('passed') and live['passed']),
            'last_acceptance': historical, 'live_health': live,
            'next_action': next_action}


def main():
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, 'reconfigure', None)
        if callable(reconfigure):
            reconfigure(encoding='utf-8', errors='replace')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('preflight', 'apply', 'status', 'accept-host'))
    parser.add_argument('--node', type=Path)
    parser.add_argument('--codex', type=Path, help='optional actual compatible Codex CLI; other hosts are checked by their Agent')
    parser.add_argument('--evidence', type=Path, help='sanitized observed host call attestation for accept-host')
    args = parser.parse_args()
    try:
        if args.action == 'status':
            result = deployment_status(ROOT)
        elif args.action == 'preflight':
            result = preflight(ROOT, args.node, args.codex)
        elif args.action == 'accept-host':
            if not args.evidence:
                parser.error('accept-host requires --evidence')
            result = accept_host(ROOT, args.evidence)
        else:
            result = apply(ROOT, args.node, args.codex)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get('passed') else 2
    except Exception as error:
        print(json.dumps(dict(passed=False, **diagnostic(error)), ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
