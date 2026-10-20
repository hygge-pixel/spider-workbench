import json
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from spider_core.runner import run_collector, RunError

HEADER = '''import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--task');p.add_argument('--output-dir');a=p.parse_args();out=Path(a.output_dir)
'''
RESULT = "(out/'collector_result.json').write_text(json.dumps({'source_exhausted':True,'route':'local','backend':'python'}),encoding='utf-8')\n"


class AuditRegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.entry=self.root/'collector.py'
        self.task=self.root/'task.json'

    def run_case(self, code, task=None):
        self.entry.write_text(HEADER+code,encoding='utf-8')
        self.task.write_text(json.dumps(task or {'completion':{'mode':'sample','min_records':1}}),encoding='utf-8')
        return run_collector(self.root,self.entry,self.task)

    def test_all_mode_obeys_minimum_even_when_source_exhausted(self):
        for count in (0,9,10):
            with self.subTest(records=count):
                rows='{}\n'*count
                result=self.run_case(f"(out/'normalized.jsonl').write_text({rows!r},encoding='utf-8')\n"+RESULT,
                    {'completion':{'mode':'all','min_records':10}})
                self.assertEqual(result.status,'completed' if count==10 else 'partial')
                self.assertEqual(result.completeness,'complete' if count==10 else 'partial')

    def test_conflicting_explicit_counts_are_rejected_before_execution(self):
        with self.assertRaises(RunError):
            self.run_case('',{'completion':{'mode':'all','min_records':10,'expected_total':2}})
        self.assertFalse((self.root/'runs').exists())

    def test_empty_expected_total_can_be_explicitly_valid(self):
        result=self.run_case("(out/'normalized.jsonl').write_text('',encoding='utf-8')\n"+RESULT,
            {'completion':{'mode':'all','expected_total':0}})
        self.assertEqual(result.status,'completed')

    def test_bad_output_encoding_still_writes_final_evidence(self):
        for filename in ('normalized.jsonl','collector_result.json'):
            with self.subTest(filename=filename):
                code="(out/'normalized.jsonl').write_text('{}\\n',encoding='utf-8')\n"+RESULT
                result=self.run_case(code+f"(out/{filename!r}).write_bytes(b'\\xff\\xfe')\n",
                    {'query':{'password':'synthetic-secret'},'completion':{'mode':'sample','min_records':1}})
                self.assertEqual(result.status,'failed')
                self.assertEqual(json.loads((result.run_dir/'run.json').read_text('utf-8'))['status'],'failed')
                self.assertFalse(json.loads((result.run_dir/'validation.json').read_text('utf-8'))['passed'])

    def test_spawn_error_still_writes_final_evidence(self):
        with patch('spider_core.runner._run_process',side_effect=OSError('synthetic spawn failure')):
            result=self.run_case('')
        self.assertEqual(result.status,'failed')
        self.assertTrue((result.run_dir/'run.json').is_file())

    def test_normal_exit_preserves_existing_background_process_behavior(self):
        marker=self.root/'normal_child_finished.txt'
        child_pid=self.root/'normal_child.pid'
        child_code=f'import time;from pathlib import Path;time.sleep(0.5);Path({str(marker)!r}).write_text("done")'
        try:
            result=self.run_case(
                "import subprocess,sys\n"
                "child=subprocess.Popen([sys.executable,'-c',"
                f"{child_code!r}],"
                "stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)\n"
                f"Path({str(child_pid)!r}).write_text(str(child.pid))\n"
                "(out/'normalized.jsonl').write_text('{}\\n',encoding='utf-8')\n"+RESULT)
            self.assertEqual(result.status,'completed')
            deadline=time.monotonic()+3
            while not marker.exists() and time.monotonic()<deadline:
                time.sleep(0.05)
            self.assertTrue(marker.exists(),'normal completion changed collector child lifetimes')
            self.assertTrue(child_pid.is_file())
        finally:
            # A written marker is not process exit. Release the child's inherited
            # working directory before TemporaryDirectory's registered cleanup.
            if child_pid.is_file():
                pid=int(child_pid.read_text())
                if os.name=='nt':
                    script=("$ErrorActionPreference='Stop'; "
                            f"try {{$p=[System.Diagnostics.Process]::GetProcessById({pid})}} "
                            "catch [System.ArgumentException] {exit 0}; "
                            "try {if (-not $p.WaitForExit(5000)) {throw 'test child did not exit'}} "
                            "finally {$p.Dispose()}")
                    subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],
                                   check=True,timeout=10,capture_output=True)
                else:
                    deadline=time.monotonic()+5
                    while True:
                        try:
                            os.kill(pid,0)
                        except ProcessLookupError:
                            break
                        self.assertLess(time.monotonic(),deadline,'test child did not exit')
                        time.sleep(0.05)

    def test_timeout_terminates_children_with_inherited_output_handles(self):
        child=self.root/'child.py'
        marker=self.root/'child_finished.txt'
        child.write_text("import time;from pathlib import Path;time.sleep(2);Path(__file__).with_name('child_finished.txt').write_text('late')",encoding='utf-8')
        timeout_seconds=1
        # runner allows 5s each for tree cleanup, output drain and final wait.
        # Leave 2s for process startup, evidence writes and scheduler variation.
        total_budget=timeout_seconds+5+5+5+2
        started=time.monotonic()
        result=self.run_case("import subprocess,sys,time\nsubprocess.Popen([sys.executable,str(Path(__file__).with_name('child.py'))])\ntime.sleep(10)\n",
                             {'execution':{'timeout_seconds':timeout_seconds}})
        elapsed=time.monotonic()-started
        self.assertEqual(result.status,'failed')
        self.assertEqual(json.loads((result.run_dir/'run.json').read_text('utf-8'))['stop_reason'],'collector_timeout')
        self.assertNotIn('cleanup could not be confirmed',(result.run_dir/'stderr.log').read_text('utf-8'))
        deadline=time.monotonic()+2
        while time.monotonic()<deadline:
            self.assertFalse(marker.exists(),'collector child kept running after timeout')
            time.sleep(0.05)
        self.assertFalse(marker.exists(),'collector child kept running after timeout')
        self.assertLess(elapsed,total_budget,'inherited stdout exceeded execution and cleanup budgets')

    @unittest.skipUnless(os.name=='nt','Windows system cleanup failure path')
    def test_timeout_cleanup_failure_still_writes_final_evidence(self):
        for failure in (subprocess.CompletedProcess([],1),OSError('taskkill unavailable'),
                        subprocess.TimeoutExpired('taskkill',5)):
            with self.subTest(failure=type(failure).__name__):
                kwargs={'side_effect':failure} if isinstance(failure,Exception) else {'return_value':failure}
                with patch('spider_core.runner.subprocess.run',**kwargs):
                    result=self.run_case('import time\ntime.sleep(10)\n',
                        {'execution':{'timeout_seconds':1}})
                self.assertEqual(result.status,'failed')
                self.assertEqual(json.loads((result.run_dir/'run.json').read_text('utf-8'))['stop_reason'],'collector_timeout')
                self.assertTrue((result.run_dir/'validation.json').is_file())
                self.assertIn('cleanup could not be confirmed',(result.run_dir/'stderr.log').read_text('utf-8'))
