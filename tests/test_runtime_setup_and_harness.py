import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile


class RuntimeSetupTests(unittest.TestCase):
    def test_node_hash_mismatch_never_extracts_or_configures(self):
        from scripts import setup_runtime as runtime
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with mock.patch.object(runtime, 'transfer', side_effect=lambda url, path: path.write_bytes(b'bad')), \
                 mock.patch.object(runtime, 'official_checksum', return_value='0' * 64):
                with self.assertRaisesRegex(ValueError, 'checksum'):
                    runtime.install_node(root, '24.22.0', 'x64')
            self.assertFalse((root / 'config/agent_tools.local.json').exists())
            self.assertFalse(list((root / 'tmp/runtimes').glob('**/node.exe')))

    def test_node_checked_zip_install_then_reuse_is_idempotent(self):
        from scripts import setup_runtime as runtime
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def download(url, path):
                with zipfile.ZipFile(path, 'w') as bundle:
                    for name in ('node.exe', 'node_modules/npm/bin/npm-cli.js'):
                        bundle.writestr(zipfile.ZipInfo('node-v24.22.0-win-x64/' + name, (2026, 1, 1, 0, 0, 0)), 'fixture')
            sample = root / 'sample.zip'
            download('', sample)
            digest = hashlib.sha256(sample.read_bytes()).hexdigest()
            with mock.patch.object(runtime, 'transfer', side_effect=download) as transfer, \
                 mock.patch.object(runtime, 'official_checksum', return_value=digest), \
                 mock.patch.object(runtime, 'probe_node', return_value='v24.22.0'):
                first = runtime.install_node(root, '24.22.0', 'x64')
                second = runtime.install_node(root, '24.22.0', 'x64')
                self.assertEqual(transfer.call_count, 1)
                self.assertEqual(second['action'], 'reused')
                Path(first['node']).write_text('modified')
                with self.assertRaisesRegex(ValueError, 'review'):
                    runtime.install_node(root, '24.22.0', 'x64')


class HarnessAdapterTests(unittest.TestCase):
    def test_preserve_profile_idempotent_conflict_and_remove_only_managed_block(self):
        from scripts import deepseek_harness as harness
        with tempfile.TemporaryDirectory(prefix='harness 中文 ') as directory:
            root = Path(directory)
            patch = root / 'profile/cordis.patch.yml'
            patch.parent.mkdir()
            original = '- id: unrelated\r\n  config:\r\n    preference: system\r\n'
            patch.write_bytes(original.encode('utf-8'))
            definition = {'command': 'node', 'args': ['launcher', '--python', 'py', '--candidate', 'chrome']}
            harness.configure(root, patch, definition)
            once = patch.read_bytes()
            harness.configure(root, patch, definition)
            self.assertEqual(patch.read_bytes(), once)
            self.assertTrue(once.decode('utf-8').startswith(original))
            with self.assertRaisesRegex(ValueError, 'conflict'):
                harness.configure(root, patch, dict(definition, command='other-node'))
            harness.remove(root, patch)
            self.assertEqual(patch.read_bytes(), original.encode('utf-8'))

    def test_existing_unmanaged_same_name_is_not_overwritten(self):
        from scripts import deepseek_harness as harness
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            patch = root / 'cordis.patch.yml'
            patch.write_text('- insert:\n    - id: old\n      config:\n        serverName: js-reverse\n')
            before = patch.read_bytes()
            with self.assertRaisesRegex(ValueError, 'conflict'):
                harness.configure(root, patch, {'command': 'node', 'args': []})
            self.assertEqual(patch.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
