import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]

class WorktreeTests(unittest.TestCase):
    def load(self):
        path=ROOT/'agent_footprint/worktrees.py';self.assertTrue(path.exists(),'worktree inspector is missing')
        spec=importlib.util.spec_from_file_location('worktrees',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
    def test_no_projects_does_not_start_git(self):
        m=self.load()
        with patch.object(m,'run_bounded',side_effect=AssertionError('must not invoke git')):
            r=m.inspect_projects([])
        self.assertEqual(r['status'],'not_requested');self.assertEqual(r['worktrees'],0)
    @unittest.skipUnless(shutil.which('git'),'Git is optional')
    def test_actual_registered_worktree_with_spaces_and_no_file_read(self):
        m=self.load()
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);project=base/'private project';project.mkdir()
            def git(*args):
                subprocess.run(['git','-C',str(project),*args],check=True,capture_output=True)
            git('init');git('-c','user.name=Test','-c','user.email=test@example.invalid','commit','--allow-empty','-m','fixture')
            git('worktree','add','-b','private-branch',str(base/'other worktree'))
            (project/'PRIVATE-SECRET').write_text('never read')
            r=m.inspect_projects([project])
            self.assertEqual(r['status'],'available');self.assertEqual(r['worktrees'],2)
            self.assertNotIn(tmp,json.dumps(r));self.assertNotIn('private-branch',json.dumps(r))
            self.assertNotIn('dirty',r);self.assertNotIn('clean',r)
    def test_duplicate_registrations_count_once_and_only_list_is_called(self):
        m=self.load();out='worktree /private/repo\x00HEAD abc\x00branch refs/heads/main\x00\x00worktree /private/other\x00HEAD def\x00\x00'
        with patch.object(m,'run_bounded',return_value=subprocess.CompletedProcess([],0,out,'')) as run:
            r=m.inspect_projects([Path('/private/repo'),Path('/private/other')])
        self.assertEqual(r['worktrees'],2)
        for call in run.call_args_list:
            self.assertIn('list',call.args[0]);self.assertNotIn('status',call.args[0]);self.assertNotIn('shell',call.kwargs)
            self.assertLessEqual(call.kwargs['timeout'],5)
    def test_failures_are_partial_without_private_stderr(self):
        m=self.load()
        with patch.object(m,'run_bounded',return_value=subprocess.CompletedProcess([],1,'','PRIVATE-TOKEN')):
            r=m.inspect_projects([Path('/private-name')])
        self.assertEqual(r['status'],'partial');self.assertEqual(r['unavailable'],1)
        self.assertNotIn('PRIVATE',json.dumps(r));self.assertNotIn('private-name',json.dumps(r))
    def test_timeout_is_partial(self):
        m=self.load()
        with patch.object(m,'run_bounded',side_effect=subprocess.TimeoutExpired(['git'],5)):
            self.assertEqual(m.inspect_projects([Path('/none')])['status'],'partial')
    def test_project_count_is_capped(self):
        m=self.load();out='worktree /repo\x00HEAD abc\x00\x00'
        with patch.object(m,'run_bounded',return_value=subprocess.CompletedProcess([],0,out,'')) as run:
            r=m.inspect_projects([Path('/repo'+str(i)) for i in range(30)])
        self.assertLessEqual(run.call_count,20);self.assertEqual(r['status'],'partial')

if __name__=='__main__':unittest.main()
