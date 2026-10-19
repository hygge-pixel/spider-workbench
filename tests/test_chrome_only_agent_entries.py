import json
from pathlib import Path
import sys
import tempfile
import unittest

from scripts.agent_platform_compat import configure_browser, doctor
from scripts.browser_toolchain import build_definitions
from spider_core.browser import WorkspaceBrowserError, load_workspace_browser_configs


ROOT = Path(__file__).resolve().parents[1]
RETIRED_NAME = bytes.fromhex('636c6f616b').decode()


class ChromeOnlyAndAgentEntryTests(unittest.TestCase):
    def test_setup_generates_only_the_supported_browser_and_no_fingerprint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            program = root / 'browser.exe'
            program.touch()
            configure_browser(root, 'chrome', program)
            data = json.loads((root / 'config/workspace_browser.json').read_text(encoding='utf-8'))
            self.assertEqual(set(data['candidates']), {'chrome'})
            self.assertEqual(data['candidates']['chrome']['environment'], {})
            self.assertEqual(data['candidates']['chrome']['launch_args'], [])
            self.assertEqual(set(load_workspace_browser_configs(root).candidates), {'chrome'})

    def test_removed_candidate_is_rejected_without_writing_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            program = root / 'browser.exe'
            program.touch()
            with self.assertRaises(ValueError):
                configure_browser(root, RETIRED_NAME, program)
            self.assertFalse((root / 'config/workspace_browser.json').exists())
        with self.assertRaises(ValueError):
            build_definitions(ROOT, Path(sys.executable), (RETIRED_NAME,), node=Path(sys.executable))

    def test_stale_multi_browser_configuration_requires_explicit_review(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            program = root / 'browser.exe'
            program.touch()
            configure_browser(root, 'chrome', program)
            path = root / 'config/workspace_browser.json'
            payload = json.loads(path.read_text(encoding='utf-8'))
            payload['candidates'][RETIRED_NAME] = dict(payload['candidates']['chrome'])
            path.write_text(json.dumps(payload), encoding='utf-8')
            before = path.read_bytes()
            with self.assertRaises(WorkspaceBrowserError):
                load_workspace_browser_configs(root)
            self.assertEqual(path.read_bytes(), before)

    def test_default_agent_entries_exist_before_any_setup(self):
        entries = {
            'codex': 'AGENTS.md', 'claude-code': 'CLAUDE.md',
            'gemini-cli': 'GEMINI.md', 'cursor': 'AGENTS.md',
            'copilot': '.github/copilot-instructions.md', 'windsurf': 'AGENTS.md',
            'cline': '.clinerules/00-spider-workbench.md',
            'roo-code': '.roo/rules/00-spider-workbench.md',
            'kiro': 'AGENTS.md', 'opencode': 'AGENTS.md',
            'trae': '.trae/rules/project_rules.md',
        }
        for host, relative in entries.items():
            with self.subTest(host=host):
                path = ROOT / relative
                self.assertTrue(path.is_file(), relative)
                if relative != 'AGENTS.md':
                    self.assertIn('AGENTS.md', path.read_text(encoding='utf-8'))
        catalog = (ROOT / 'AGENTS.md').read_text(encoding='utf-8')
        for skill in (ROOT / 'skills').glob('*/SKILL.md'):
            self.assertIn(skill.relative_to(ROOT).as_posix(), catalog)

    def test_doctor_reports_file_readiness_separately_from_host_loading(self):
        result = doctor(ROOT)
        self.assertIn('agent_entries', result)
        self.assertEqual(len(result['agent_entries']), 11)
        for host, item in result['agent_entries'].items():
            self.assertTrue(item['entry_present'], host)
            self.assertFalse(item['host_loaded_verified'], host)

    def test_shipped_current_source_has_no_removed_browser_definition(self):
        manifest = json.loads((ROOT / 'MANIFEST.sha256.json').read_text(encoding='utf-8'))
        for name in manifest['files']:
            path = ROOT / name
            if path.is_file():
                self.assertFalse(RETIRED_NAME in path.read_text(encoding='utf-8').lower(), name)


if __name__ == '__main__':
    unittest.main()
