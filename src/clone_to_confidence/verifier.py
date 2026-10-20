from __future__ import annotations
import shutil,subprocess
from pathlib import Path
from .checks import audit
def verify(root:Path):
 r={"static":audit(root),"docker":{"status":"UNAVAILABLE","evidence":[]},"tests":{"status":"SKIPPED","evidence":[]}}; docker=shutil.which("docker")
 if docker and (root/"Dockerfile").exists():
  try:
   p=subprocess.run([docker,"build","-t","clone-to-confidence-verify",str(root)],capture_output=True,text=True,timeout=300); r["docker"]={"status":"PASS" if p.returncode==0 else "FAIL","evidence":(p.stdout+p.stderr)[-2000:]}
  except subprocess.TimeoutExpired:r["docker"]={"status":"FAIL","evidence":"Docker build timed out"}
 elif not docker:r["docker"]={"status":"UNAVAILABLE","evidence":"Docker executable not found"}
 return r
