from __future__ import annotations
import re, shutil, subprocess
from pathlib import Path
from .checks import audit

_SAFE_TESTS = [
    (re.compile(r"^python(?:3)? -m unittest(?: discover(?: -s [A-Za-z0-9_./-]+)?(?: -v)?)?$"), lambda x: x.split()),
    (re.compile(r"^pytest(?: -q)?$"), lambda x: x.split()),
    (re.compile(r"^npm test$"), lambda x: x.split()),
    (re.compile(r"^cargo test$"), lambda x: x.split()),
    (re.compile(r"^go test(?: ./\.\.\.)?$"), lambda x: x.split()),
]

def _documented_test(root: Path):
    readme = root / "README.md"
    if not readme.exists(): return None
    for line in readme.read_text(errors="replace").splitlines():
        command = line.strip().removeprefix("$").strip()
        for pattern, split in _SAFE_TESTS:
            if pattern.fullmatch(command): return split(command)
    return None

def verify(root: Path):
    result = {"static": audit(root), "docker": {"status": "UNAVAILABLE", "evidence": []}, "tests": {"status": "SKIPPED", "evidence": []}}
    docker = shutil.which("docker")
    if docker and (root / "Dockerfile").exists():
        try:
            p = subprocess.run([docker, "build", "-t", "clone-to-confidence-verify", str(root)], capture_output=True, text=True, timeout=300)
            result["docker"] = {"status": "PASS" if p.returncode == 0 else "FAIL", "evidence": (p.stdout + p.stderr)[-2000:]}
        except subprocess.TimeoutExpired:
            result["docker"] = {"status": "FAIL", "evidence": "Docker build timed out"}
    elif not docker:
        result["docker"] = {"status": "UNAVAILABLE", "evidence": "Docker executable not found"}
    test_args = _documented_test(root)
    if test_args:
        executable = shutil.which(test_args[0])
        if executable:
            try:
                p = subprocess.run(test_args, cwd=root, capture_output=True, text=True, timeout=120)
                result["tests"] = {"status": "PASS" if p.returncode == 0 else "FAIL", "evidence": (p.stdout + p.stderr)[-2000:]}
            except subprocess.TimeoutExpired:
                result["tests"] = {"status": "FAIL", "evidence": "Documented test command timed out"}
        else:
            result["tests"] = {"status": "UNAVAILABLE", "evidence": f"{test_args[0]} executable not found"}
    return result
