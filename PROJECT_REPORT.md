# Clone to Confidence — Project Report

## 1. Overview

Clone to Confidence is an offline-first Python CLI that audits repositories for clean-machine rebuildability. It reports deterministic evidence for Git history, dependency lockfiles, runtime pins, Docker packaging, test discoverability, README quality, environment examples, and machine-specific absolute paths.

The project is designed around a simple rule: if a repository says it works, it should provide evidence that another developer can rebuild and verify it.

## 2. Project locations

- Original project location: `C:\Users\ashutosh\omnirush.ai`
- Final project location: `C:\Users\ashutosh\omnirush.ai`
- Linux/container mapping used for verification: `/c/Users/ashutosh/omnirush.ai`
- Dedicated `C:\Clone-to-Confidence` folder: **not created** because the existing workspace was already a dedicated, organized project repository. No duplicate copy was necessary.

The original files were preserved in place. No destructive move or deletion was performed.

## 3. Architecture and structure

```text
clone-to-confidence/
├── pyproject.toml
├── uv.lock
├── .python-version
├── Dockerfile
├── .dockerignore
├── .gitignore
├── .env.example
├── README.md
├── LICENSE
├── PROJECT_REPORT.md
├── src/clone_to_confidence/
│   ├── __init__.py
│   ├── auditor/checks implementation: checks.py
│   ├── cli.py
│   ├── fixer.py
│   ├── report.py
│   └── verifier.py
├── tests/
│   ├── test_auditor.py
│   └── test_fixer.py
└── examples/broken-repo/
    ├── README.md
    ├── app.py
    └── pyproject.toml

Main commands:

clone-to-confidence audit PATH

clone-to-confidence audit PATH --format json

clone-to-confidence verify PATH

clone-to-confidence fix PATH --dry-run

clone-to-confidence fix PATH --apply

4. Technologies and dependencies
Python 3.12 (.python-version and requires-python = ">=3.12,<3.13")

Python standard library for the runtime implementation

argparse for CLI parsing

unittest for tests

uv for environment and lockfile management

Hatchling as the PEP 517 build backend

Dockerfile for isolated verification

No paid APIs, hosted services, databases, or runtime API keys

The application dependency list is empty. uv.lock pins the build environment resolution.

5. Buildathon track recommendation
Recommended track: Developer Tools & Open Source. The project is a local developer CLI that audits reproducibility, provides evidence-backed remediation, and verifies repositories with Docker when available. It does not depend on a hosted service, paid API, or generic AI coding workflow.

6. Tests and checks executed
All commands ran from /c/Users/ashutosh/omnirush.ai.

Check	Result
uv lock --check	PASS
uv run python -m unittest discover -s tests -v	PASS — 9 tests
uv build --wheel --sdist --out-dir /tmp/clone-to-confidence-dist-final	PASS
CLI text audit	PASS — 8 PASS, 0 FAIL, 0 WARN
CLI JSON audit	PASS — valid JSON
CLI verification	PASS for static checks and tests
Test suite with network namespace disabled via unshare -n	PASS — 9 tests
Dry-run fixer coverage	PASS
git diff --check	PASS
Dockerfile testability	PASS — Dockerfile now includes tests/ for container test execution
Docker build attempt	BLOCKED — docker executable is unavailable (docker: command not found)
Tests inside Docker	NOT RUN — blocked by unavailable Docker runtime
The verifier reported Docker build: UNAVAILABLE; Docker was not claimed as passing.

7. Issues discovered and fixes applied
Removed tracked .opencode/omnirush.json, which contained a developer-specific absolute Windows workspace path.

Added .opencode/ to .gitignore so generated workspace metadata is not published.

Hardened .dockerignore against .env, .env.*, and generated .opencode content entering Docker build contexts.

Fixed the dependency audit so a plain requirements.txt is not incorrectly treated as its own lockfile.

Improved absolute-path detection for JSON-escaped Windows paths.

Added regression coverage for escaped Windows paths.

Changed the synthetic secret test value to avoid committing a realistic-looking API token.

Updated `verify` to recognize the documented `uv run` test-command prefix, execute it through an argument list without `shell=True`, and print bounded, secret-redacted failure evidence. Added regression tests for command detection and failure evidence.

8. Git status and commits
Verified current state:

text
Copy
Download
Branch: main
Working tree: clean
Remote: origin (https://github.com/Ashutoshranjan195/clone-to-confidence.git)
Recent commits:

text
Copy
Download
9d3d010 chore: untrack local OmniRush config
7462b7e fix: make Docker image testable
5b51e84 docs: refresh submission status
9a9558a docs: add buildathon submission details
643deca docs: record final release commit
9. GitHub publishing status
Successfully Published.

Repository URL: https://github.com/Ashutoshranjan195/clone-to-confidence

Status: Public

Branch: main

Latest verified commit: 9d3d010

The code has been successfully pushed and verified on GitHub. The default branch is main. The local opencode.jsonc was successfully untracked and ignored to prevent exposing local machine paths.

10. Security checks and remaining risks
Completed checks:

No tracked .env, private key, certificate, or credential-named files.

No obvious API keys, private keys, GitHub tokens, or passwords found in tracked project content.

.env.example contains placeholders only.

Machine-specific workspace metadata was removed from tracked files.

.env and .env.* are excluded from Docker contexts, while .env.example remains allowed.

Audit does not execute repository code.

Remaining risks:

Secret scanning is heuristic and is not a substitute for a dedicated scanner such as Gitleaks.

Docker verification is not a complete security sandbox. Do not mount the host filesystem or Docker socket for untrusted repositories.

The Docker image was not built here because Docker is unavailable. The Dockerfile now copies the test suite so the documented network-disabled container test can run when Docker is available.

The source contains the regex used to detect Windows absolute paths; this is detector logic, not a machine-specific path.

11. Limitations and recommended improvements
Add CI for Python 3.12, unit tests, uv lock --check, package builds, and security scanning.

Run and record a real Docker build and docker run --rm --network none clone-to-confidence python -m unittest discover -s tests -v on a host with Docker installed.

Add an explicit user-supplied verification policy for more test command types.

Add a release tag and GitHub repository metadata after publication.

Consider adding a SECURITY.md, contribution guide, and changelog for a larger public community.

12. Buildathon submission preparation
Deadline: 20 October 2026 at 11:59 PM IST

Recommended track: Developer Tools & Open Source

Public GitHub URL: https://github.com/Ashutoshranjan195/clone-to-confidence

Concise description: “Clone to Confidence audits repositories for clean-machine rebuildability, explains failures with evidence, proposes safe fixes, and verifies Docker builds without executing code during audit.”

Relevant OmniRush build session: ses_eab191c06ffeJzn2r3dp5pZBmT (Clone to Confidence CLI Implementation)

Demo video: Not available (optional)

Live demo: Not available (local CLI tool)

Submission ID: Pending OmniRush dashboard submission.