import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from urllib.error import URLError

from scripts import deploy, setup_chrome
from spider_core import project_runtime


class RecoveryTests(unittest.TestCase):
    def test_official_unix_node_layout_can_run_regression(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            node = root / 'runtime/bin/node'
            npm = root / 'runtime/lib/node_modules/npm/bin/npm-cli.js'
            node.parent.mkdir(parents=True)
            npm.parent.mkdir(parents=True)
            node.write_bytes(b'fixture')
            npm.write_text('fixture')
            with mock.patch.object(project_runtime.subprocess, 'run', return_value=mock.Mock(stdout='v24.22.0')):
                self.assertEqual(project_runtime.select_node(root, node), node.resolve())

    def test_project_node_wins_over_path_and_explicit_wins_over_project(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project, explicit = root / 'project/node', root / 'explicit/node'
            for node in (project, explicit):
                (node.parent / 'node_modules/npm/bin').mkdir(parents=True)
                node.write_bytes(b'fixture')
                (node.parent / 'node_modules/npm/bin/npm-cli.js').write_text('fixture')
            (root / 'config').mkdir()
            (root / 'config/agent_tools.local.json').write_text(json.dumps({'browser_toolchain': {'node_executable': str(project)}}))
            with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(project_runtime.subprocess, 'run', return_value=mock.Mock(stdout='v24.22.0')):
                self.assertEqual(project_runtime.select_node(root), project.resolve())
                self.assertEqual(project_runtime.select_node(root, explicit), explicit.resolve())
            project.unlink()
            with self.assertRaisesRegex(ValueError, 'missing'):
                project_runtime.select_node(root)

    def test_metadata_retries_then_uses_validated_fallback(self):
        opener = mock.Mock()
        opener.open.side_effect = URLError('private proxy details')
        with mock.patch.object(setup_chrome, 'build_opener', return_value=opener), mock.patch.object(setup_chrome.time, 'sleep'), \
             mock.patch.object(setup_chrome, 'curl_fetch', return_value=io.BytesIO(b'{}'), create=True) as fallback:
            with setup_chrome.fetch(setup_chrome.METADATA) as stream:
                self.assertEqual(stream.read(), b'{}')
        self.assertEqual(opener.open.call_count, 3)
        fallback.assert_called_once_with(setup_chrome.METADATA)

    def test_live_health_does_not_relabel_or_overwrite_history(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'outputs').mkdir()
            path = root / 'outputs/deployment_acceptance.json'
            path.write_text(json.dumps({'passed': True, 'status': 'completed', 'started_at': 'historical'}))
            before = path.read_bytes()
            with mock.patch('spider_core.browser.status_browser_candidate', side_effect=deploy.WorkspaceBrowserError('browser_unavailable')):
                report = deploy.deployment_status(root)
            self.assertTrue(report['last_acceptance']['passed'])
            self.assertFalse(report['live_health']['passed'])
            self.assertFalse(report['passed'])
            self.assertEqual(path.read_bytes(), before)

    def test_launcher_ensures_browser_instead_of_only_status(self):
        from scripts import start_js_reverser as launcher
        with mock.patch.object(launcher.sys, 'argv', ['launcher', '--candidate', 'chrome', '--describe']), \
             mock.patch.object(launcher, 'ensure_browser_candidate', create=True) as ensure, \
             mock.patch.object(launcher, 'launch_spec', return_value=(['node', 'entry'], Path('.'), {})), \
             mock.patch('sys.stdout', new_callable=io.StringIO):
            self.assertEqual(launcher.main(), 0)
            ensure.assert_called_once_with(launcher.ROOT, 'chrome')

    def test_stage_has_safe_code_and_elapsed_time(self):
        with tempfile.TemporaryDirectory() as directory:
            state = deploy.Deployment(Path(directory))
            state.stage('fixture', lambda: {'passed': True})
            self.assertGreaterEqual(state.report['stages']['fixture']['elapsed_seconds'], 0)
        self.assertEqual(deploy.diagnostic(URLError('secret'))['code'], 'network_connection_failed')

    def test_curl_rejects_redirect_response_and_private_url_before_use(self):
        with mock.patch.object(setup_chrome.shutil, 'which', return_value='curl'), \
             mock.patch.object(setup_chrome.subprocess, 'run', return_value=mock.Mock(returncode=0, stderr=b'STATUS:302')) as run:
            with self.assertRaises(setup_chrome.OfficialDownloadError):
                setup_chrome.curl_fetch(setup_chrome.METADATA)
            with self.assertRaises(ValueError):
                setup_chrome.curl_fetch('https://untrusted.invalid/file')
            self.assertEqual(run.call_count, 1)

    def test_bootstrap_runtime_configuration_can_transition_to_tool_environment(self):
        from scripts import browser_toolchain as toolchain
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base, python, node, entry = [root / value for value in ('base-python', 'tool-python', 'node', 'entry')]
            for path in (base, python, node, entry):
                path.write_bytes(b'fixture')
            (root / 'alias').mkdir()
            recorded_node = str(root / 'alias' / '..' / 'node')
            config = root / 'config/agent_tools.local.json'
            config.parent.mkdir()
            config.write_text(json.dumps({'unrelated': 'preserved', 'browser_toolchain': {'python_executable': str(base), 'node_executable': recorded_node},
                               'runtime_bootstrap': {'python': str(base), 'node': recorded_node, 'toolchain_pending': True}}))
            with mock.patch.object(toolchain, 'ROOT', root), mock.patch.object(toolchain.subprocess, 'run', return_value=mock.Mock(stdout='v24.22.0')):
                toolchain.configure(python, node, entry)
            result = json.loads(config.read_text('utf-8'))
            self.assertEqual(result['browser_toolchain']['python_executable'], str(python))
            self.assertEqual(result['unrelated'], 'preserved')
            self.assertFalse(result['runtime_bootstrap']['toolchain_pending'])


if __name__ == '__main__':
    unittest.main()
