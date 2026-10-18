"""Configure and verify the project's browser/MCP layer without collecting site data."""
from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def write_json(path, value):
    path = Path(path)
    path.resolve().relative_to(ROOT.resolve())
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def build_definitions(root, python, candidates=('chrome', 'cloak'), *, node=None):
    if node is None:
        raise ValueError('Node executable required for the single-process MCP launcher')
    names = {'chrome': 'js-reverse', 'cloak': 'js-reverse-cloak'}
    return {names[candidate]: {'command': str(node),
            'args': [str(Path(root) / 'scripts/start_js_reverser.mjs'), '--python', str(python), '--candidate', candidate]}
            for candidate in candidates}


def merge_definitions(existing, definitions, *, replace_managed=False):
    merged = copy.deepcopy(existing)
    servers = merged.setdefault('mcpServers', {})
    if not isinstance(servers, dict):
        raise ValueError('existing mcpServers must be an object')
    for name, definition in definitions.items():
        if name in servers and servers[name] != definition and not replace_managed:
            raise ValueError('managed MCP name conflict; review before --replace-managed: ' + name)
        servers[name] = copy.deepcopy(definition)
    return merged


def probe_stdio(command, cwd, env, *, live=False, timeout=45):
    """Initialize MCP, list tools, and optionally call list_pages. Never return tool payloads."""
    process = subprocess.Popen(command, cwd=cwd, env=dict(os.environ, **env),
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, encoding='utf-8', errors='replace', bufsize=1,
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    messages = queue.Queue()
    def read_stdout():
        for line in process.stdout:
            try:
                messages.put(json.loads(line))
            except ValueError:
                continue
        messages.put(None)
    def drain_stderr():
        for _ in process.stderr:
            pass  # Do not persist arbitrary tool logs or private page data.
    threading.Thread(target=read_stdout, daemon=True).start()
    threading.Thread(target=drain_stderr, daemon=True).start()
    def request(identifier, method, params):
        process.stdin.write(json.dumps({'jsonrpc': '2.0', 'id': identifier, 'method': method, 'params': params}) + '\n')
        process.stdin.flush()
        deadline = time.monotonic() + timeout
        while True:
            try:
                response = messages.get(timeout=max(.01, deadline - time.monotonic()))
            except queue.Empty:
                raise RuntimeError('MCP response timeout') from None
            if response is None:
                raise RuntimeError('MCP process ended before response')
            if response.get('id') != identifier:
                if time.monotonic() > deadline:
                    raise RuntimeError('MCP response timeout')
                continue
            if 'error' in response:
                raise RuntimeError('MCP protocol returned an error; raw payload withheld')
            return response['result']
    try:
        initialized = request(1, 'initialize', {'protocolVersion': '2024-11-05',
            'capabilities': {}, 'clientInfo': {'name': 'spider-framework-probe', 'version': '2.0'}})
        process.stdin.write('{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
        process.stdin.flush()
        listed = request(2, 'tools/list', {})
        tools = listed.get('tools', [])
        names = {tool.get('name') for tool in tools}
        if not tools or 'list_pages' not in names:
            raise RuntimeError('expected browser tool list missing')
        if live:
            called = request(3, 'tools/call', {'name': 'list_pages', 'arguments': {}})
            if called.get('isError'):
                raise RuntimeError('MCP read-only browser call failed; raw payload withheld')
        return {'passed': True, 'protocol_initialized': True, 'tools': len(tools),
                'server_version': initialized.get('serverInfo', {}).get('version'),
                'read_only_tool_passed': bool(live),
                'scope': 'MCP initialization and list_pages' if live else 'MCP stdio only; browser not verified'}
    finally:
        try:
            process.stdin.close()
        except (OSError, ValueError):
            pass
        if process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill(); process.wait(timeout=5)
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream:
                stream.close()


def local_settings():
    path = ROOT / 'config/agent_tools.local.json'
    if not path.is_file():
        raise ValueError('run browser_toolchain.py configure first')
    return json.loads(path.read_text(encoding='utf-8'))['browser_toolchain']


def launch_spec(candidate):
    from spider_core.browser import load_workspace_browser_configs
    pool = load_workspace_browser_configs(ROOT)
    browser = pool.candidates[candidate]
    settings = local_settings()
    node, entry = Path(settings['node_executable']), Path(settings['js_reverser_entry'])
    if not node.is_file() or not entry.is_file():
        raise ValueError('configured Node or built JSReverser entry is missing')
    runtime = ROOT / 'runs/_mcp' / ('js-reverse-cloak' if candidate == 'cloak' else 'js-reverse')
    env = {'SPIDER_MCP_RUN_DIR': str(runtime), 'REMOTE_DEBUGGING_URL': browser.cdp_url,
           'REMOTE_DEBUGGING_PORT': str(9232 if candidate == 'cloak' else 9222)}
    return [str(node), str(entry), '--browserUrl', browser.cdp_url], runtime, env


def configure(python, node, entry, *, write_project=False, replace_managed=False):
    python, node, entry = Path(python).resolve(), Path(node).resolve(), Path(entry).resolve()
    if not all(path.is_file() for path in (python, node, entry)):
        raise ValueError('Python, Node and built JSReverser entry must be existing files')
    version = subprocess.run([str(node), '--version'], capture_output=True, text=True, check=True).stdout.strip()
    if int(version.lstrip('v').split('.')[0]) < 24:
        raise ValueError('Node 24+ is required by this tested toolchain')
    definitions = build_definitions(ROOT, python, node=node)
    generated = ROOT / 'runs/_mcp/generated/mcp_config.json'
    destinations = []
    if write_project:
        for relative in ('.mcp.json', '.agents/mcp_config.json', '.gemini/settings.json'):
            path = ROOT / relative
            data = json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {}
            destinations.append((path, merge_definitions(data, definitions, replace_managed=replace_managed)))
    config = ROOT / 'config/agent_tools.local.json'
    data = json.loads(config.read_text(encoding='utf-8')) if config.is_file() else {}
    managed = {'python_executable': str(python), 'node_executable': str(node), 'js_reverser_entry': str(entry)}
    if 'browser_toolchain' in data and data['browser_toolchain'] != managed and not replace_managed:
        raise ValueError('existing toolchain settings differ; review before --replace-managed')
    data['browser_toolchain'] = managed
    write_json(config, data)
    write_json(generated, {'mcpServers': definitions})
    for path, content in destinations:
        write_json(path, content)
    return {'passed': True, 'generated': str(generated),
            'project_configs_merged': [str(path.relative_to(ROOT)) for path, _ in destinations],
            'note': 'No user-global host configuration is changed; reconnect the target Agent and verify tools.'}


def cdp_smoke(candidate):
    from spider_core.browser import load_workspace_browser_configs, status_browser_candidate
    status_browser_candidate(ROOT, candidate)  # Verify executable/profile ownership before attachment.
    from playwright.sync_api import sync_playwright
    cdp = load_workspace_browser_configs(ROOT).candidates[candidate].cdp_url
    with sync_playwright() as playwright:
        browser = playwright.chromium.connect_over_cdp(cdp, timeout=15000)
        if not browser.contexts:
            raise RuntimeError('CDP context missing')
        page = browser.contexts[0].new_page()
        try:
            page.goto('data:text/html,<title>Spider CDP smoke</title><div id="probe">framework-ok</div>',
                      wait_until='domcontentloaded', timeout=15000)
            if page.locator('#probe').inner_text(timeout=15000) != 'framework-ok':
                raise RuntimeError('CDP synthetic page mismatch')
        finally:
            page.close()  # Close only our synthetic tab; do not close the shared browser.
    return {'passed': True, 'candidate': candidate, 'profile_checked': True,
            'synthetic_page_verified': True, 'external_targets_tested': False}


def doctor():
    import importlib.metadata
    result = {'python': sys.version.split()[0], 'python_packages': {},
              'browser': {}, 'mcp_configured': False, 'live_verified': False}
    for name in ('playwright', 'requests', 'httpx', 'curl_cffi', 'beautifulsoup4', 'pytest'):
        try:
            result['python_packages'][name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            result['python_packages'][name] = None
    from spider_core.browser import load_workspace_browser_configs, WorkspaceBrowserError
    try:
        pool = load_workspace_browser_configs(ROOT)
        result['browser'] = {'default_candidate': pool.default_candidate,
                            'executables': {name: item.executable.is_file() for name, item in pool.candidates.items()}}
    except WorkspaceBrowserError:
        result['browser'] = {'status': 'not_configured_or_invalid'}
    try:
        settings = local_settings()
        result['mcp_configured'] = Path(settings['js_reverser_entry']).is_file() and Path(settings['node_executable']).is_file()
    except (ValueError, OSError, KeyError):
        pass
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    configuration = sub.add_parser('configure')
    configuration.add_argument('--python', type=Path, default=Path(sys.executable))
    configuration.add_argument('--node', type=Path, required=True)
    configuration.add_argument('--entry', type=Path, default=ROOT / 'vendor/js-reverse-mcp/build/src/index.js')
    configuration.add_argument('--write-project-mcp', action='store_true')
    configuration.add_argument('--replace-managed', action='store_true')
    for name in ('cdp-smoke', 'mcp-smoke'):
        command = sub.add_parser(name)
        command.add_argument('--candidate', choices=('chrome', 'cloak'), required=True)
        if name == 'mcp-smoke':
            command.add_argument('--stdio-only', action='store_true')
    sub.add_parser('doctor')
    args = parser.parse_args()
    try:
        if args.action == 'configure':
            result = configure(args.python, args.node, args.entry,
                               write_project=args.write_project_mcp, replace_managed=args.replace_managed)
        elif args.action == 'cdp-smoke':
            result = cdp_smoke(args.candidate)
        elif args.action == 'mcp-smoke':
            if not args.stdio_only:
                from spider_core.browser import status_browser_candidate
                status_browser_candidate(ROOT, args.candidate)
            command, runtime, env = launch_spec(args.candidate)
            runtime.mkdir(parents=True, exist_ok=True)
            result = probe_stdio(command, runtime, env, live=not args.stdio_only)
        else:
            result = doctor()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as error:
        # Retain stable failure categories, not arbitrary URLs, credentials or tool payloads.
        print(json.dumps({'passed': False, 'error_type': type(error).__name__,
                          'error': str(error) if isinstance(error, (ValueError, RuntimeError)) else 'toolchain_check_failed'}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
