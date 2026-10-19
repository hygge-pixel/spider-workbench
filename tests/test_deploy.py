import importlib
import io
import json
from pathlib import Path
import tempfile
import os
import subprocess
import sys
import unittest
from unittest import mock
import zipfile


class ChromeSetupTests(unittest.TestCase):
    def test_interrupted_download_is_not_promoted_to_completed_cache(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            asset = {'version': '1.2.3.4', 'platform': 'win64', 'url': 'https://storage.googleapis.com/chrome-for-testing-public/1.2.3.4/win64/chrome-win64.zip'}
            def broken(_, destination):
                destination.write_bytes(b'partial')
                raise RuntimeError('interrupted')
            with mock.patch.object(module, 'download', side_effect=broken), self.assertRaises(RuntimeError):
                module.install(root, asset)
            self.assertFalse(list((root / 'tmp/downloads').glob('*.zip')))
            self.assertFalse((root / 'tmp/browsers').exists())

    def module(self):
        return importlib.import_module('scripts.setup_chrome')

    def test_only_official_matching_stable_asset_is_accepted(self):
        module = self.module()
        data = {'channels': {'Stable': {'version': '1.2.3.4', 'downloads': {'chrome': [
            {'platform': 'win64', 'url': 'https://evil.invalid/chrome.zip'}]}}}}
        with self.assertRaises(ValueError):
            module.select_asset(data, 'win64')
        data['channels']['Stable']['downloads']['chrome'][0]['url'] = 'https://storage.googleapis.com/chrome-for-testing-public/1.2.3.4/win64/chrome-win64.zip'
        self.assertEqual(module.select_asset(data, 'win64')['version'], '1.2.3.4')
        with self.assertRaises(ValueError):
            module.select_asset(data, 'mac-arm64')

    def test_zip_traversal_and_link_are_rejected_before_extraction(self):
        module = self.module()
        for name, mode in [('../escape', 0), ('C:/escape', 0), ('chrome/link', 0o120777 << 16)]:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                archive = root / 'bad.zip'
                with zipfile.ZipFile(archive, 'w') as bundle:
                    entry = zipfile.ZipInfo(name)
                    entry.external_attr = mode
                    bundle.writestr(entry, 'fixture')
                with self.assertRaises(ValueError):
                    module.extract_checked(archive, root / 'extract')
                self.assertFalse((root / 'extract').exists())

    def test_download_cache_and_existing_program_are_verified_and_reused(self):
        module = self.module()
        with tempfile.TemporaryDirectory(prefix='中文 安装 ') as directory:
            root = Path(directory)
            asset = {'version': '1.2.3.4', 'platform': 'win64', 'url': 'https://storage.googleapis.com/chrome-for-testing-public/1.2.3.4/win64/chrome-win64.zip'}
            def download(_, destination):
                with zipfile.ZipFile(destination, 'w') as bundle:
                    bundle.writestr('chrome-win64/chrome.exe', 'synthetic executable')
            with mock.patch.object(module, 'download', side_effect=download) as transfer, \
                 mock.patch.object(module, 'program_version', return_value='1.2.3.4'):
                first = module.install(root, asset)
                second = module.install(root, asset)
                self.assertEqual(transfer.call_count, 1)
                self.assertEqual(first['archive_sha256'], second['archive_sha256'])
                self.assertEqual(second['action'], 'reused')
                Path(first['executable']).write_text('user modification')
                with self.assertRaises(ValueError):
                    module.install(root, asset)
            self.assertFalse((root / 'config/workspace_browser.json').exists())


class DeploymentStateTests(unittest.TestCase):
    def test_cli_json_is_utf8_even_with_legacy_parent_codepage(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'outputs').mkdir()
            (root / 'outputs/deployment_acceptance.json').write_text(json.dumps({'passed': False, 'label': '中文路径'}, ensure_ascii=False), encoding='utf-8')
            program = f"from scripts import deploy; from pathlib import Path; deploy.ROOT=Path({str(root)!a}); deploy.sys.argv=['deploy','status']; raise SystemExit(deploy.main())"
            result = subprocess.run([sys.executable, '-c', program], cwd=Path(__file__).resolve().parents[1],
                                    env=dict(os.environ, PYTHONIOENCODING='cp936'), capture_output=True)
            self.assertEqual(json.loads(result.stdout.decode('utf-8'))['last_acceptance']['label'], '中文路径')

    def test_child_error_category_is_preserved_without_tool_payload(self):
        module = self.module()
        failed = mock.Mock(returncode=1, stdout=json.dumps({'passed': False, 'error_type': 'RuntimeError',
                           'error': 'MCP read-only browser call failed; raw payload withheld'}), stderr='private page data')
        with mock.patch.object(module.subprocess, 'run', return_value=failed):
            with self.assertRaisesRegex(module.StageFailure, 'mcp_read_only_tool_failed'):
                module.command(Path('.'), ['fixture'])

    def test_host_acceptance_is_bound_to_current_source_and_configuration(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'MANIFEST.sha256.json').write_text(json.dumps({'files': {}}))
            generated = root / 'runs/_mcp/generated/mcp_config.json'
            generated.parent.mkdir(parents=True)
            generated.write_text('{}')
            state = module.Deployment(root)
            for name in module.TECHNICAL_STAGES:
                state.stage(name, lambda: {'passed': True})
            state.report.update(configuration_sha256=module.hashlib.sha256(generated.read_bytes()).hexdigest(),
                                source_sha256=module.source_fingerprint(root))
            state.finish()
            evidence = {'attempt_id': state.report['attempt_id'], 'configuration_sha256': state.report['configuration_sha256'],
                        'host': 'fixture', 'host_version': '1.0', 'session_id': 'observed-session', 'tool_name': 'list_pages',
                        'observed_at': module.datetime.now(module.timezone.utc).isoformat(), 'tool_call_passed': True,
                        'effective_config_passed': True, 'provenance': 'agent_observed_call'}
            path = root / 'host.json'
            path.write_text(json.dumps(evidence))
            with mock.patch('spider_core.browser.status_browser_candidate'):
                self.assertTrue(module.accept_host(root, path)['passed'])
            (root / 'config').mkdir()
            (root / 'config/workspace_browser.json').write_text('{}')
            with self.assertRaisesRegex(module.StageFailure, 'changed_since_checks'):
                module.accept_host(root, path)

    def test_missing_technical_stages_cannot_be_accepted_as_complete(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as directory:
            state = module.Deployment(Path(directory))
            state.finish()
            self.assertEqual(state.report['status'], 'incomplete')
            self.assertFalse(state.report['technical_passed'])

    def test_node_typescript_failure_stops_preflight_before_installation(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            npm = root / 'node_modules/npm/bin/npm-cli.js'
            npm.parent.mkdir(parents=True)
            npm.write_text('fixture')
            with mock.patch.object(module, 'verify_installation', return_value={'passed': True}), \
                 mock.patch('bootstrap.resolve_node', return_value=root / 'node.exe'), \
                 mock.patch.object(module.subprocess, 'run', side_effect=[mock.Mock(stdout='v24.14.1'), mock.Mock(returncode=-10, stdout='')]):
                with self.assertRaisesRegex(module.StageFailure, 'typescript_probe_failed'):
                    module.preflight(root)
            self.assertFalse((root / 'outputs').exists())

    def test_bare_host_success_or_old_attempt_is_not_accepted(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = module.Deployment(root)
            for name in module.TECHNICAL_STAGES:
                state.stage(name, lambda: {'passed': True})
            state.finish()
            evidence = root / 'host.json'
            evidence.write_text(json.dumps({'tool_call_passed': True}))
            with self.assertRaises(module.StageFailure):
                module.accept_host(root, evidence)
            self.assertFalse(json.loads((root / 'outputs/deployment_acceptance.json').read_text())['passed'])

    def module(self):
        return importlib.import_module('scripts.deploy')

    def test_failure_is_persisted_without_private_command_output(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = module.Deployment(root)
            def fail():
                raise RuntimeError('private payload')
            with self.assertRaises(RuntimeError):
                state.stage('dependencies', fail)
            saved = json.loads((root / 'outputs/deployment_acceptance.json').read_text())
            self.assertEqual(saved['stages']['dependencies']['status'], 'failed')
            self.assertFalse(saved['passed'])
            self.assertNotIn('private payload', json.dumps(saved))

    def test_technical_success_keeps_current_host_call_pending(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = module.Deployment(root)
            for name in module.TECHNICAL_STAGES:
                state.stage(name, lambda: {'passed': True})
            state.finish()
            saved = json.loads((root / 'outputs/deployment_acceptance.json').read_text())
            self.assertFalse(saved['passed'])
            self.assertIsNone(saved['host_tool_call_passed'])
            self.assertEqual(saved['status'], 'host_pending')
            self.assertIn('host', saved['next_action'])

    def test_restart_does_not_carry_old_success_into_new_attempt(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            previous = module.Deployment(root)
            previous.stage('mcp', lambda: {'passed': True})
            current = module.Deployment(root)
            current.stage('preflight', lambda: {'passed': True})
            saved = json.loads((root / 'outputs/deployment_acceptance.json').read_text())
            self.assertNotIn('mcp', saved['stages'])
            history = root / 'runs/_deployment/attempts' / (previous.report['attempt_id'] + '.json')
            self.assertTrue(history.is_file(), 'failed/interrupted attempts must remain reviewable after resume')

    def test_effective_host_definition_checks_all_launcher_arguments(self):
        module = self.module()
        fn = getattr(module, 'host_definition_matches', None)
        self.assertTrue(callable(fn), 'same service name or launcher alone is not enough')
        expected = {'command': 'node', 'args': ['launcher', '--python', 'project-python', '--candidate', 'chrome']}
        self.assertTrue(fn(expected, expected, Path('/project')))
        wrong = dict(expected, args=['launcher', '--python', 'other-python', '--candidate', 'chrome'])
        self.assertFalse(fn(wrong, expected, Path('/project')))


if __name__ == '__main__':
    unittest.main()
