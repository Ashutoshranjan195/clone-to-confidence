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

## What problem this solves

“Works on my machine” is not evidence that another developer can clone, install,
test, and run a repository. Clone to Confidence turns that uncertainty into a
small, reviewable readout: eight deterministic checks, the evidence that caused
each result, and a next step when the repository is not yet reproducible.

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

Verification is explicit. It runs static checks and attempts a real `docker build` when Docker is installed. It reports Docker as `UNAVAILABLE` when Docker cannot be found. The verifier executes only a small allowlist of documented test commands (`python -m unittest`, `uv run python -m unittest`, `pytest`, `uv run pytest`, `npm test`, `cargo test`, or `go test`) using argument lists; unknown README commands remain `SKIPPED` rather than being guessed. Do not mount the host filesystem or Docker socket into untrusted builds: Docker verification is not a complete security sandbox.

## Local web dashboard

Launch the dependency-free dashboard on the loopback interface:

```bash
clone-to-confidence web
# open http://127.0.0.1:8765/
```

Use `--port 0` to let the operating system choose an available port, or pass a
different explicit port such as `clone-to-confidence web --port 9000`. The
dashboard starts in an empty state; **Load broken-repo fixture** audits the
included `examples/broken-repo` demo immediately. For another repository, paste
an existing directory path and choose **Run audit**. Audit and dry-run fixes are
read-only. Verification is separate and explicit, and **Apply safe fixes** first
requires a confirmation click. **Export JSON** downloads the latest audit
readout without sending repository data anywhere.

### Windows quick start

From PowerShell in the repository directory:

```powershell
Set-Location (Join-Path $HOME "omnirush.ai")
$env:UV_PROJECT_ENVIRONMENT = ".venv-windows"
uv sync
uv run clone-to-confidence web
```

Open `http://127.0.0.1:8765/`. The `UV_PROJECT_ENVIRONMENT` override is useful
when an older environment contains a Unix-style `lib64` link that Windows cannot
remove. The local dashboard can audit an explicitly supplied directory, verify
it, preview safe create-only fixes, and apply them only after confirmation.

### Hosted demo mode

The hosted mode is intentionally narrower than local mode:

```bash
PORT=8080 uv run clone-to-confidence web --host 0.0.0.0 --public-demo
```

It audits only the bundled `examples/broken-repo` fixture, labels the result as a
demonstration, and keeps the server read-only. It does not accept arbitrary
client filesystem paths, run verification, or apply fixes. This makes a public
demo useful without pretending that a cloud server can see a visitor's local
disk. See [HOSTING.md](HOSTING.md) for a container and Render deployment guide.

### Example audit output

```text
PASS        Git history
FAIL        Dependency lockfile
FAIL        Pinned runtime
FAIL        Dockerfile
WARN        Test command
FAIL        README
WARN        .env.example
PASS        Absolute local paths

Result: 2 PASS | 4 FAIL | 2 WARN
```

The exact result depends on the repository being audited. The dashboard's score
is transparent: `PASS=100`, `WARN=50`, `FAIL=0`, and `UNSUPPORTED/SKIPPED=25`.
It is a triage signal, not a claim that the application is correct or secure.

## Test

```bash
uv run python -m unittest discover -s tests -v
```

## Security considerations

Repositories are untrusted input. Audit does not execute code, follows no symlinks, excludes dependency and VCS directories, bounds subprocesses, and does not print secret values. Docker builds can still exploit kernel, daemon, network, or build-context risks; use an isolated runner and review Dockerfiles.

Hosted mode adds HTTP method and JSON body validation, a bounded request size,
static asset containment checks, security response headers, generic error
messages, and read-only routing. It never exposes the Docker socket and never
accepts uploaded code or arbitrary Git URLs. Local verification remains an
explicit developer action; it should not be exposed directly to the public
internet without an isolated execution design.

## Reproducibility checklist

This repository includes a Git commit, `uv.lock`, `.python-version`, a Dockerfile, a unittest command, setup/run/test README instructions, placeholder-only `.env.example`, and no embedded machine paths. Docker may be unavailable on the host; that is reported rather than claimed as passing.

## Future work

Add GitHub URL and ZIP auditing through a temporary workspace with archive
traversal checks, strict size/time limits, and isolated sandbox execution; add an
explicit user-supplied test command policy, deeper ecosystem manifests, bounded
Docker test execution, and CI integration without changing the deterministic
core.

## Hackathon submission brief

**Problem:** Developers and judges often have to trust a README claim that a
repository is reproducible without seeing the evidence.

**Solution:** Clone to Confidence is an offline-first Python CLI and dashboard
that checks the concrete signals behind a clean-machine rebuild and explains the
gaps instead of hiding them behind a binary “works” badge.

**Differentiation:** It is deterministic, evidence-first, and honest about its
boundaries. Audit never executes repository code; verification is separate and
explicit; fixes are create-only and confirmation-gated; the hosted demo is
read-only rather than accepting unsafe arbitrary code.

**Key features:** Eight audit checks, expandable evidence/remediation, a
transparent confidence score, Docker/test verification statuses, JSON export,
and safe `.env.example`/runtime-pin proposals.

**Technology:** Python 3.12 standard library, `ThreadingHTTPServer`, static
HTML/CSS/JavaScript, `unittest`, and an optional Docker verification path.

**Demo walkthrough:** Open the hosted or local dashboard, run the bundled demo,
inspect the eight cards, expand evidence, export the JSON report, then show the
local-only verify and safe-fix flows.

**Current limitations:** The hosted demo cannot see a visitor's local files and
therefore audits only its bundled fixture. Docker verification is not a complete
security sandbox. GitHub URL/ZIP ingestion, persistent reports, authentication,
and public arbitrary-repository execution are intentionally future work.
