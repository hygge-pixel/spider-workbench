"""Installation contracts: preserve existing work, resume only verified stages."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts import verify_distribution, install_browser_toolchain as installer


class SourcePatchTests(unittest.TestCase):
    def test_only_exact_reviewed_changes_are_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'example.py'
            source.write_text('before', encoding='utf-8')
            before = hashlib.sha256(source.read_bytes()).hexdigest()
            manifest = root / 'MANIFEST.sha256.json'
            manifest.write_text(json.dumps({'schema_version': 1, 'files': {'example.py': before}}))
            source.write_text('after', encoding='utf-8')
            fn = getattr(verify_distribution, 'verify_installation', None)
            self.assertTrue(callable(fn), 'installation must recognize explicitly reviewed local patches')
            self.assertFalse(fn(root)['passed'])
            (root / 'config').mkdir()
            record = {'schema_version': 1, 'manifest_sha256': hashlib.sha256(manifest.read_bytes()).hexdigest(),
                      'files': {'example.py': {'before': before, 'after': hashlib.sha256(source.read_bytes()).hexdigest(),
                                              'reason': 'reviewed fix', 'reviewed': True}}}
            (root / 'config/source_patches.local.json').write_text(json.dumps(record))
            self.assertTrue(fn(root)['passed'])
            self.assertFalse(verify_distribution.verify(root)['passed'], 'original provenance must remain unchanged')
            source.write_text('unreviewed followup', encoding='utf-8')
            self.assertFalse(fn(root)['passed'])


class ResumeTests(unittest.TestCase):
    def test_component_checkpoint_requires_matching_inputs_and_live_probe(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fn = getattr(installer, 'install_component', None)
            self.assertTrue(callable(fn), 'component installation must resume verified work')
            fingerprint = mock.Mock(return_value='first')
            with mock.patch.object(installer, 'ROOT', root), \
                 mock.patch.object(installer, 'component_fingerprint', fingerprint, create=True), \
                 mock.patch.object(installer, 'component_ready', return_value=True, create=True), \
                 mock.patch.object(installer, 'plans', return_value=[(root, ['fixture'])]), \
                 mock.patch.object(installer.subprocess, 'run') as run:
                self.assertEqual(fn('ast', Path('node'))['action'], 'installed')
                self.assertEqual(fn('ast', Path('node'))['action'], 'reused')
                self.assertEqual(run.call_count, 1)
                fingerprint.return_value = 'changed-lock'
                self.assertEqual(fn('ast', Path('node'))['action'], 'installed')
                self.assertEqual(run.call_count, 2)
                with mock.patch.object(installer, 'component_ready', side_effect=[False, True]):
                    self.assertEqual(fn('ast', Path('node'))['action'], 'installed')
                self.assertEqual(run.call_count, 3)

    def test_failed_component_never_leaves_success_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fn = getattr(installer, 'install_component', None)
            self.assertTrue(callable(fn), 'failed stages need recoverable state')
            with mock.patch.object(installer, 'ROOT', root), \
                 mock.patch.object(installer, 'component_fingerprint', return_value='one', create=True), \
                 mock.patch.object(installer, 'plans', return_value=[(root, ['fixture'])]), \
                 mock.patch.object(installer.subprocess, 'run', side_effect=RuntimeError('private payload')):
                with self.assertRaises(RuntimeError):
                    fn('ast', Path('node'))
            self.assertFalse((root / 'runs/_deployment/components/ast.json').exists())


class RuntimeChoiceTests(unittest.TestCase):
    def test_project_config_and_explicit_runtime_have_consistent_priority(self):
        from spider_core.project_runtime import select_python
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            configured = root / 'configured.exe'
            explicit = root / 'explicit.exe'
            for path in (configured, explicit):
                path.write_bytes(b'fixture')
            (root / 'config').mkdir()
            (root / 'config/agent_tools.local.json').write_text(json.dumps({'browser_toolchain': {'python_executable': str(configured)}}))
            with mock.patch('spider_core.project_runtime.subprocess.run', return_value=mock.Mock(stdout='3.11')), \
                 mock.patch.dict(os.environ, {}, clear=True):
                self.assertEqual(select_python(root), configured.resolve())
                self.assertEqual(select_python(root, explicit), explicit.resolve())
            configured.unlink()
            with self.assertRaisesRegex(ValueError, 'missing'):
                select_python(root)

    def test_modified_lock_invalidates_component_fingerprint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lock = root / 'package-lock.json'
            lock.write_text('first')
            with mock.patch.object(installer, 'ROOT', root), \
                 mock.patch.object(installer.subprocess, 'run', return_value=mock.Mock(stdout='v24.16.0')):
                first = installer.component_fingerprint('ast', root / 'node')
                lock.write_text('changed')
                self.assertNotEqual(first, installer.component_fingerprint('ast', root / 'node'))

    def test_regression_wrapper_considers_tool_environment_before_task_venv(self):
        wrapper = (Path(__file__).resolve().parents[1] / 'scripts/run_full_regression.ps1').read_text()
        self.assertIn('.venv-toolchain/Scripts/python.exe', wrapper)
        self.assertLess(wrapper.index('.venv-toolchain/Scripts/python.exe'), wrapper.index('.venv/Scripts/python.exe'))


if __name__ == '__main__':
    unittest.main()
