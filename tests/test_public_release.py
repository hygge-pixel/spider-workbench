import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile
import shutil
import subprocess

from scripts.check_public_release import scan, refresh_manifest
from scripts.release import build_release


class PublicReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'source'
        self.root.mkdir()
        (self.root / 'README.md').write_text('public source\n', encoding='utf-8')
        self.output = Path(self.temp.name) / 'artifacts'

    def put(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
        return path

    def manifest(self, names):
        data = {'schema_version': 1, 'files': {name: hashlib.sha256((self.root/name).read_bytes()).hexdigest() for name in names}}
        self.put('MANIFEST.sha256.json', json.dumps(data))

    def test_clean_minimal_source_is_accepted(self):
        self.manifest(['README.md'])
        self.assertTrue(scan(self.root, require_structure=False)['passed'])

    def test_developer_sources_are_audited_in_repository(self):
        self.put('tests/test_contract.py', 'import unittest\n')
        self.put('requirements-dev.txt', 'pytest==8.4.2\n')
        refresh_manifest(self.root)
        data = json.loads((self.root/'MANIFEST.sha256.json').read_text())
        self.assertIn('tests/test_contract.py', data['files'])
        self.assertIn('requirements-dev.txt', data['files'])
        self.assertTrue(scan(self.root, require_structure=False)['passed'])

    def test_install_bundle_has_its_own_valid_manifest_and_no_developer_suites(self):
        self.put('tests/test_contract.py', 'import unittest\n')
        self.put('scripts/run_developer_tests.py', 'print("developer")\n')
        self.put('requirements-dev.txt', 'pytest==8.4.2\n')
        self.put('.github/workflows/ci.yml', 'name: fixture\n')
        self.put('skills/web-reverse-master/scripts/selftest.py', 'print("selftest")\n')
        self.put('scripts/helper.py', 'print("runtime")\n')
        refresh_manifest(self.root)
        original = (self.root/'MANIFEST.sha256.json').read_bytes()
        source = build_release(self.root, self.output, require_structure=False)
        install = build_release(self.root, self.output, require_structure=False, kind='install')
        with zipfile.ZipFile(source['archive']) as bundle:
            self.assertIn('spider-workbench/tests/test_contract.py', bundle.namelist())
        extracted = Path(self.temp.name)/'extracted'
        with zipfile.ZipFile(install['archive']) as bundle:
            bundle.extractall(extracted)
            self.assertNotIn('spider-workbench/tests/test_contract.py', bundle.namelist())
        installed = extracted/'spider-workbench'
        names = json.loads((installed/'MANIFEST.sha256.json').read_text())['files']
        self.assertIn('scripts/helper.py', names)
        self.assertNotIn('requirements-dev.txt', names)
        self.assertNotIn('scripts/run_developer_tests.py', names)
        self.assertNotIn('.github/workflows/ci.yml', names)
        self.assertNotIn('skills/web-reverse-master/scripts/selftest.py', names)
        self.assertTrue(scan(installed, require_structure=False)['passed'])
        again = build_release(self.root, Path(self.temp.name)/'again', require_structure=False, kind='install')
        self.assertEqual(Path(install['archive']).read_bytes(), Path(again['archive']).read_bytes())
        self.assertEqual((self.root/'MANIFEST.sha256.json').read_bytes(), original)

    def test_install_manifest_cannot_smuggle_developer_file(self):
        self.put('tests/test_contract.py', 'import unittest\n')
        self.manifest(['README.md', 'tests/test_contract.py'])
        manifest = json.loads((self.root/'MANIFEST.sha256.json').read_text())
        manifest['distribution_kind'] = 'install'
        self.put('MANIFEST.sha256.json', json.dumps(manifest))
        self.assertFalse(scan(self.root, require_structure=False)['passed'])

    def test_forbidden_runtime_config_and_credentials_are_rejected(self):
        for name in ('runs/history.json', 'config/workspace_browser.json',
                     'config/local_credentials/key.env', '.mcp.json', 'node_modules/a.js',
                     'experiments/old_site/collector.py', 'platforms/site/collector.py'):
            with self.subTest(name=name):
                self.put(name, 'sensitive local material')
                self.manifest(['README.md', name])
                result = scan(self.root, require_structure=False)
                self.assertFalse(result['passed'])
                self.assertIn('forbidden_path', {item['rule'] for item in result['issues']})

    def test_high_confidence_secret_is_reported_without_echoing_value(self):
        secret = 'gh' + 'p_' + 'A' * 36
        self.put('README.md', secret)
        self.manifest(['README.md'])
        result = scan(self.root, require_structure=False)
        self.assertFalse(result['passed'])
        self.assertNotIn(secret, json.dumps(result))
        self.assertIn('known_secret', {item['rule'] for item in result['issues']})

    def test_private_machine_path_is_rejected(self):
        self.put('README.md', 'C:' + '/Users/' + 'private-owner/project/file.py')
        self.manifest(['README.md'])
        self.assertFalse(scan(self.root, require_structure=False)['passed'])

    def test_manifest_tampering_prevents_release_creation(self):
        self.manifest(['README.md'])
        self.put('README.md', 'modified after manifest')
        with self.assertRaises(ValueError):
            build_release(self.root, self.output, require_structure=False)
        self.assertFalse(self.output.exists())

    def test_symlink_cannot_import_external_content(self):
        outside = Path(self.temp.name) / 'private.txt'
        outside.write_text('outside')
        link = self.root / 'README.md'
        link.unlink()
        try:
            link.symlink_to(outside)
        except OSError:
            self.skipTest('symlink privilege unavailable; junction behavior covered separately')
        self.manifest(['README.md'])
        self.assertFalse(scan(self.root, require_structure=False)['passed'])

    def test_unsafe_manifest_path_is_rejected(self):
        self.put('MANIFEST.sha256.json', json.dumps({'schema_version':1, 'files':{'../private.txt':'0'*64}}))
        self.assertFalse(scan(self.root, require_structure=False)['passed'])

    def test_git_tracked_local_file_is_checked_even_outside_manifest(self):
        self.manifest(['README.md'])
        self.put('.mcp.json', 'local config')
        with mock.patch('scripts.check_public_release.tracked_files', return_value=['README.md', '.mcp.json']):
            result = scan(self.root, require_structure=False)
        self.assertFalse(result['passed'])
        self.assertIn('unmanifested_tracked_file', {i['rule'] for i in result['issues']})
        self.assertIn('forbidden_path', {i['rule'] for i in result['issues']})

    def test_broken_local_markdown_link_is_reported(self):
        self.put('README.md', '[missing](docs/missing.md)')
        self.manifest(['README.md'])
        self.assertFalse(scan(self.root, require_structure=False)['passed'])

    def test_refresh_excludes_local_state_and_installed_dependencies(self):
        self.put('runs/private.json', 'must stay local')
        self.put('node_modules/a.js', 'installed code')
        self.put('config/workspace_browser.json', 'actual browser')
        self.put('scripts/new_helper.py', 'print("public")\n')
        result = refresh_manifest(self.root)
        self.assertEqual(set(result['files']), {'README.md', 'scripts/new_helper.py'})
        self.assertTrue(scan(self.root, require_structure=False)['passed'])

    def test_optional_backend_lockfiles_remain_in_source_release(self):
        self.put('requirements-backends/scrapling.lock', 'scrapling==0.4.2\n')
        self.put('requirements-backends/camoufox.lock', 'camoufox==0.4.11\n')
        result = refresh_manifest(self.root)
        self.assertIn('requirements-backends/scrapling.lock', result['files'])
        self.assertIn('requirements-backends/camoufox.lock', result['files'])

    @unittest.skipUnless(shutil.which('git'), 'Git required for checkout integrity acceptance')
    def test_git_index_preserves_crlf_bytes_under_user_autocrlf_setting(self):
        attributes = Path(__file__).resolve().parents[1] / '.gitattributes'
        shutil.copyfile(attributes, self.root/'.gitattributes')
        original = b'public CRLF fixture\r\nsecond line\r\n'
        (self.root/'README.md').write_bytes(original)
        subprocess.run(['git','init','-q'],cwd=self.root,check=True,capture_output=True)
        subprocess.run(['git','-c','core.autocrlf=true','add','.'],cwd=self.root,check=True,capture_output=True)
        stored = subprocess.check_output(['git','show',':README.md'],cwd=self.root)
        self.assertEqual(stored, original)

    def test_repeated_build_is_deterministic_and_contains_only_manifest_files(self):
        self.manifest(['README.md'])
        self.put('runs/private.json', 'never include')
        first = build_release(self.root, self.output, require_structure=False)
        data = Path(first['archive']).read_bytes()
        os.utime(self.root / 'README.md', (1790000000, 1790000000))
        second = build_release(self.root, Path(self.temp.name)/'second', require_structure=False)
        self.assertEqual(data, Path(second['archive']).read_bytes())
        with zipfile.ZipFile(first['archive']) as archive:
            self.assertEqual(archive.namelist(), ['spider-workbench/MANIFEST.sha256.json', 'spider-workbench/README.md'])


if __name__ == '__main__':
    unittest.main()
