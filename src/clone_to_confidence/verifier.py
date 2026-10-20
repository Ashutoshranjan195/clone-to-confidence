from __future__ import annotations

import re
import shlex
import shutil
import subprocess
from pathlib import Path

from .checks import audit

_SAFE_TESTS = [
    re.compile(r"^python(?:3)? -m unittest(?: discover(?: -s [A-Za-z0-9_./-]+)?(?: -v)?)?$"),
    re.compile(r"^pytest(?: -q)?$"),
    re.compile(r"^npm test$"),
    re.compile(r"^cargo test$"),
    re.compile(r"^go test(?: ./\.\.)?$"),
]
_SECRET_OUTPUT = [
    (re.compile(r"(?i)\b(?:sk|ghp|github_pat)-[A-Za-z0-9_:-]{12,}"), "[REDACTED_SECRET]"),
    (re.compile(r"(?i)\b(?:AKIA[0-9A-Z]{12,})\b"), "[REDACTED_SECRET]"),
    (re.compile(r"(?i)(\b(?:password|secret|token|api[_-]?key)\s*[=:]\s*)[^\s]+"), r"\1[REDACTED_SECRET]"),
]

def _redact_output(output: str) -> str:
    for pattern, replacement in _SECRET_OUTPUT:
        output = pattern.sub(replacement, output)
    return output

def _documented_test(root: Path):
    readme = root / "README.md"
    if not readme.exists():
        return None
    for line in readme.read_text(errors="replace").splitlines():
        command = line.strip().removeprefix("$").strip()
        try:
            tokens = shlex.split(command)
        except ValueError:
            continue
        prefix = []
        if tokens[:2] == ["uv", "run"]:
            prefix = tokens[:2]
            tokens = tokens[2:]
        normalized = " ".join(tokens)
        if any(pattern.fullmatch(normalized) for pattern in _SAFE_TESTS):
            return prefix + tokens
    return None

def _result_evidence(process: subprocess.CompletedProcess[str]) -> str:
    output = (process.stdout or "") + (process.stderr or "")
    return _redact_output(output[-2000:])

def verify(root: Path):
    result = {"static": audit(root), "docker": {"status": "UNAVAILABLE", "evidence": []}, "tests": {"status": "SKIPPED", "evidence": []}}
    docker = shutil.which("docker")
    if docker and (root / "Dockerfile").exists():
        try:
            process = subprocess.run([docker, "build", "-t", "clone-to-confidence-verify", str(root)], capture_output=True, text=True, timeout=300)
            result["docker"] = {"status": "PASS" if process.returncode == 0 else "FAIL", "evidence": _result_evidence(process)}
        except subprocess.TimeoutExpired:
            result["docker"] = {"status": "FAIL", "evidence": "Docker build timed out"}
    elif not docker:
        result["docker"] = {"status": "UNAVAILABLE", "evidence": "Docker executable not found"}

    test_args = _documented_test(root)
    if test_args:
        executable = shutil.which(test_args[0])
        if executable:
            try:
                process = subprocess.run(test_args, cwd=root, capture_output=True, text=True, timeout=120)
                result["tests"] = {"status": "PASS" if process.returncode == 0 else "FAIL", "evidence": _result_evidence(process)}
            except subprocess.TimeoutExpired:
                result["tests"] = {"status": "FAIL", "evidence": "Documented test command timed out"}
        else:
            result["tests"] = {"status": "UNAVAILABLE", "evidence": f"{test_args[0]} executable not found"}
    return result
