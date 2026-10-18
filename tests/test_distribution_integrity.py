import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.verify_distribution import verify


class DistributionIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.file = self.root / 'README.md'
        self.file.write_text('original', encoding='utf-8')
        self.manifest = {'schema_version': 1, 'files': {
            'README.md': hashlib.sha256(self.file.read_bytes()).hexdigest()}}

    def save(self):
        (self.root / 'MANIFEST.sha256.json').write_text(json.dumps(self.manifest), encoding='utf-8')

    def test_accepts_matching_and_ignores_new_local_files(self):
        self.save()
        (self.root / 'local.txt').write_text('new', encoding='utf-8')
        result = verify(self.root)
        self.assertTrue(result['passed'])
        self.assertEqual(result['checked_files'], 1)

    def test_reports_changed_and_missing_original(self):
        self.save()
        self.file.write_text('changed', encoding='utf-8')
        self.assertEqual(verify(self.root)['changed'], ['README.md'])
        self.file.unlink()
        self.assertEqual(verify(self.root)['missing'], ['README.md'])

    def test_rejects_traversal_and_non_digest_manifest(self):
        for key in ('../outside', '/outside', 'C:/outside', 'sub\\outside'):
            self.manifest['files'] = {key: '0' * 64}
            self.save()
            result = verify(self.root)
            self.assertFalse(result['passed'])
            self.assertIn('error', result)
        self.manifest['files'] = {'README.md': 'not-a-digest'}
        self.save()
        self.assertFalse(verify(self.root)['passed'])


if __name__ == '__main__':
    unittest.main()
