import importlib.util
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]

class ProcessTests(unittest.TestCase):
    def load(self):
        path=ROOT/'agent_footprint/processes.py';self.assertTrue(path.exists(),'process collector is missing')
        spec=importlib.util.spec_from_file_location('processes',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
    def test_exact_names_current_user_only_and_no_paths(self):
        m=self.load()
        text='''100 1 501 2048 12.5 /Users/private/.bin/claude
101 1 501 1024 0.1 /Applications/Codex.app/Contents/MacOS/Codex
102 1 502 99 0.0 /bin/codex
103 1 501 99 0.0 /bin/node
104 1 501 99 0.0 /bin/claude-helper
105 1 501 99 0.0 /bin/python
'''
        items=m.parse_ps(text,501)
        self.assertEqual(len(items),2);self.assertEqual(items[0]['rss_bytes'],2048*1024)
        self.assertEqual({i['agent'] for i in items},{'Claude Code','Codex'})
        self.assertNotIn('private',json.dumps(items));self.assertNotIn('ppid',json.dumps(items))
    def test_malformed_negative_or_nonfinite_metrics_ignored(self):
        m=self.load()
        text='1 0 501 -1 0 claude\n2 0 501 9 nan codex\n3 0 501 9 inf codex\n4 0 501 9 1 codex --token=SECRET\nnot a process\n'
        self.assertEqual(m.parse_ps(text,501),[])
    def test_collect_uses_no_args_and_timeout(self):
        m=self.load()
        if not hasattr(m.os,'getuid'):self.skipTest('POSIX only')
        result=subprocess.CompletedProcess([],0,f'100 1 {m.os.getuid()} 2048 12.5 /bin/claude\n','')
        with patch.object(m,'run_bounded',return_value=result) as run:
            r=m.collect_processes()
        self.assertEqual(r['status'],'available');self.assertEqual(r['total_rss_bytes'],2048*1024)
        self.assertNotIn('args',repr(run.call_args));self.assertNotIn('capture_output',run.call_args.kwargs);self.assertGreater(run.call_args.kwargs['timeout'],0)
    def test_subprocess_failure_does_not_leak_stderr(self):
        m=self.load()
        with patch.object(m,'run_bounded',return_value=subprocess.CompletedProcess([],1,'','SECRET USER')):
            r=m.collect_processes()
        self.assertEqual(r['status'],'unavailable');self.assertNotIn('SECRET',json.dumps(r))
    def test_timeout_is_unavailable(self):
        m=self.load()
        with patch.object(m,'run_bounded',side_effect=subprocess.TimeoutExpired(['ps'],3)):
            self.assertEqual(m.collect_processes()['status'],'unavailable')

if __name__=='__main__':unittest.main()
