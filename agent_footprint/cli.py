"""CLI orchestration; scanners are imported only for a real observation."""
import argparse
import math
from pathlib import Path
import sys

from . import __version__
from .report import demo_report, make_report, render_html, render_json, render_text, write_output


def positive_int(value):
    number=int(value)
    if not 1 <= number <= 1000000:
        raise argparse.ArgumentTypeError('must be between 1 and 1000000')
    return number


def timeout_seconds(value):
    number=float(value)
    if not math.isfinite(number) or not 0 < number <= 300:
        raise argparse.ArgumentTypeError('must be a finite number greater than 0 and at most 300')
    return number


def main(argv=None):
    parser=argparse.ArgumentParser(description='Read-only local footprint of Claude Code and Codex. No API key or cleanup.')
    parser.add_argument('--version',action='version',version=__version__)
    parser.add_argument('--demo',action='store_true',help='Synthetic demo; inspect no local agent data or processes')
    parser.add_argument('--format',choices=('text','json','html'),default='text')
    parser.add_argument('--output',type=Path,help='Create a NEW report file; existing files and symlinks are refused')
    parser.add_argument('--claude-home',type=Path,default=Path.home()/'.claude',help='Explicit Claude data root (default: ~/.claude)')
    parser.add_argument('--codex-home',type=Path,default=Path.home()/'.codex',help='Explicit Codex data root (default: ~/.codex)')
    parser.add_argument('--project',type=Path,action='append',default=[],help='Opt-in Git registration count for one trusted repository; repeat up to 20')
    parser.add_argument('--max-files',type=positive_int,default=100000,help='Traversal entry budget, including directories (default: 100000)')
    parser.add_argument('--timeout',type=timeout_seconds,default=10,help='Disk traversal seconds (default: 10); process and Git checks have separate fixed bounds')
    parser.add_argument('--no-processes',action='store_true',help='Skip ps process observation')
    args=parser.parse_args(argv)
    if len(args.project)>20:
        parser.error('at most 20 projects are permitted')
    try:
        if args.demo:
            data=demo_report()
        else:
            from .collect import collect_disk
            from .processes import collect_processes
            from .worktrees import inspect_projects
            disk=collect_disk(args.claude_home.expanduser(),args.codex_home.expanduser(),max_files=args.max_files,timeout=args.timeout)
            processes=({'status':'unavailable','items':[],'total_rss_bytes':None,'notes':['Process observation skipped by request.']}
                       if args.no_processes else collect_processes())
            worktrees=inspect_projects([p.expanduser() for p in args.project])
            data=make_report(disk,processes,worktrees)
        output={'text':render_text,'json':render_json,'html':render_html}[args.format](data)
        if args.output:
            write_output(args.output.expanduser(),output)
            print('Report saved to the requested new file. Review before sharing.',file=sys.stderr)
        else:
            # Stable UTF-8 pipes on Windows and legacy terminal locales.
            if hasattr(sys.stdout, 'reconfigure'):
                sys.stdout.reconfigure(encoding='utf-8')
            sys.stdout.write(output)
        return 0
    except (OSError, ValueError) as error:
        if isinstance(error,FileExistsError):
            message='Output already exists. Choose a new filename; nothing was overwritten.'
        else:
            message='Could not complete the report. Check filesystem permissions and output location.'
        print('Error: '+message,file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print('Interrupted. No cleanup was performed.',file=sys.stderr)
        return 130


if __name__=='__main__':
    raise SystemExit(main())
