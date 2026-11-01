import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]

class DiskTests(unittest.TestCase):
    def load(self):
        path=ROOT/'agent_footprint/collect.py'
        self.assertTrue(path.exists(), 'metadata collector is missing')
        spec=importlib.util.spec_from_file_location('collect',path)
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
    def test_known_directories_only_and_no_contents_or_paths(self):
        m=self.load()
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);c=base/'secret-user-claude';x=base/'codex';(c/'projects').mkdir(parents=True)
            (c/'projects'/'private-project.jsonl').write_bytes(b'SECRET PROMPT')
            (c/'auth.json').write_bytes(b'not counted'*100)
            with patch.object(Path,'read_text',side_effect=AssertionError('contents read')),patch.object(Path,'read_bytes',side_effect=AssertionError('contents read')):
                r=m.collect_disk(c,x)
            self.assertEqual(r['totals']['logical_bytes'],13)
            self.assertEqual(r['totals']['files'],1)
            self.assertTrue(r['complete'])
            self.assertNotIn(tmp,json.dumps(r));self.assertNotIn('private-project',json.dumps(r));self.assertNotIn('SECRET',json.dumps(r))
    def test_hardlinks_deduplicate_across_categories(self):
        m=self.load()
        with tempfile.TemporaryDirectory() as tmp:
            c=Path(tmp)/'c';(c/'projects').mkdir(parents=True);(c/'debug').mkdir()
            p=c/'projects'/'a';p.write_bytes(b'12345')
            try:os.link(p,c/'debug'/'b')
            except OSError:self.skipTest('hardlinks unavailable')
            r=m.collect_disk(c,Path(tmp)/'x');self.assertEqual(r['totals']['logical_bytes'],5);self.assertEqual(r['totals']['files'],1)
    def test_zero_direntry_inode_uses_nofollow_path_metadata_for_hardlinks(self):
        m=self.load()
        import contextlib
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as tmp:
            c=Path(tmp)/'c';(c/'projects').mkdir(parents=True);(c/'debug').mkdir()
            original=c/'projects'/'a';original.write_bytes(b'12345')
            try:os.link(original,c/'debug'/'b')
            except OSError:self.skipTest('hardlinks unavailable')
            real_scandir=m.os.scandir
            class ZeroInodeEntry:
                def __init__(self,entry):self.entry=entry
                def __getattr__(self,name):return getattr(self.entry,name)
                def stat(self,*,follow_symlinks):
                    actual=self.entry.stat(follow_symlinks=follow_symlinks)
                    values={name:getattr(actual,name) for name in ('st_mode','st_dev','st_size')}
                    values['st_ino']=0
                    if hasattr(actual,'st_blocks'):values['st_blocks']=actual.st_blocks
                    return SimpleNamespace(**values)
            @contextlib.contextmanager
            def zero_inode_scandir(location):
                with real_scandir(location) as entries:
                    yield (ZeroInodeEntry(entry) for entry in entries)
            with patch.object(m.os,'scandir',side_effect=zero_inode_scandir):
                report=m.collect_disk(c,Path(tmp)/'x')
            self.assertEqual(report['totals']['files'],1)
            self.assertEqual(report['totals']['logical_bytes'],5)
    def test_symlink_files_directories_and_roots_are_skipped(self):
        m=self.load()
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);c=base/'c';(c/'projects').mkdir(parents=True);outside=base/'outside';outside.mkdir();(outside/'secret').write_bytes(b'secret')
            try:
                (c/'projects'/'escape').symlink_to(outside,target_is_directory=True)
                (c/'projects'/'file').symlink_to(outside/'secret')
                (base/'x').symlink_to(c,target_is_directory=True)
            except OSError:self.skipTest('symlinks unavailable')
            r=m.collect_disk(c,base/'x');self.assertEqual(r['totals']['files'],0)
            self.assertGreaterEqual(sum(v['skipped_symlinks'] for v in r['categories']),2)
            self.assertFalse(r['complete'])
    def test_file_budget_is_shared_and_marks_partial(self):
        m=self.load()
        with tempfile.TemporaryDirectory() as tmp:
            c=Path(tmp)/'c';(c/'projects').mkdir(parents=True)
            for i in range(10):(c/'projects'/str(i)).write_bytes(b'x')
            r=m.collect_disk(c,Path(tmp)/'x',max_files=2)
            self.assertLessEqual(r['totals']['files'],2);self.assertFalse(r['complete']);self.assertTrue(r['limit_reached'])
    def test_expired_time_budget_is_not_success(self):
        m=self.load()
        with tempfile.TemporaryDirectory() as tmp:
            c=Path(tmp)/'c';(c/'projects').mkdir(parents=True);(c/'projects'/'a').write_bytes(b'x')
            r=m.collect_disk(c,Path(tmp)/'x',timeout=0)
            self.assertTrue(r['limit_reached']);self.assertFalse(r['complete'])
    @unittest.skipIf(os.name=='nt','POSIX sparse metadata')
    def test_sparse_logical_and_allocated_are_separate(self):
        m=self.load()
        with tempfile.TemporaryDirectory() as tmp:
            c=Path(tmp)/'c';(c/'projects').mkdir(parents=True)
            with (c/'projects'/'sparse').open('wb') as f:f.truncate(8*1024*1024)
            r=m.collect_disk(c,Path(tmp)/'x')
            self.assertEqual(r['totals']['logical_bytes'],8*1024*1024)
            self.assertLess(r['totals']['allocated_bytes'],r['totals']['logical_bytes'])
    @unittest.skipUnless(hasattr(os,'mkfifo'),'FIFO support')
    def test_fifo_is_not_opened_or_counted(self):
        m=self.load()
        with tempfile.TemporaryDirectory() as tmp:
            c=Path(tmp)/'c';(c/'projects').mkdir(parents=True);os.mkfifo(c/'projects'/'fifo')
            r=m.collect_disk(c,Path(tmp)/'x');self.assertEqual(r['totals']['files'],0)
    def test_permission_failure_is_partial_without_path_disclosure(self):
        m=self.load()
        with tempfile.TemporaryDirectory() as tmp:
            c=Path(tmp)/'c';(c/'projects').mkdir(parents=True)
            with patch.object(m.os,'scandir',side_effect=PermissionError('PRIVATE-PATH')):
                r=m.collect_disk(c,Path(tmp)/'x')
            self.assertFalse(r['complete']);self.assertFalse(r['limit_reached'])
            self.assertNotIn('PRIVATE',json.dumps(r));self.assertGreater(sum(v['errors'] for v in r['categories']),0)
    def test_reparse_points_are_links_even_with_directory_mode(self):
        m=self.load()
        self.assertTrue(hasattr(m,'_is_link'),'Windows reparse protection missing')
        from types import SimpleNamespace
        self.assertTrue(m._is_link(SimpleNamespace(st_mode=0o040755,st_file_attributes=0x400)))
        self.assertFalse(m._is_link(SimpleNamespace(st_mode=0o040755)))
    def test_nonfinite_time_budget_refused(self):
        m=self.load()
        for value in (float('inf'),float('nan')):
            with self.assertRaises(ValueError):m.collect_disk(Path('/none'),Path('/none'),timeout=value)
    def test_bad_budgets_refused(self):
        m=self.load()
        for kw in ({'max_files':0},{'max_files':-1},{'timeout':-1}):
            with self.assertRaises(ValueError):m.collect_disk(Path('/none'),Path('/none'),**kw)

if __name__=='__main__':unittest.main()
