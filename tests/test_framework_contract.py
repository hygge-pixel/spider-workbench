import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def shipped_files():
    return json.loads((ROOT / 'MANIFEST.sha256.json').read_text(encoding='utf-8'))['files']


class FrameworkContractTests(unittest.TestCase):
    def test_no_previous_platform_collector_or_proof_is_packaged(self):
        names = shipped_files()
        self.assertFalse([p for p in names if p.startswith('platforms/') and p.endswith(('collector.py', 'proof.json'))])
        registry = json.loads((ROOT / 'platforms/registry.json').read_text(encoding='utf-8'))
        self.assertEqual(registry['schema_version'], 1)
        self.assertIsInstance(registry['platforms'], list)

    def test_only_example_local_collector_is_initially_packaged(self):
        collectors = sorted(p for p in shipped_files()
                            if p.startswith('experiments/') and p.endswith('/collector.py'))
        self.assertEqual(collectors, ['experiments/example_local/collector.py'])

    def test_eighteen_canonical_skills_and_complete_deployment_docs(self):
        original = {Path(name).parts[1] for name in shipped_files()
                    if name.startswith('skills/') and name.count('/') == 2 and name.endswith('/SKILL.md')}
        self.assertEqual(len(original), 18)
        for name in original:
            self.assertTrue((ROOT / 'skills' / name / 'SKILL.md').is_file(), name)
        for name in ('部署与调整说明', '交给目标Agent', '框架与Skills说明', '导出调整记录', '部署实施计划'):
            path = ROOT / f'docs/{name}.md'
            self.assertTrue(path.is_file(), name)
            self.assertGreater(len(path.read_text(encoding='utf-8')), 300)

    def test_no_bundled_credentials_or_active_browser_mcp_config(self):
        manifest = ROOT / 'MANIFEST.sha256.json'
        if manifest.is_file():
            names = json.loads(manifest.read_text(encoding='utf-8'))['files']
            self.assertNotIn('config/workspace_browser.json', names)
            self.assertNotIn('.mcp.json', names)
            for name in names:
                self.assertFalse(name.endswith('/cookies.json'), name)
                self.assertFalse(name.endswith('.env'), name)
                self.assertNotIn('node_modules', Path(name).parts)
                self.assertNotIn('__pycache__', Path(name).parts)
                self.assertNotIn('.git', Path(name).parts)
        else:
            self.fail('distribution manifest must exist in the release')


if __name__ == '__main__':
    unittest.main()
