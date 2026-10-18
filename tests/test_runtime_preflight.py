"""Runtime mismatches must be detected before any dependency mutation."""
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts import install_browser_toolchain as installer


class RuntimePreflightTests(unittest.TestCase):
    def test_wrong_base_python_is_rejected_before_building_install_plan(self):
        with mock.patch.object(installer.sys, 'version_info', (3, 12, 8)), \
             mock.patch.object(installer.subprocess, 'run') as command:
            with self.assertRaisesRegex(ValueError, 'Python 3.11'):
                installer.plans('python', None)
            command.assert_not_called()

    def test_existing_wrong_version_venv_is_preserved_and_not_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executable = root / '.venv-toolchain' / ('Scripts/python.exe' if installer.os.name == 'nt' else 'bin/python')
            executable.parent.mkdir(parents=True)
            executable.write_bytes(b'old environment')
            with mock.patch.object(installer, 'ROOT', root), \
                 mock.patch.object(installer.subprocess, 'run', return_value=mock.Mock(stdout='3.12', returncode=0)):
                with self.assertRaisesRegex(ValueError, 'existing.*Python 3.11'):
                    installer.plans('python', None)
            self.assertEqual(executable.read_bytes(), b'old environment')

    def test_existing_python_311_venv_plan_uses_only_that_python(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executable = root / '.venv-toolchain' / ('Scripts/python.exe' if installer.os.name == 'nt' else 'bin/python')
            executable.parent.mkdir(parents=True)
            executable.write_bytes(b'correct environment')
            with mock.patch.object(installer, 'ROOT', root), \
                 mock.patch.object(installer.subprocess, 'run', return_value=mock.Mock(stdout='3.11', returncode=0)):
                plans = installer.plans('python', None)
            self.assertEqual(len(plans), 2)
            self.assertTrue(all(command[0] == str(executable) for _, command in plans))


if __name__ == '__main__':
    unittest.main()
