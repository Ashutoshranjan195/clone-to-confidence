# Clone to Confidence

**If it says it works, prove it works.**

Clone to Confidence is a small offline-first CLI that audits a repository for clean-machine rebuildability. It reports evidence instead of promising compatibility: dependency locks, runtime pins, Docker packaging, tests, documentation, environment placeholders, and machine-specific paths.

## Features and limitations

- Eight deterministic static checks; audit never executes repository code.
- JSON output for CI and readable terminal output for humans.
- Safe fixes are opt-in, create-only, and never copy secrets.
- Explicit verification can build the repository's Dockerfile. Docker is not a complete security sandbox.
- Python projects are the primary supported ecosystem; common Node, Rust, and Go manifests are recognized for lockfile checks.
- Heuristics can miss secrets and may flag legitimate absolute paths.

## Prerequisites

Python 3.12, Git for history checks, and optionally Docker Engine for verification.

## Install

```bash
uv sync
# or: python -m venv .venv && . .venv/bin/activate && pip install -e .
```

## Setup

Install the CLI with the commands below.

## Run

For a packaged project, run the CLI with `clone-to-confidence audit PATH`.

## Audit

```bash
clone-to-confidence audit .
clone-to-confidence audit . --format json > report.json
```

Audit is read-only and returns exit code 1 when a required check fails. Statuses mean `PASS` evidence met the rule, `FAIL` a required rule was not met, `WARN` a heuristic or conditional concern exists, `UNSUPPORTED` no recognized ecosystem/tool exists, and `SKIPPED` was intentionally not run.

Example: a deliberately broken fixture can be audited with `clone-to-confidence audit examples/broken-repo`.

### JSON report

```json
{"id":"pinned_runtime","name":"Pinned runtime","status":"FAIL","evidence":[],"remediation":"Commit a runtime pin such as .python-version."}
```

The actual report includes all eight checks and a summary.

## Safe fixes

```bash
clone-to-confidence fix examples/broken-repo --dry-run
clone-to-confidence fix examples/broken-repo --apply
```

Only missing `.env.example` and `.python-version` files are proposed for Python projects. Existing files are never overwritten. Review the dry run first.

## Verify

```bash
clone-to-confidence verify .
```

When Docker is available, build and run the included test suite without network access:

```bash
docker build --pull --progress=plain -t clone-to-confidence .
docker run --rm --network none clone-to-confidence \
  python -m unittest discover -s tests -v
```

Verification is explicit. It runs static checks and attempts a real `docker build` when Docker is installed. It reports Docker as `UNAVAILABLE` when Docker cannot be found. The verifier executes only a small allowlist of documented test commands (`python -m unittest`, `pytest`, `npm test`, `cargo test`, or `go test`) using argument lists; unknown README commands remain `SKIPPED` rather than being guessed. Do not mount the host filesystem or Docker socket into untrusted builds: Docker verification is not a complete security sandbox.

## Test

```bash
python -m unittest discover -s tests -v
```

## Security considerations

Repositories are untrusted input. Audit does not execute code, follows no symlinks, excludes dependency and VCS directories, bounds subprocesses, and does not print secret values. Docker builds can still exploit kernel, daemon, network, or build-context risks; use an isolated runner and review Dockerfiles.

## Reproducibility checklist

This repository includes a Git commit, `uv.lock`, `.python-version`, a Dockerfile, a unittest command, setup/run/test README instructions, placeholder-only `.env.example`, and no embedded machine paths. Docker may be unavailable on the host; that is reported rather than claimed as passing.

## Future work

Add an explicit, user-supplied test command policy, deeper ecosystem manifests, bounded Docker test execution, and CI integration without changing the deterministic core.
