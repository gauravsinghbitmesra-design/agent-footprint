import importlib.util
from pathlib import Path
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]

class BoundedProcessTests(unittest.TestCase):
    def load(self):
        path=ROOT/'agent_footprint/subprocesses.py'
        self.assertTrue(path.exists(),'bounded subprocess helper is missing')
        spec=importlib.util.spec_from_file_location('bounded_processes',path)
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

    def test_success_unicode_and_nonzero(self):
        m=self.load()
        result=m.run_bounded([sys.executable,'-c',"import sys;sys.stdout.buffer.write('hello \\u2603'.encode('utf-8'));sys.exit(3)"],timeout=3)
        self.assertEqual(result.stdout,'hello \u2603');self.assertEqual(result.returncode,3)
        self.assertEqual(result.stderr,'')

    def test_stdout_overflow_fails_while_child_is_still_writing(self):
        m=self.load();start=time.monotonic()
        with self.assertRaises(subprocess.SubprocessError):
            m.run_bounded([sys.executable,'-c',"import os,time;os.write(1,b'x'*1000000);time.sleep(10)"],timeout=3,max_bytes=4096)
        self.assertLess(time.monotonic()-start,2)

    def test_huge_stderr_is_discarded(self):
        m=self.load()
        result=m.run_bounded([sys.executable,'-c',"import os;os.write(2,b'x'*2000000);print('ok')"],timeout=3,max_bytes=4096)
        self.assertEqual(result.stdout,'ok\n');self.assertEqual(result.stderr,'')

    def test_timeout_kills_and_reaps_child(self):
        m=self.load();start=time.monotonic()
        launched=[]
        original=m.subprocess.Popen
        def record(*args,**kwargs):
            child=original(*args,**kwargs);launched.append(child);return child
        with patch.object(m.subprocess,'Popen',side_effect=record),self.assertRaises(subprocess.TimeoutExpired):
            m.run_bounded([sys.executable,'-c','import time;time.sleep(10)'],timeout=.1)
        self.assertLess(time.monotonic()-start,2)
        self.assertEqual(len(launched),1);self.assertIsNotNone(launched[0].returncode)

    def test_inherited_stdout_does_not_hold_parent_forever(self):
        m=self.load();start=time.monotonic()
        code="import subprocess,sys;subprocess.Popen([sys.executable,'-c','import time;time.sleep(1)']);print('parent done')"
        with self.assertRaises(subprocess.TimeoutExpired):
            m.run_bounded([sys.executable,'-c',code],timeout=.1)
        self.assertLess(time.monotonic()-start,.9)

    def test_invalid_limits_refused(self):
        m=self.load()
        for kwargs in ({'timeout':0},{'timeout':float('inf')},{'timeout':float('nan')},{'timeout':1,'max_bytes':0}):
            with self.assertRaises(ValueError):m.run_bounded([sys.executable,'-c','pass'],**kwargs)

if __name__=='__main__':unittest.main()
