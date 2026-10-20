from __future__ import annotations
import re, subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
PASS, FAIL, WARN, SKIPPED, UNSUPPORTED = "PASS", "FAIL", "WARN", "SKIPPED", "UNSUPPORTED"
TEXT_EXTENSIONS={".md",".txt",".toml",".yaml",".yml",".json",".ini",".cfg",".py",".js",".ts",".sh",".env",".example"}
EXCLUDED={".git",".venv","venv","node_modules","__pycache__",".pytest_cache","dist","build",".tox"}
@dataclass
class Check:
 id:str; name:str; status:str; explanation:str; evidence:list[str]; remediation:str
 def to_dict(self): return asdict(self)
def _run(args,cwd,timeout=10):
 try:
  p=subprocess.run(args,cwd=cwd,capture_output=True,text=True,timeout=timeout); return p.returncode,(p.stdout+p.stderr).strip()
 except FileNotFoundError:return None,"tool not installed"
 except subprocess.TimeoutExpired:return 124,"command timed out"
 except OSError as e:return 125,str(e)
def _files(root):
 for p in root.rglob("*"):
  if any(x in EXCLUDED for x in p.relative_to(root).parts) or p.is_symlink() or not p.is_file():continue
  if p.suffix.lower() in TEXT_EXTENSIONS or p.name in {"Dockerfile","Makefile","Procfile"}:yield p
def _manifest(root):
 maps={"pyproject.toml":"uv.lock","package.json":"package-lock.json","Cargo.toml":"Cargo.lock","go.mod":"go.sum"}
 found=[x for x in maps if (root/x).exists()]
 if not found and (root/"requirements.txt").exists(): return (["requirements.txt"],[])
 return (found,[maps[x] for x in found if (root/maps[x]).exists()]) if found else (None,[])
def git_history(root):
 c,o=_run(["git","rev-parse","--is-inside-work-tree"],root)
 if c is None:return Check("git_history","Git history",UNSUPPORTED,"Git is not installed.",[],"Install Git and initialize a repository.")
 if c:return Check("git_history","Git history",FAIL,"The target is not a Git work tree.",[],"Run git init and create at least one commit.")
 c,o=_run(["git","rev-list","--count","HEAD"],root)
 if c==0 and o.isdigit() and int(o)>0:return Check("git_history","Git history",PASS,"Git history contains at least one commit.",[f"{o} commit(s)"],"")
 return Check("git_history","Git history",FAIL,"Git metadata exists but no commit is available.",[o],"Create an initial commit.")
def dependency_lockfile(root):
 m,l=_manifest(root)
 if m is None:return Check("dependency_lockfile","Dependency lockfile",UNSUPPORTED,"No recognized package manifest was found.",[],"Add a supported manifest and its ecosystem lockfile.")
 if l:return Check("dependency_lockfile","Dependency lockfile",PASS,"A lockfile matches a detected package manifest.",l,"")
 return Check("dependency_lockfile","Dependency lockfile",FAIL,"A supported manifest has no matching lockfile.",m,"Generate and commit the ecosystem-appropriate lockfile.")
def pinned_runtime(root):
 c=[".python-version",".nvmrc",".node-version","rust-toolchain.toml",".tool-versions","go.mod"]
 f=[x for x in c if (root/x).is_file() and (root/x).read_text(errors="replace").strip()]
 return Check("pinned_runtime","Pinned runtime",PASS,"An explicit runtime configuration was found.",f,"") if f else Check("pinned_runtime","Pinned runtime",FAIL,"No explicit runtime version was detected.",[],"Commit a runtime pin such as .python-version.")
def dockerfile(root):
 p=root/"Dockerfile"
 return Check("dockerfile","Dockerfile",PASS,"A non-empty Dockerfile is present.",["Dockerfile"],"") if p.is_file() and p.stat().st_size else Check("dockerfile","Dockerfile",FAIL,"No usable Dockerfile was found.",[],"Add a minimal reproducible Dockerfile.")
def test_command(root):
 ev=[]; p=root/"README.md"; t=p.read_text(errors="replace") if p.exists() else ""
 if re.search(r"(?im)^\s*(?:\$\s*)?(?:python(?:3)?\s+-m\s+unittest|pytest|npm\s+test|cargo\s+test|go\s+test)",t):ev.append("README.md")
 if (root/"tests").is_dir() or (root/"test").is_dir():ev.append("tests/ directory")
 return Check("test_command","Test command",PASS,"A test command or test suite is identifiable.",ev,"") if ev else Check("test_command","Test command",WARN,"No documented or clearly identifiable test command was found.",[],"Document the exact test command in README.md.")
def readme(root):
 p=root/"README.md"
 if not p.is_file():return Check("readme","README",FAIL,"README.md is missing.",[],"Add setup, run, and test instructions.")
 t=p.read_text(errors="replace"); sections=[s for s in ("setup","install","run","test") if re.search(rf"(?im)^#+\s*.*{s}",t)]
 return Check("readme","README",PASS,"README contains meaningful setup, run, and test sections.",sections,"") if len(t.strip())>=120 and {"setup","run","test"}.issubset(sections) else Check("readme","README",FAIL,"README is missing meaningful setup, run, or test instructions.",sections,"Document setup, run, and test workflows.")
def env_example(root):
 p=root/".env.example"
 if not p.exists():return Check("env_example",".env.example",WARN,"No environment example was found; this is only a failure when configuration is required.",[],"Add .env.example with placeholders if configuration is needed.")
 hits=[]
 for i,line in enumerate(p.read_text(errors="replace").splitlines(),1):
  if re.search(r"(?i)(sk-[A-Za-z0-9]{12,}|AKIA[0-9A-Z]{12,}|-----BEGIN|password\s*=\s*[^$<{][^\s]+|secret\s*=\s*[^$<{][^\s]+)",line):hits.append(f".env.example:{i}")
 return Check("env_example",".env.example",FAIL,"The example file contains a secret-like value; values are not printed.",hits,"Replace values with placeholders and rotate exposed credentials.") if hits else Check("env_example",".env.example",PASS,"An example environment file contains no obvious secret-like values.",[".env.example"],"")
def absolute_paths(root):
 hits=[]; pat=re.compile(r"(?:/home/[^\s'\"`]+|/Users/[^\s'\"`]+|[A-Za-z]:\\Users\\[^\s'\"`]+)")
 for p in _files(root):
  try:lines=p.read_text(errors="replace").splitlines()
  except OSError:continue
  for i,line in enumerate(lines,1):
   normalized=line.replace("\\\\", "\\")
   if pat.search(normalized) and "http://" not in line and "https://" not in line and "re.compile" not in line and "pat=re" not in line:hits.append(f"{p.relative_to(root)}:{i}")
 return Check("absolute_paths","Absolute local paths",WARN,"Possible machine-specific absolute paths were found; heuristics can over-report.",hits[:20],"Use relative paths or environment-based configuration.") if hits else Check("absolute_paths","Absolute local paths",PASS,"No likely machine-specific absolute paths were found.",[],"")
def audit(root):return [git_history(root),dependency_lockfile(root),pinned_runtime(root),dockerfile(root),test_command(root),readme(root),env_example(root),absolute_paths(root)]
