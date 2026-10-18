import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

import bootstrap


SOURCE = Path(__file__).resolve().parents[1]


class BootstrapTests(unittest.TestCase):
    def test_default_demo_uses_runner_without_network_or_installer(self):
        with tempfile.TemporaryDirectory(prefix='customer demo ') as directory:
            root = Path(directory)
            for name in ('spider.py','AGENTS.md','CLAUDE.md','GEMINI.md','MANIFEST.sha256.json'):
                shutil.copyfile(SOURCE/name,root/name)
            for name in ('spider_core','scripts','skills','platforms','experiments/example_local'):
                shutil.copytree(SOURCE/name,root/name,ignore=shutil.ignore_patterns('__pycache__','selftest_tmp'))
            # Integrity is independently tested; use a fixture checker here so only selected files are needed.
            with mock.patch.object(bootstrap,'check_integrity',return_value=None), \
                 mock.patch.object(bootstrap,'install_tools',side_effect=AssertionError('installer must be explicit')):
                result=bootstrap.onboard(root)
            self.assertTrue(result['passed'])
            self.assertEqual(result['demo']['records'],3)
            self.assertTrue(result['demo']['validation_passed'])
            self.assertFalse(result['tools_installed_this_run'])
            self.assertFalse(result['agent_mcp_loading_verified'])
            self.assertFalse((root/'config/workspace_browser.json').exists())
            self.assertTrue((root/'outputs/onboarding.json').is_file())

    def test_missing_node_is_reported_before_any_dependency_install(self):
        with mock.patch.object(bootstrap.shutil,'which',return_value=None):
            with self.assertRaisesRegex(ValueError,'Node'):
                bootstrap.resolve_node(None)

    def test_selected_node_is_forwarded_to_existing_installer_and_generator(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            node=root/'node.exe'
            node.write_bytes(b'fixture')
            python=root/'.venv-toolchain'/('Scripts/python.exe' if bootstrap.os.name=='nt' else 'bin/python')
            python.parent.mkdir(parents=True)
            python.write_bytes(b'fixture')
            with mock.patch.object(bootstrap,'run_command',return_value={'passed':True}) as command:
                bootstrap.install_tools(root,node)
            args=[call.args[1] for call in command.call_args_list]
            self.assertIn('--apply',args[0])
            self.assertEqual(args[0][args[0].index('--node')+1],str(node))
            self.assertIn('configure',args[1])
            self.assertNotIn('--write-project-mcp',args[1])

    def test_bad_integrity_blocks_all_setup_and_installation(self):
        with mock.patch.object(bootstrap,'check_integrity',side_effect=ValueError('integrity failed')), \
             mock.patch.object(bootstrap,'install_tools') as install, \
             mock.patch.object(bootstrap,'run_command') as command:
            with self.assertRaises(ValueError):
                bootstrap.onboard(Path('.'),install=True)
            install.assert_not_called()
            command.assert_not_called()

    def test_explicit_install_failure_prevents_demo_success_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with mock.patch.object(bootstrap,'check_integrity'), \
                 mock.patch.object(bootstrap,'resolve_node',return_value=Path('node')), \
                 mock.patch.object(bootstrap,'install_tools',side_effect=RuntimeError('install failed')):
                with self.assertRaises(RuntimeError):
                    bootstrap.onboard(root,install=True)
            self.assertFalse((root/'outputs/onboarding.json').exists())

    def test_command_error_identifies_step_without_echoing_payload(self):
        failed=mock.Mock(returncode=1,stdout='private-session-value',stderr='private-session-value')
        with mock.patch.object(bootstrap.subprocess,'run',return_value=failed):
            with self.assertRaisesRegex(RuntimeError,'agent_platform_compat.py') as raised:
                bootstrap.run_command(Path('.'),['python','scripts/agent_platform_compat.py','setup'])
        self.assertNotIn('private-session-value',str(raised.exception))


if __name__=='__main__':
    unittest.main()
