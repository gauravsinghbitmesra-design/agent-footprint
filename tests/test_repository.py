"""Public-artifact and clone usability checks. Never inspect real agent data."""
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import unquote, urlsplit

ROOT=Path(__file__).resolve().parents[1]


class RepositoryTests(unittest.TestCase):
    def test_relative_document_links_exist(self):
        for doc in [ROOT/'README.md',ROOT/'AGENTS.md',ROOT/'CLAUDE.md',ROOT/'PROMPT.md',*list((ROOT/'docs').rglob('*.md'))]:
            for target in re.findall(r'\]\(([^)\s]+)\)',doc.read_text(encoding='utf-8')):
                if urlsplit(target).scheme or target.startswith('#'): continue
                self.assertTrue((doc.parent/unquote(target.split('#')[0])).exists(),f'{doc.name}: {target}')

    def test_committed_examples_are_current_synthetic_data(self):
        from agent_footprint.report import demo_report, render_html
        data=json.loads((ROOT/'examples/demo.json').read_text(encoding='utf-8'))
        self.assertTrue(data['demo']); self.assertEqual(data,demo_report())
        self.assertEqual((ROOT/'examples/demo.html').read_text(encoding='utf-8'),render_html(demo_report()))

    def test_public_examples_have_no_private_paths_or_remote_resources(self):
        for name in ('demo.html','demo.json'):
            text=(ROOT/'examples'/name).read_text(encoding='utf-8')
            self.assertNotIn('/Users/',text); self.assertNotIn('C:\\Users\\',text)
            self.assertNotIn('http://',text); self.assertNotIn('https://',text)
            self.assertIn('Synthetic',text)

    def test_private_reports_are_gitignored(self):
        for name in ('reports/real.json','footprint.local.html','.env','state/real.json'):
            p=subprocess.run(['git','check-ignore','-q',name],cwd=ROOT)
            self.assertEqual(p.returncode,0,name)

    def test_fixture_cli_redacts_names_and_contents_in_all_formats(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);claude=root/'private-user';codex=root/'private-codex';(claude/'projects'/'secret-project').mkdir(parents=True)
            (claude/'projects'/'secret-project'/'PRIVATE-TOKEN.jsonl').write_text('never-read-secret-token',encoding='utf-8')
            for form in ('text','json','html'):
                p=subprocess.run([sys.executable,'run.py','--claude-home',str(claude),'--codex-home',str(codex),'--no-processes','--format',form],cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
                self.assertEqual(p.returncode,0,p.stderr)
                for secret in (tmp,'private-user','private-codex','secret-project','PRIVATE-TOKEN','never-read-secret-token'):
                    self.assertNotIn(secret,p.stdout)
                if form=='json':
                    data=json.loads(p.stdout)
                    self.assertEqual(data['disk']['totals']['logical_bytes'],23)
                    self.assertEqual(data['disk']['totals']['files'],1)
                    self.assertFalse(data['demo'])


if __name__=='__main__': unittest.main()
