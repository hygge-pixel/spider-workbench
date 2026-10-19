import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.agent_platform_compat import configure_browser, doctor, ensure_junction, setup, set_default_browser


ROOT = Path(__file__).resolve().parents[1]


class PortableSetupTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='framework space ')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        skill = self.root / 'skills/demo'
        skill.mkdir(parents=True)
        (skill / 'SKILL.md').write_text('---\nname: demo\n---\n', encoding='utf-8')
        for name in ('AGENTS.md', 'CLAUDE.md', 'GEMINI.md'):
            (self.root / name).write_text('rules', encoding='utf-8')
        (self.root / 'platforms').mkdir()
        (self.root / 'platforms/registry.json').write_text(
            '{"schema_version":1,"platforms":[]}', encoding='utf-8')

    def test_setup_rebuilds_links_and_is_idempotent(self):
        self.assertTrue(setup(self.root)['ok'])
        self.assertTrue(setup(self.root)['ok'])
        for relative in ('.agents/skills', '.claude/skills', '.gemini/skills'):
            self.assertEqual((self.root / relative).resolve(), (self.root / 'skills').resolve())
        self.assertFalse((self.root / 'config/workspace_browser.json').exists())
        self.assertTrue(doctor(self.root)['ok'])

    def test_setup_preserves_conflicting_real_directory(self):
        conflict = self.root / '.agents/skills'
        conflict.mkdir(parents=True)
        marker = conflict / 'keep.txt'
        marker.write_text('keep', encoding='utf-8')
        result = setup(self.root)
        self.assertFalse(result['ok'])
        self.assertEqual(marker.read_text(encoding='utf-8'), 'keep')

    def test_browser_config_requires_real_executable_and_preserves_existing(self):
        program = self.root / 'browser app.exe'
        program.write_bytes(b'test fixture only')
        missing = self.root / 'missing.exe'
        with self.assertRaises(ValueError):
            configure_browser(self.root, 'chrome', missing)
        result = configure_browser(self.root, 'chrome', program)
        self.assertTrue(result['ok'])
        path = self.root / 'config/workspace_browser.json'
        payload = json.loads(path.read_text(encoding='utf-8'))
        self.assertEqual(payload['default_candidate'], 'chrome')
        self.assertEqual(set(payload['candidates']), {'chrome'})
        profile = Path(payload['candidates']['chrome']['user_data_dir'])
        self.assertEqual(profile, self.root / 'tmp/chrome-mcp')
        self.assertEqual(payload['candidates']['chrome']['launch_args'], [])
        before = path.read_bytes()
        again = configure_browser(self.root, 'chrome', program)
        self.assertTrue(again['ok'])
        self.assertEqual(before, path.read_bytes())
        other = self.root / 'other.exe'
        other.write_bytes(b'other fixture')
        with self.assertRaises(FileExistsError):
            configure_browser(self.root, 'chrome', other)
        self.assertEqual(before, path.read_bytes())

    def test_browser_config_rejects_unknown_candidate_even_with_merge(self):
        program = self.root / 'browser.exe'
        program.touch()
        configure_browser(self.root, 'chrome', program)
        path = self.root / 'config/workspace_browser.json'
        before = path.read_bytes()
        for merge in (False, True):
            with self.assertRaises(ValueError):
                configure_browser(self.root, 'unsupported', program, merge=merge)
        self.assertEqual(path.read_bytes(), before)

    def test_doctor_is_read_only_and_optional_tools_do_not_block_core(self):
        setup(self.root)
        before = sorted(str(p.relative_to(self.root)) for p in self.root.rglob('*'))
        result = doctor(self.root)
        after = sorted(str(p.relative_to(self.root)) for p in self.root.rglob('*'))
        self.assertEqual(before, after)
        self.assertTrue(result['ok'])
        self.assertEqual(result['browser']['status'], 'not_configured')
        self.assertIn('optional_tools', result)

    def test_setting_default_preserves_the_configured_chrome(self):
        program = self.root / 'browser.exe'
        program.touch()
        configure_browser(self.root, 'chrome', program)
        path = self.root / 'config/workspace_browser.json'
        before = path.read_bytes()
        set_default_browser(self.root, 'chrome')
        self.assertEqual(json.loads(before), json.loads(path.read_bytes()))
        with self.assertRaises(ValueError):
            set_default_browser(self.root, 'unsupported')

    def test_link_conflict_does_not_follow_an_external_directory(self):
        outside = self.root / 'outside'
        outside.mkdir()
        link = self.root / 'link'
        self.assertTrue(ensure_junction(link, outside)['ok'])
        self.assertFalse(ensure_junction(link, self.root / 'skills')['ok'])
        self.assertEqual(link.resolve(), outside)


if __name__ == '__main__':
    unittest.main()
