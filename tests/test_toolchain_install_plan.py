from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest import mock

from scripts import install_browser_toolchain as installer


class InstallPlanTests(unittest.TestCase):
    def test_python_plan_is_separate_from_existing_task_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / '.venv').mkdir()
            with mock.patch.object(installer, 'ROOT', root):
                tasks = installer.plans('python', None)
            self.assertIn('.venv-toolchain', tasks[0][1][-1])
            self.assertFalse((root / '.venv-toolchain').exists())

    def test_incomplete_tool_environment_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / '.venv-toolchain').mkdir()
            (root / '.venv-toolchain/keep').write_text('keep')
            with mock.patch.object(installer, 'ROOT', root), self.assertRaises(ValueError):
                installer.plans('python', None)

    def test_ast_plan_uses_local_lock_not_global_install(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            node = root / 'runtime/node.exe'
            node.parent.mkdir()
            node.write_bytes(b'fixture')
            npm = node.parent / 'node_modules/npm/bin/npm-cli.js'
            npm.parent.mkdir(parents=True)
            npm.write_text('fixture')
            with (mock.patch.object(installer, 'ROOT', root),
                  mock.patch.object(installer.subprocess, 'run', return_value=SimpleNamespace(stdout='v24.16.0'))):
                tasks = installer.plans('ast', node)
            self.assertEqual(tasks[0][0], root)
            self.assertIn('ci', tasks[0][1])
            self.assertIn('--ignore-scripts', tasks[0][1])
            self.assertNotIn('--global', tasks[0][1])


if __name__ == '__main__':
    unittest.main()
