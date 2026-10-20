import json
import tempfile
import unittest
from pathlib import Path

from spider_core.promotion import promote_experiment, PromotionError
from spider_core.runner import run_collector
from spider_core.registry import load_registry


class CollectorPackageTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.folder=self.root/'experiments/demo';self.folder.mkdir(parents=True)
        (self.root/'platforms').mkdir()
        (self.root/'platforms/registry.json').write_text('{"schema_version":1,"platforms":[]}',encoding='utf-8')
        self.collector=self.folder/'collector.py'
        self.collector.write_text('''import argparse,json
from pathlib import Path
from helper import TITLE
p=argparse.ArgumentParser();p.add_argument('--task');p.add_argument('--output-dir');a=p.parse_args()
out=Path(a.output_dir);data=json.loads(Path(__file__).with_name('mapping.json').read_text('utf-8'))
(out/'normalized.jsonl').write_text(json.dumps({'id':data['id'],'title':TITLE})+'\\n',encoding='utf-8')
(out/'collector_result.json').write_text(json.dumps({'source_exhausted':True,'route':'local','backend':'python'}),encoding='utf-8')
''',encoding='utf-8')
        (self.folder/'helper.py').write_text("TITLE='helper value'",encoding='utf-8')
        (self.folder/'mapping.json').write_text('{"id":"1"}',encoding='utf-8')
        self.metadata={'platform_id':'audit','platform_name':'Audit','id':'items','name':'Items','route':'local',
                       'requires_auth':False,'unique_key':'id','required_fields':['id','title'],
                       'files':['helper.py','mapping.json']}
        self.save_metadata()
        self.task=self.folder/'task.example.json'
        self.task.write_text(json.dumps({'validation':{'unique_key':'id','required_fields':['id','title']},
                                        'completion':{'mode':'all','expected_total':1}}),encoding='utf-8')

    def save_metadata(self):
        (self.folder/'capability.json').write_text(json.dumps(self.metadata),encoding='utf-8')

    def test_registered_multifile_collector_runs_and_helper_changes_invalidate_proof(self):
        before=run_collector(self.root,self.collector,self.task)
        promoted=promote_experiment(self.root,self.folder,before.run_dir)
        self.assertTrue((promoted.target_dir/'helper.py').is_file())
        self.assertTrue((promoted.target_dir/'mapping.json').is_file())
        after=run_collector(self.root,promoted.target_dir/'collector.py',self.task,selector='audit/items')
        self.assertEqual(after.status,'completed')
        self.assertEqual(load_registry(self.root).capabilities[0].proof_status,'verified')
        (promoted.target_dir/'helper.py').write_text("TITLE='changed'",encoding='utf-8')
        self.assertEqual(load_registry(self.root).capabilities[0].proof_status,'stale')

    def test_helper_changed_since_run_is_rejected(self):
        run=run_collector(self.root,self.collector,self.task)
        (self.folder/'helper.py').write_text("TITLE='changed'",encoding='utf-8')
        with self.assertRaises(PromotionError):
            promote_experiment(self.root,self.folder,run.run_dir)

    def test_undeclared_local_helper_does_not_create_broken_verified_capability(self):
        del self.metadata['files'];self.save_metadata()
        run=run_collector(self.root,self.collector,self.task)
        with self.assertRaises(PromotionError):
            promote_experiment(self.root,self.folder,run.run_dir)
        self.assertEqual(load_registry(self.root).capabilities,())

    def test_session_and_traversal_files_are_rejected(self):
        run=run_collector(self.root,self.collector,self.task)
        (self.folder/'cookies.json').write_text('{"sid":"synthetic"}',encoding='utf-8')
        for name in ('cookies.json','../outside.py','config.env','runs/item.json'):
            with self.subTest(name=name):
                self.metadata['files']=[name];self.save_metadata()
                with self.assertRaises(PromotionError):
                    promote_experiment(self.root,self.folder,run.run_dir)

    def test_case_variants_of_session_cache_cannot_be_registered(self):
        run=run_collector(self.root,self.collector,self.task)
        (self.folder/'Cookies.json').write_text('{"sid":"synthetic-session"}',encoding='utf-8')
        self.metadata['files'].append('Cookies.json');self.save_metadata()
        from spider_core.collector_package import package_hashes
        with self.assertRaises(ValueError):
            package_hashes(self.collector)

    def test_invalid_metadata_type_is_reported_as_a_contract_error(self):
        from spider_core.runner import RunError
        (self.folder/'capability.json').write_text('[]',encoding='utf-8')
        with self.assertRaises(RunError):
            run_collector(self.root,self.collector,self.task)

    def test_json_secret_checks_are_case_insensitive(self):
        from spider_core.collector_package import package_hashes
        (self.folder/'settings.JSON').write_text('{"api_key":"synthetic-key"}',encoding='utf-8')
        self.metadata['files'].append('settings.JSON');self.save_metadata()
        with self.assertRaises(ValueError):
            package_hashes(self.collector)

    def test_from_package_import_requires_files_and_a_fresh_run(self):
        package = self.folder / 'helpers'
        package.mkdir()
        (package / '__init__.py').write_text('', encoding='utf-8')
        (package / 'value.py').write_text("TITLE='package value'", encoding='utf-8')
        (package / 'unused.py').write_text("raise RuntimeError('not needed')", encoding='utf-8')
        self.collector.write_text(self.collector.read_text('utf-8').replace(
            'from helper import TITLE', 'from helpers import value\nTITLE=value.TITLE'), encoding='utf-8')
        del self.metadata['files']; self.save_metadata()
        old_run = run_collector(self.root, self.collector, self.task)
        with self.assertRaisesRegex(PromotionError, r'capability\.files.*run'):
            promote_experiment(self.root, self.folder, old_run.run_dir)
        self.assertEqual(load_registry(self.root).capabilities, ())
        self.metadata['files'] = ['helpers/__init__.py', 'helpers/value.py', 'mapping.json']
        self.save_metadata()
        with self.assertRaises(PromotionError):
            promote_experiment(self.root, self.folder, old_run.run_dir)
        fresh = run_collector(self.root, self.collector, self.task)
        promoted = promote_experiment(self.root, self.folder, fresh.run_dir)
        self.assertFalse((promoted.target_dir / 'helpers/unused.py').exists())
        self.assertEqual(run_collector(self.root, promoted.target_dir / 'collector.py',
                                      self.task, selector='audit/items').status, 'completed')

    def test_static_package_imports_reject_each_omitted_source(self):
        from spider_core.collector_package import package_hashes
        sources = {
            'pkg/__init__.py': '', 'pkg/value.py': 'TITLE=1',
            'pkg/worker.py': '', 'pkg/sub/__init__.py': '', 'pkg/sub/worker.py': '',
        }
        for name, content in sources.items():
            path = self.folder / name; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8')
        cases = [
            ('collector.py', 'from pkg import value', 'pkg/value.py'),
            ('collector.py', 'import pkg.value', 'pkg/__init__.py'),
            ('collector.py', 'from pkg.sub import worker', 'pkg/__init__.py'),
            ('pkg/worker.py', 'from . import value', 'pkg/value.py'),
            ('pkg/worker.py', 'from .value import TITLE', 'pkg/value.py'),
            ('pkg/sub/worker.py', 'from .. import value', 'pkg/value.py'),
            ('pkg/sub/worker.py', 'from ..value import TITLE', 'pkg/value.py'),
            ('pkg/sub/worker.py', 'from pkg import value', 'pkg/value.py'),
            ('pkg/__init__.py', 'from . import value', 'pkg/value.py'),
        ]
        self.collector.write_text('# static fixture\n', encoding='utf-8')
        for importer, statement, omitted in cases:
            with self.subTest(importer=importer, statement=statement, omitted=omitted):
                for name, content in sources.items():
                    (self.folder / name).write_text(content, encoding='utf-8')
                self.collector.write_text('# static fixture\n', encoding='utf-8')
                (self.folder / importer).write_text(statement + '\n', encoding='utf-8')
                metadata = {'files': [name for name in sources if name != omitted]}
                with self.assertRaisesRegex(ValueError, r'capability\.files.*run'):
                    package_hashes(self.collector, metadata=metadata, require_declared_imports=True)

    def test_complete_relative_and_namespace_packages_remain_portable(self):
        package = self.folder / 'helpers'
        (package / 'sub').mkdir(parents=True)
        files = {
            'helpers/__init__.py': 'from . import value\n',
            'helpers/value.py': "TITLE='relative value'\n",
            'helpers/sub/__init__.py': '',
            'helpers/sub/worker.py': 'from ..value import TITLE\n',
            # A namespace package has no initializer to declare.
            'namespace/value.py': 'from helpers.sub.worker import TITLE\n',
        }
        for name, content in files.items():
            path = self.folder / name; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8')
        self.collector.write_text(self.collector.read_text('utf-8').replace(
            'from helper import TITLE', 'from namespace import value\nTITLE=value.TITLE'), encoding='utf-8')
        self.metadata['files'] = [*files, 'mapping.json']; self.save_metadata()
        run = run_collector(self.root, self.collector, self.task)
        promoted = promote_experiment(self.root, self.folder, run.run_dir)
        self.assertEqual(run_collector(self.root, promoted.target_dir / 'collector.py',
                                      self.task, selector='audit/items').status, 'completed')
        self.assertEqual(load_registry(self.root).capabilities[0].proof_status, 'verified')

    def test_module_attribute_is_not_mistaken_for_package_submodule(self):
        from spider_core.collector_package import package_hashes
        self.collector.write_text('from helper import TITLE\nimport json\n', encoding='utf-8')
        (self.folder / 'helper').mkdir()
        (self.folder / 'helper/TITLE.py').write_text('# unrelated namespace\n', encoding='utf-8')
        self.assertEqual(set(package_hashes(self.collector, metadata={'files': ['helper.py']},
                                           require_declared_imports=True)), {'collector.py', 'helper.py'})

    def test_legacy_single_file_registration_and_proof_remain_supported(self):
        self.collector.write_text(self.collector.read_text('utf-8').replace(
            'from helper import TITLE', "TITLE='single file'"), encoding='utf-8')
        # Keep the data inline too: no undeclared runtime file is needed.
        self.collector.write_text(self.collector.read_text('utf-8').replace(
            "json.loads(Path(__file__).with_name('mapping.json').read_text('utf-8'))",
            "{'id':'1'}"), encoding='utf-8')
        del self.metadata['files']; self.save_metadata()
        run = run_collector(self.root, self.collector, self.task)
        promoted = promote_experiment(self.root, self.folder, run.run_dir)
        proof = json.loads((promoted.target_dir / 'proof.json').read_text('utf-8'))
        self.assertNotIn('collector_files', proof)
        self.assertEqual(load_registry(self.root).capabilities[0].proof_status, 'verified')
        self.assertEqual(run_collector(self.root, promoted.target_dir / 'collector.py',
                                      self.task, selector='audit/items').status, 'completed')
