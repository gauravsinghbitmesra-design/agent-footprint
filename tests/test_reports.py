import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ReportTests(unittest.TestCase):
    def api(self):
        self.assertIsNotNone(importlib.util.find_spec('agent_footprint.report'), 'report module not implemented')
        from agent_footprint import report
        return report

    def test_demo_is_explicit_and_deterministic(self):
        m=self.api(); data=m.demo_report()
        self.assertEqual(data,m.demo_report())
        self.assertTrue(data['demo']); self.assertEqual(data['schema_version'],1)
        self.assertNotIn('/Users/',json.dumps(data))

    def test_html_escapes_dynamic_content_and_has_no_remote_assets(self):
        m=self.api(); data=m.demo_report()
        data['disk']['categories'][0]['category']='<script>alert(1)</script>'
        html=m.render_html(data)
        self.assertIn('&lt;script&gt;',html); self.assertNotIn('<script>',html)
        self.assertNotIn('https://',html); self.assertNotIn('http://',html)
        self.assertIn('Synthetic demo',html); self.assertIn('viewport',html)

    def test_text_distinguishes_observed_storage_from_reclaimable(self):
        m=self.api(); text=m.render_text(m.demo_report())
        self.assertIn('observed',text.lower()); self.assertIn('not reclaimable',text.lower())
        self.assertNotIn('freed',text.lower())

    def test_unknown_allocation_and_process_data_stay_unknown(self):
        m=self.api(); data=m.demo_report()
        data['disk']['totals']['allocated_bytes']=None
        data['processes']={'status':'unavailable','items':[], 'total_rss_bytes':None,'notes':['Not supported.']}
        for text in (m.render_text(data),m.render_html(data)):
            self.assertIn('Unavailable',text)

    def test_partial_scan_warning_is_visible_in_both_formats(self):
        m=self.api(); data=m.demo_report(); data['disk']['complete']=False
        for text in (m.render_text(data),m.render_html(data)):
            self.assertIn('Partial',text); self.assertIn('lower bound',text)

    def test_write_refuses_existing_files_and_symlinks(self):
        m=self.api()
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/'report.html'; target.write_text('keep')
            with self.assertRaises(FileExistsError): m.write_output(target,'overwrite')
            self.assertEqual(target.read_text(),'keep')
            link=Path(tmp)/'link'
            try: link.symlink_to(target)
            except OSError: return
            with self.assertRaises(FileExistsError): m.write_output(link,'overwrite')

    def test_output_is_private_on_posix(self):
        import os,stat
        m=self.api()
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'report.txt';m.write_output(p,'hello')
            self.assertEqual(p.read_text(),'hello')
            if os.name!='nt': self.assertEqual(stat.S_IMODE(p.stat().st_mode),0o600)

    def test_cli_demo_json_and_no_overwrite(self):
        p=subprocess.run([sys.executable,'run.py','--demo','--format','json'],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertTrue(json.loads(p.stdout)['demo'])
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'report.json';path.write_text('keep')
            p=subprocess.run([sys.executable,'run.py','--demo','--format','json','--output',str(path)],cwd=ROOT,capture_output=True,text=True)
            self.assertNotEqual(p.returncode,0);self.assertEqual(path.read_text(),'keep')
            self.assertNotIn('Traceback',p.stderr)

    def test_cli_stdout_is_utf8_even_with_legacy_locale(self):
        import os
        env=dict(os.environ, PYTHONIOENCODING='ascii')
        p=subprocess.run([sys.executable,'run.py','--demo'],cwd=ROOT,env=env,capture_output=True)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn('Read-only · local',p.stdout.decode('utf-8'))

    def test_cli_rejects_invalid_budgets(self):
        for opts in (['--max-files','0'],['--timeout','-1'],['--timeout','nan'],['--timeout','inf']):
            p=subprocess.run([sys.executable,'run.py',*opts],cwd=ROOT,capture_output=True,text=True)
            self.assertNotEqual(p.returncode,0)
            self.assertNotIn('Traceback',p.stderr)
            self.assertIn('usage:',p.stderr.lower())


if __name__=='__main__': unittest.main()
