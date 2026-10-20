"""Installation contracts: preserve existing work, resume only verified stages."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
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


class SourcePatchDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        source = Path(__file__).resolve().parents[1]
        manifest = json.loads((source / 'MANIFEST.sha256.json').read_text('utf-8'))
        for name in (*manifest['files'], 'MANIFEST.sha256.json'):
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / name, target)
        # This isolated fixture includes the newly written tests before the
        # maintainer refreshes the real source manifest. Establish its own baseline.
        for name in manifest['files']:
            manifest['files'][name] = hashlib.sha256((self.root / name).read_bytes()).hexdigest()
        (self.root / 'MANIFEST.sha256.json').write_bytes(
            (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
        self.original_manifest = (self.root / 'MANIFEST.sha256.json').read_bytes()

    def approve(self, name, content):
        from hashlib import sha256
        path = self.root / name
        path.write_text(content, encoding='utf-8')
        manifest = json.loads(self.original_manifest)['files']
        record = {'schema_version': 1, 'manifest_sha256': sha256(self.original_manifest).hexdigest(),
                  'files': {name: {'before': manifest[name], 'after': sha256(path.read_bytes()).hexdigest(),
                                   'reviewed': True, 'reason': 'synthetic reviewed maintenance'}}}
        destination = self.root / 'config/source_patches.local.json'
        destination.write_text(json.dumps(record), encoding='utf-8')
        return destination

    def test_reviewed_patch_passes_delivery_but_still_fails_original_release(self):
        from scripts.run_full_regression import verify_source
        from scripts.check_public_release import scan
        from scripts.release import build_release
        self.approve('README.md', (self.root / 'README.md').read_text('utf-8') + '\nLocal reviewed note.\n')
        self.assertTrue(verify_distribution.verify_installation(self.root)['passed'])
        self.assertFalse(scan(self.root)['passed'])
        result = verify_source(self.root)
        self.assertTrue(result['passed'])
        self.assertFalse(result['original_distribution_passed'])
        self.assertEqual(result['reviewed_local_changes'], ['README.md'])
        with self.assertRaises(ValueError):
            build_release(self.root, self.root / 'outputs/forbidden-release')
        self.assertEqual((self.root / 'MANIFEST.sha256.json').read_bytes(), self.original_manifest)

    def test_real_delivery_cli_accepts_reviewed_patch_without_refreshing_manifest(self):
        self.approve('README.md', (self.root / 'README.md').read_text('utf-8') + '\nLocal reviewed note.\n')
        result = subprocess.run([sys.executable, str(self.root / 'scripts/run_full_regression.py'),
                                 '--delivery-only'], cwd=self.root, capture_output=True, text=True,
                                encoding='utf-8', timeout=60,
                                env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1', SPIDER_PYTHON=sys.executable))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['source']['reviewed_local_changes'], ['README.md'])
        self.assertFalse(report['source']['original_distribution_passed'])
        self.assertEqual(report['offline_records'], 3)
        self.assertEqual((self.root / 'MANIFEST.sha256.json').read_bytes(), self.original_manifest)

    def test_delivery_rejects_missing_unreviewed_and_stale_approval(self):
        from scripts.run_full_regression import verify_source
        path = self.root / 'README.md'
        original = path.read_text('utf-8')
        for change in ('unreviewed', 'stale_manifest', 'followup', 'missing'):
            with self.subTest(change=change):
                record_path = self.approve('README.md', original + '\nLocal note.\n')
                record = json.loads(record_path.read_text('utf-8'))
                if change == 'unreviewed': record['files']['README.md']['reviewed'] = False
                elif change == 'stale_manifest': record['manifest_sha256'] = '0' * 64
                elif change == 'followup': path.write_text(original + '\nDifferent followup.\n', encoding='utf-8')
                else: path.unlink()
                record_path.write_text(json.dumps(record), encoding='utf-8')
                with self.assertRaises(ValueError): verify_source(self.root)

    def test_approval_does_not_bypass_content_structure_or_syntax_checks(self):
        from scripts.run_full_regression import verify_source
        original = (self.root / 'README.md').read_text('utf-8')
        for suffix in ('\ngh' + 'p_' + 'A' * 36, '\n[bad](missing-local-fixture.md)\n',
                       '\nC:' + '/Users/' + 'private-owner/fixture.py\n'):
            with self.subTest(suffix=suffix[:12]):
                self.approve('README.md', original + suffix)
                self.assertTrue(verify_distribution.verify_installation(self.root)['passed'])
                with self.assertRaises(ValueError): verify_source(self.root)
        source = Path(__file__).resolve().parents[1]
        shutil.copy2(source / 'README.md', self.root / 'README.md')
        self.approve('platforms/registry.json', '{"schema_version":1,"platforms":[{}]}')
        self.assertTrue(verify_distribution.verify_installation(self.root)['passed'])
        with self.assertRaises(ValueError): verify_source(self.root)
        # Restore exact original bytes before switching the approved file.
        shutil.copy2(source / 'platforms/registry.json', self.root / 'platforms/registry.json')
        self.approve('spider_core/routing.py', 'def broken(:\n')
        self.assertTrue(verify_distribution.verify_installation(self.root)['passed'])
        with self.assertRaises(SyntaxError): verify_source(self.root)


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
    @mock.patch.dict(os.environ, {'SPIDER_PYTHON': ''})
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
