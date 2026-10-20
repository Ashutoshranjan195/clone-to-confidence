from __future__ import annotations
import argparse,sys
from pathlib import Path
from .checks import audit
from .report import report
from .fixer import apply
from .verifier import verify
def path_arg(v):
 p=Path(v).expanduser().resolve()
 if not p.is_dir():raise argparse.ArgumentTypeError(f"repository path is not a directory: {v}")
 return p
def main(argv=None):
 parser=argparse.ArgumentParser(prog="clone-to-confidence",description="Prove whether a repository can be rebuilt on a clean machine."); sub=parser.add_subparsers(dest="command",required=True)
 a=sub.add_parser("audit",help="run eight deterministic static checks without executing repository code"); a.add_argument("path",type=path_arg); a.add_argument("--format",choices=("text","json"),default="text")
 v=sub.add_parser("verify",help="run static checks and an explicit Docker build when available"); v.add_argument("path",type=path_arg)
 f=sub.add_parser("fix",help="show or apply only safe deterministic fixes"); f.add_argument("path",type=path_arg); f.add_argument("--dry-run",action="store_true",help="show changes without writing (default)"); f.add_argument("--apply",action="store_true",help="write new files only; never overwrite")
 n=parser.parse_args(argv)
 if n.command=="audit":
  cs=audit(n.path); print(report(cs,n.path,n.format)); return 1 if any(c.status=="FAIL" for c in cs) else 0
 if n.command=="fix":
  ch=apply(n.path,dry_run=not n.apply); print("DRY RUN — no files changed." if not n.apply else "Applied safe fixes:")
  if not ch:print("No safe deterministic fixes identified.")
  for action,rel,content in ch:print(f"{action.upper()} {rel}\n{content.rstrip()}")
  return 0
 r=verify(n.path); print(report(r["static"],n.path)); print(f"\nDocker build: {r['docker']['status']}"); print(f"Tests: {r['tests']['status']}"); return 1 if any(c.status=="FAIL" for c in r["static"]) or r["docker"]["status"]=="FAIL" or r["tests"]["status"]=="FAIL" else 0
if __name__=="__main__":sys.exit(main())
