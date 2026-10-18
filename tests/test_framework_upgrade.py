import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.upgrade_framework import make_plan, apply_plan, rollback


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class UpgradeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        base = Path(self.temporary.name)
        self.release, self.target = base / 'release', base / 'target'
        self.release.mkdir(); self.target.mkdir()
        for root, text in ((self.release, 'new'), (self.target, 'old')):
            (root / 'README.md').write_text(text, encoding='utf-8')
            (root / 'platforms').mkdir()
            (root / 'platforms/registry.json').write_text('{"keep":"local"}', encoding='utf-8')
        (self.release / 'scripts').mkdir()
        (self.release / 'scripts/new.py').write_text('new helper', encoding='utf-8')
        self.old = {'schema_version': 1, 'files': {'README.md': digest(self.target / 'README.md')}}
        (self.release / 'upgrade').mkdir()
        (self.release / 'upgrade/v1_manifest.sha256.json').write_text(json.dumps(self.old), encoding='utf-8')
        files = {p.relative_to(self.release).as_posix(): digest(p) for p in self.release.rglob('*') if p.is_file()}
        (self.release / 'MANIFEST.sha256.json').write_text(json.dumps({'schema_version': 1, 'files': files}), encoding='utf-8')

    def test_dry_run_then_upgrade_preserves_new_tasks_registry_and_config(self):
        for relative in ('experiments/my_task/collector.py', 'config/workspace_browser.json', 'runs/local/cookies.json'):
            path = self.target / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('keep exactly', encoding='utf-8')
        plan = make_plan(self.release, self.target)
        self.assertEqual((self.target / 'README.md').read_text(), 'old')
        result = apply_plan(self.release, self.target, plan)
        self.assertTrue(result['passed'])
        self.assertEqual((self.target / 'README.md').read_text(), 'new')
        self.assertEqual((self.target / 'platforms/registry.json').read_text(), '{"keep":"local"}')
        for relative in ('experiments/my_task/collector.py', 'config/workspace_browser.json', 'runs/local/cookies.json'):
            self.assertEqual((self.target / relative).read_text(), 'keep exactly')
        repeated = make_plan(self.release, self.target)
        self.assertFalse(repeated['changes'])
        rollback(self.target, Path(result['backup']))
        self.assertEqual((self.target / 'README.md').read_text(), 'old')
        self.assertFalse((self.target / 'scripts/new.py').exists())

    def test_conflict_blocks_all_writes_until_explicit_local_merge(self):
        (self.target / 'README.md').write_text('local customization', encoding='utf-8')
        plan = make_plan(self.release, self.target)
        self.assertEqual(plan['conflicts'], ['README.md'])
        with self.assertRaises(ValueError):
            apply_plan(self.release, self.target, plan)
        self.assertFalse((self.target / 'scripts/new.py').exists())
        resolved = make_plan(self.release, self.target, accept_local=['README.md'])
        self.assertFalse(resolved['conflicts'])
        apply_plan(self.release, self.target, resolved)
        self.assertEqual((self.target / 'README.md').read_text(), 'local customization')

    def test_rollback_preserves_work_added_after_upgrade(self):
        result = apply_plan(self.release, self.target, make_plan(self.release, self.target))
        (self.target / 'README.md').write_text('new work after upgrade', encoding='utf-8')
        with self.assertRaises(ValueError):
            rollback(self.target, Path(result['backup']))
        self.assertEqual((self.target / 'README.md').read_text(), 'new work after upgrade')

    def test_tampered_release_is_rejected_before_writing(self):
        (self.release / 'scripts/new.py').write_text('tampered', encoding='utf-8')
        with self.assertRaises(ValueError):
            make_plan(self.release, self.target)

    def test_missing_unchanged_framework_file_is_restored(self):
        path = self.release / 'core.py'
        path.write_text('unchanged source', encoding='utf-8')
        self.old['files']['core.py'] = digest(path)
        (self.release / 'upgrade/v1_manifest.sha256.json').write_text(json.dumps(self.old), encoding='utf-8')
        files = {p.relative_to(self.release).as_posix(): digest(p) for p in self.release.rglob('*')
                 if p.is_file() and p.name != 'MANIFEST.sha256.json'}
        (self.release / 'MANIFEST.sha256.json').write_text(json.dumps({'schema_version': 1, 'files': files}), encoding='utf-8')
        result = apply_plan(self.release, self.target, make_plan(self.release, self.target))
        self.assertTrue(result['passed'])
        self.assertEqual((self.target / 'core.py').read_text(), 'unchanged source')

    def test_path_traversal_is_rejected(self):
        data = {'schema_version': 1, 'files': {'../escape': 'a' * 64}}
        (self.release / 'MANIFEST.sha256.json').write_text(json.dumps(data), encoding='utf-8')
        with self.assertRaises(ValueError):
            make_plan(self.release, self.target)

    def test_existing_directory_is_reported_as_conflict_before_any_write(self):
        (self.target / 'scripts/new.py').mkdir(parents=True)
        marker = self.target / 'scripts/new.py/local_work.txt'
        marker.write_text('keep directory contents', encoding='utf-8')
        plan = make_plan(self.release, self.target)
        self.assertIn('scripts/new.py', plan['conflicts'])
        with self.assertRaises(ValueError):
            apply_plan(self.release, self.target, plan)
        self.assertEqual((self.target / 'README.md').read_text(), 'old')
        self.assertEqual(marker.read_text(), 'keep directory contents')
        self.assertFalse((self.target / 'outputs').exists())

    def test_file_in_destination_ancestors_is_reported_before_any_write(self):
        (self.target / 'scripts').write_text('local file uses directory name', encoding='utf-8')
        plan = make_plan(self.release, self.target)
        self.assertIn('scripts/new.py', plan['conflicts'])
        with self.assertRaises(ValueError):
            apply_plan(self.release, self.target, plan)
        self.assertEqual((self.target / 'README.md').read_text(), 'old')
        self.assertFalse((self.target / 'outputs').exists())


if __name__ == '__main__':
    unittest.main()
