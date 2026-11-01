"""Aggregate-only rendering. No external assets, telemetry or file-content reads."""
from datetime import datetime, timezone
from html import escape
import json
import os
from pathlib import Path

from . import __version__

LIMITS = [
    'Observed storage is not reclaimable space. Sessions and worktrees may contain valuable work.',
    'Allocated bytes sum file blocks; compression and shared APFS copies can make this differ from unique physical storage.',
    'Process attribution uses executable names, not authenticated ownership by an agent session. Generic runtimes and many helpers are excluded.',
    'RSS is a process snapshot, not a RAM leak diagnosis; shared pages may be counted more than once.',
    'Prompt, transcript, credential and project file contents are not read; environment values are not included in reports. No cleanup is performed.',
]


def make_report(disk, processes, worktrees, *, demo=False):
    return {'schema_version': 1, 'version': __version__, 'demo': demo,
            'generated_at': '2026-11-01T00:00:00Z' if demo else datetime.now(timezone.utc).isoformat(),
            'disk': disk, 'processes': processes, 'worktrees': worktrees, 'limitations': list(LIMITS)}


def demo_report():
    mib = 1024 ** 2
    rows = [
        {'agent': 'Claude Code', 'category': 'Session data', 'logical_bytes': 640*mib, 'allocated_bytes': 648*mib, 'files': 1200},
        {'agent': 'Claude Code', 'category': 'Debug logs', 'logical_bytes': 180*mib, 'allocated_bytes': 184*mib, 'files': 420},
        {'agent': 'Codex', 'category': 'Session data', 'logical_bytes': 420*mib, 'allocated_bytes': 424*mib, 'files': 800},
        {'agent': 'Codex', 'category': 'Worktrees', 'logical_bytes': 800*mib, 'allocated_bytes': 816*mib, 'files': 3200},
    ]
    for row in rows:
        row.update(status='complete', skipped_symlinks=0, errors=0)
    disk = {'categories': rows, 'totals': {key: sum(r[key] for r in rows) for key in ('files','logical_bytes','allocated_bytes')},
            'complete': True, 'limit_reached': False, 'notes': ['Synthetic numbers; not measurements from a real laptop.']}
    processes = {'status': 'available', 'items': [{'agent': 'Claude Code', 'pid': 101, 'rss_bytes': 240*mib, 'cpu_percent': 1.2},
                                               {'agent': 'Codex', 'pid': 102, 'rss_bytes': 160*mib, 'cpu_percent': 0.3}],
                 'total_rss_bytes': 400*mib, 'notes': ['Synthetic process snapshot.']}
    worktrees = {'status': 'available', 'projects': 1, 'worktrees': 3, 'unavailable': 0,
                 'notes': ['Registration counts only; no file status or cleanup eligibility inferred.']}
    return make_report(disk, processes, worktrees, demo=True)


def size(value):
    if value is None:
        return 'Unavailable'
    number = float(value)
    for unit in ('B', 'KiB', 'MiB', 'GiB', 'TiB'):
        if abs(number) < 1024 or unit == 'TiB':
            return f'{number:,.1f} {unit}' if unit != 'B' else f'{int(number):,} B'
        number /= 1024


def coverage(data):
    disk=data['disk']
    return ('Complete for selected categories' if disk['complete'] else
            'Partial scan — observed totals are a lower bound')


def findings(data):
    rows=[r for r in data['disk']['categories'] if r['logical_bytes'] > 0]
    notes=[]
    if rows:
        biggest=max(rows, key=lambda r:r['logical_bytes'])
        notes.append(f"Largest observed category: {biggest['agent']} / {biggest['category']} ({size(biggest['logical_bytes'])}). Review its purpose before removing anything.")
    else:
        notes.append('No file bytes observed in the selected categories. Missing or inaccessible data is not proof an agent is absent.')
    if not data['disk']['complete']:
        notes.append('Coverage is partial. Inspect category states; increase scan budgets only if appropriate. Do not treat these counts as a full inventory.')
    notes.append('Compare the same workload and scan scope over time. A single snapshot cannot establish that agents caused a slowdown.')
    notes.append('Use this aggregate report with Claude or Codex to discuss the evidence. Ask for an explained plan before any separate cleanup.')
    return notes


def render_text(data):
    lines=['AGENT FOOTPRINT'+(' | Synthetic demo' if data['demo'] else ''),
           'Read-only · local · no API key', '', coverage(data),
           f"Observed logical storage: {size(data['disk']['totals']['logical_bytes'])}",
           f"Observed allocated file blocks: {size(data['disk']['totals']['allocated_bytes'])}",
           f"Files counted: {data['disk']['totals']['files']:,}",
           f"Selected process RSS: {size(data['processes']['total_rss_bytes'])}", '',
           'AGENT / CATEGORY                         LOGICAL       ALLOCATED      FILES  STATE']
    for row in data['disk']['categories']:
        label=f"{row['agent']} / {row['category']}"
        lines.append(f"{label:<40} {size(row['logical_bytes']):>12} {size(row['allocated_bytes']):>12} {row['files']:>8,}  {row['status']}")
    lines += ['', 'PROCESSES (selected executable names only)']
    if data['processes']['status']!='available': lines.append('Unavailable')
    for row in data['processes']['items']:
        lines.append(f"{row['agent']}: PID {row['pid']}, RSS {size(row['rss_bytes'])}, ps-reported CPU {row['cpu_percent']}%")
    worktrees=data['worktrees']
    lines += ['', f"Worktree registration checks: {worktrees['status']}",
              f"Projects checked: {worktrees['projects']} · Registered worktrees: {worktrees['worktrees']} · Unavailable: {worktrees['unavailable']}",
              '', 'NEXT STEPS']
    lines += ['- '+note for note in findings(data)]
    lines += ['', 'COVERAGE & LIMITS']
    for group in ('disk','processes','worktrees'):
        lines += ['- '+note for note in data[group]['notes']]
    lines += ['- '+note for note in data['limitations']]
    return '\n'.join(lines)+'\n'


STYLE = '''
:root{color-scheme:dark;--bg:#0b1215;--panel:#121d23;--line:#293a42;--text:#e8f0ef;--muted:#a5babd;--accent:#88e7b6}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:16px/1.6 system-ui,-apple-system,sans-serif}main{max-width:1100px;margin:auto;padding:44px 24px}header{border-bottom:1px solid var(--line);padding-bottom:26px}h1{font-size:clamp(32px,6vw,56px);letter-spacing:-2px;margin:8px 0}h2{font-size:22px;margin:0 0 16px}.eyebrow{color:var(--accent);font:12px/1.5 monospace;letter-spacing:2px}p{margin:8px 0;color:var(--muted)}.badge{display:inline-block;border:1px solid var(--line);border-radius:30px;padding:5px 12px;color:var(--accent);font-size:13px}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin:24px 0}.card,section{min-width:0;background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:22px}section{margin:20px 0}.number{font-size:30px;line-height:1.3;letter-spacing:-1px}.label{color:var(--muted);font-size:13px;margin-top:6px}.table-wrap{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:14px}th{text-align:left;color:var(--muted);font-weight:500}td,th{padding:12px 10px;border-bottom:1px solid var(--line)}td:first-child{padding-left:0}li{margin:9px 0;color:var(--muted)}.status{color:var(--accent)}footer{color:var(--muted);font-size:12px;margin:28px 0;overflow-wrap:anywhere}.warning{border-left:3px solid var(--accent);padding:10px 16px;margin:20px 0;overflow-wrap:anywhere}small{color:var(--muted)}
@media(max-width:640px){main{padding:24px 14px}.grid{grid-template-columns:minmax(0,1fr)}.card,section{padding:16px}.number{font-size:27px}h1{letter-spacing:-1px}}
@media print{:root{--bg:white;--panel:white;--text:#111;--muted:#444;--line:#ddd;--accent:#17643a;color-scheme:light}main{max-width:none;padding:0}.card,section{break-inside:avoid}h1{font-size:36px}}
'''


def render_html(data):
    e=lambda v:escape(str(v), quote=True)
    total=data['disk']['totals']
    rows=''.join('<tr>'+''.join(f'<td>{e(v)}</td>' for v in
                 (r['agent'],r['category'],size(r['logical_bytes']),size(r['allocated_bytes']),f"{r['files']:,}",r['status']))+'</tr>'
                 for r in data['disk']['categories'])
    processes=''.join('<tr>'+''.join(f'<td>{e(v)}</td>' for v in
                      (r['agent'],r['pid'],size(r['rss_bytes']),str(r['cpu_percent'])+'%'))+'</tr>' for r in data['processes']['items'])
    if not processes: processes='<tr><td colspan="4">'+('Unavailable' if data['processes']['status']!='available' else 'No matching executable names observed')+'</td></tr>'
    list_html=lambda notes:'<ul>'+''.join(f'<li>{e(n)}</li>' for n in notes)+'</ul>'
    all_notes=[n for group in ('disk','processes','worktrees') for n in data[group]['notes']]+data['limitations']
    demo='<span class="badge">Synthetic demo · not a real laptop measurement</span>' if data['demo'] else '<span class="badge">Local observation · no cleanup performed</span>'
    wt=data['worktrees']
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="color-scheme" content="dark light"><title>Agent Footprint report</title><style>{STYLE}</style></head>
<body><main><header><div class="eyebrow">DEVELOPER TOOLS / AGENT FOOTPRINT</div><h1>Know what your agents leave behind.</h1><p>Claude Code &amp; Codex · file metadata and selected process statistics</p>{demo}</header>
<div class="warning">{e(coverage(data))}. Observed storage is <strong>not reclaimable</strong> space.</div>
<div class="grid"><div class="card"><div class="number">{e(size(total['logical_bytes']))}</div><div class="label">Observed logical file size</div></div><div class="card"><div class="number">{e(size(total['allocated_bytes']))}</div><div class="label">Observed allocated file blocks</div></div><div class="card"><div class="number">{e(size(data['processes']['total_rss_bytes']))}</div><div class="label">Selected process RSS · not exclusive memory</div></div></div>
<section><h2>Where the bytes are</h2><p>{total['files']:,} files counted. Missing categories are shown rather than hidden.</p><div class="table-wrap"><table><thead><tr><th>Agent</th><th>Category</th><th>Logical</th><th>Allocated</th><th>Files</th><th>Coverage</th></tr></thead><tbody>{rows}</tbody></table></div></section>
<section><h2>Process snapshot</h2><p>Exact executable-name matches for the current user; generic runtimes and many helpers are excluded.</p><div class="table-wrap"><table><thead><tr><th>Agent</th><th>PID</th><th>RSS</th><th>ps-reported CPU</th></tr></thead><tbody>{processes}</tbody></table></div></section>
<section><h2>Worktree registrations</h2><p>{e(wt['status'])} · {wt['projects']} projects checked · {wt['worktrees']} registered worktrees · {wt['unavailable']} unavailable</p><p>Counts include the main checkout. No project names, branches, tracked file contents or cleanup eligibility are inspected.</p></section>
<section><h2>What to do next</h2>{list_html(findings(data))}</section><section><h2>Read the limits before acting</h2>{list_html(all_notes)}</section><footer>Agent Footprint {e(data['version'])} · schema {data['schema_version']} · {e(data['generated_at'])}<br>Review before sharing. Aggregate reports omit personal paths, project names and process arguments; they are not a proof of anonymity.</footer></main></body></html>'''


def write_output(path, content):
    """Create a private new file, never overwrite existing files or symlinks."""
    fd=os.open(Path(path), os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
    with os.fdopen(fd,'w',encoding='utf-8',newline='\n') as output:
        output.write(content)


def render_json(data):
    return json.dumps(data, indent=2, ensure_ascii=True)+'\n'
