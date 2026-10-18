from pathlib import Path
import tempfile
import unittest

from scripts.run_full_regression import requires_pytest


class RegressionDiscoveryTests(unittest.TestCase):
    def test_function_style_tests_are_not_silently_skipped(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'test_example.py'
            path.write_text('def test_example():\n    assert True\n', encoding='utf-8')
            self.assertTrue(requires_pytest(path))

    def test_unittest_and_inherited_testcase_need_no_external_runner(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'test_example.py'
            path.write_text('import unittest\nclass Base(unittest.TestCase):\n'
                            '    def test_example(self): pass\n'
                            'class Child(Base):\n    def test_other(self): pass\n', encoding='utf-8')
            self.assertFalse(requires_pytest(path))

    def test_plain_test_class_requires_pytest(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'test_example.py'
            path.write_text('class TestDemo:\n    def test_example(self): pass\n', encoding='utf-8')
            self.assertTrue(requires_pytest(path))


if __name__ == '__main__':
    unittest.main()
