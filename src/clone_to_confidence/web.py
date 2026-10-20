"""Dependency-free local dashboard and safe hosted demo.

Local mode accepts an explicit existing repository directory and keeps the
verification/fixer workflows available. Hosted demo mode exposes only the
bundled fixture and is read-only, so a public instance never accepts a client
filesystem path or executes a client-selected command.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from .checks import audit
from .fixer import apply as apply_fixes
from .report import summary
from .verifier import verify


PACKAGE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = PACKAGE_DIR / "web_assets"
_SOURCE_DEMO_PATH = PACKAGE_DIR.parent.parent / "examples" / "broken-repo"
DEFAULT_DEMO_PATH = Path(os.environ.get("CLONE_TO_CONFIDENCE_DEMO_PATH", str(_SOURCE_DEMO_PATH))).expanduser()
MAX_BODY_BYTES = 64 * 1024
DEFAULT_PORT = 8765
SCORE_FORMULA = "PASS=100, WARN=50, FAIL=0, UNSUPPORTED/SKIPPED=25"


class DashboardError(ValueError):
    """An expected, user-actionable dashboard request error."""

    status = HTTPStatus.BAD_REQUEST


class ForbiddenError(DashboardError):
    status = HTTPStatus.FORBIDDEN


class PayloadTooLargeError(DashboardError):
    status = HTTPStatus.REQUEST_ENTITY_TOO_LARGE


class UnsupportedMediaTypeError(DashboardError):
    status = HTTPStatus.UNSUPPORTED_MEDIA_TYPE


def repository_path(value: str | os.PathLike[str]) -> Path:
    """Resolve an explicitly supplied existing directory.

    This function intentionally does not accept glob patterns, files, or a
    browser-style directory listing. The audit code remains responsible for
    the bounded repository scan.
    """

    if not isinstance(value, (str, os.PathLike)) or not str(value).strip():
        raise DashboardError("Enter a repository directory path.")
    try:
        path = Path(value).expanduser().resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        raise DashboardError("Repository path does not exist or cannot be resolved.") from None
    if not path.is_dir():
        raise DashboardError("Repository path must be an existing directory.")
    return path


def dashboard_summary(checks: list[Any]) -> dict[str, int]:
    raw = summary(checks)
    return {
        "PASS": raw["PASS"],
        "FAIL": raw["FAIL"],
        "WARN": raw["WARN"],
        "UNAVAILABLE": raw["UNSUPPORTED"] + raw["SKIPPED"],
    }


def confidence_score(checks: list[Any]) -> int:
    weights = {"PASS": 1.0, "WARN": 0.5, "FAIL": 0.0, "UNSUPPORTED": 0.25, "SKIPPED": 0.25}
    if not checks:
        return 0
    return round(sum(weights.get(check.status, 0.0) for check in checks) / len(checks) * 100)


def check_payload(root: Path, *, public_demo: bool = False) -> dict[str, Any]:
    checks = audit(root)
    raw_summary = summary(checks)
    return {
        "repository": "bundled-demo" if public_demo else str(root),
        "repositoryName": "Bundled demo repository" if public_demo else root.name or str(root),
        "demo": public_demo,
        "checks": [check.to_dict() for check in checks],
        "summary": raw_summary,
        "displaySummary": dashboard_summary(checks),
        "score": confidence_score(checks),
        "scoreFormula": SCORE_FORMULA,
    }


def fixes_payload(root: Path, *, dry_run: bool = True) -> dict[str, Any]:
    changes = apply_fixes(root, dry_run=dry_run)
    return {
        "repository": str(root),
        "dryRun": dry_run,
        "changes": [
            {"action": action, "path": relative, "content": content}
            for action, relative, content in changes
        ],
    }


def verify_payload(root: Path) -> dict[str, Any]:
    result = verify(root)
    return {
        "repository": str(root),
        "checks": [check.to_dict() for check in result["static"]],
        "summary": summary(result["static"]),
        "docker": result["docker"],
        "tests": result["tests"],
    }


class DashboardHandler(BaseHTTPRequestHandler):
    """HTTP API and static asset handler used by the local dashboard."""

    server_version = "CloneToConfidence/0.1"

    def _send(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
        )
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: HTTPStatus, value: dict[str, Any]) -> None:
        self._send(status, json.dumps(value, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def _error(self, status: HTTPStatus, message: str) -> None:
        self._json(status, {"error": message})

    def _body(self) -> dict[str, Any]:
        if self.headers.get("Transfer-Encoding"):
            raise DashboardError("Chunked request bodies are not supported.")
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise DashboardError("Request body length is invalid.") from None
        if length < 0:
            raise DashboardError("Request body length is invalid.")
        if length > MAX_BODY_BYTES:
            # Consume only the bounded prefix before closing this request. This
            # lets ordinary HTTP clients receive the 413 response cleanly while
            # avoiding an unbounded read from an untrusted caller.
            self.rfile.read(MAX_BODY_BYTES + 1)
            self.close_connection = True
            raise PayloadTooLargeError("Request body is too large.")
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            self.rfile.read(length)
            raise UnsupportedMediaTypeError("Content-Type must be application/json.")
        try:
            data = json.loads(self.rfile.read(length) or b"{}")
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise DashboardError("Request body must be valid JSON.") from None
        if not isinstance(data, dict):
            raise DashboardError("Request body must be a JSON object.")
        return data

    @property
    def public_demo(self) -> bool:
        return bool(getattr(self.server, "public_demo", False))

    def _method_not_allowed(self) -> None:
        self.send_response(HTTPStatus.METHOD_NOT_ALLOWED)
        self.send_header("Allow", "GET, POST")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        body = json.dumps({"error": "Method not allowed."}).encode("utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        parsed = urlparse(self.path)
        if parsed.path == "/api/demo":
            try:
                root = repository_path(DEFAULT_DEMO_PATH)
                self._json(HTTPStatus.OK, {"mode": "public-demo" if self.public_demo else "local", **check_payload(root, public_demo=self.public_demo), "demo": True})
            except DashboardError as exc:
                self._error(HTTPStatus.SERVICE_UNAVAILABLE, "The bundled demo fixture is unavailable.")
            except (OSError, UnicodeError):
                self._error(HTTPStatus.SERVICE_UNAVAILABLE, "The bundled demo fixture could not be read.")
            except Exception:
                self._error(HTTPStatus.INTERNAL_SERVER_ERROR, "Demo audit could not be completed.")
            return
        if parsed.path == "/api/health":
            self._json(
                HTTPStatus.OK,
                {
                    "status": "ok",
                    "mode": "public-demo" if self.public_demo else "local",
                    "demoAvailable": DEFAULT_DEMO_PATH.is_dir(),
                    "readOnly": self.public_demo,
                },
            )
            return
        self._serve_asset(parsed.path)

    def _serve_asset(self, request_path: str) -> None:
        relative = "index.html" if request_path in ("", "/") else unquote(request_path.removeprefix("/"))
        if "\x00" in relative:
            self._error(HTTPStatus.NOT_FOUND, "Asset not found.")
            return
        # Resolve and verify containment so /../ cannot escape the asset folder.
        candidate = (ASSETS_DIR / relative).resolve()
        try:
            candidate.relative_to(ASSETS_DIR.resolve())
        except ValueError:
            self._error(HTTPStatus.NOT_FOUND, "Asset not found.")
            return
        if not candidate.is_file():
            self._error(HTTPStatus.NOT_FOUND, "Asset not found.")
            return
        try:
            body = candidate.read_bytes()
        except OSError:
            self._error(HTTPStatus.NOT_FOUND, "Asset could not be read.")
            return
        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        self._send(HTTPStatus.OK, body, content_type)

    def do_POST(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        path = urlparse(self.path).path
        known_routes = {"/api/audit", "/api/verify", "/api/fixes"}
        if path not in known_routes:
            self._error(HTTPStatus.NOT_FOUND, "API route not found.")
            return
        if self.public_demo:
            self._error(ForbiddenError.status, "Hosted demo mode is read-only and exposes only the bundled demo.")
            return
        try:
            data = self._body()
            if path == "/api/audit":
                root = repository_path(data.get("path", ""))
                self._json(HTTPStatus.OK, check_payload(root))
            elif path == "/api/verify":
                root = repository_path(data.get("path", ""))
                self._json(HTTPStatus.OK, verify_payload(root))
            elif path == "/api/fixes":
                root = repository_path(data.get("path", ""))
                dry_run = data.get("dryRun", True)
                if not isinstance(dry_run, bool):
                    raise DashboardError("dryRun must be a boolean.")
                if not dry_run and data.get("confirm") is not True:
                    raise DashboardError("Applying fixes requires explicit confirmation.")
                self._json(HTTPStatus.OK, fixes_payload(root, dry_run=dry_run))
        except DashboardError as exc:
            self._error(exc.status, str(exc))
        except (OSError, UnicodeError):
            self._error(HTTPStatus.INTERNAL_SERVER_ERROR, "Repository operation could not be completed.")
        except Exception:
            self._error(HTTPStatus.INTERNAL_SERVER_ERROR, "Request could not be completed.")

    def do_PUT(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        self._method_not_allowed()

    def do_PATCH(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        self._method_not_allowed()

    def do_DELETE(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        self._method_not_allowed()

    def do_OPTIONS(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        self._method_not_allowed()

    def do_HEAD(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        self._method_not_allowed()

    def log_message(self, format: str, *args: Any) -> None:
        # Keep dashboard output quiet unless callers opt into their own logging.
        return


class DashboardServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def configured_port(port: int | None = None) -> int:
    if port is not None:
        return port
    raw = os.environ.get("PORT", str(DEFAULT_PORT)).strip()
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_PORT
    return value if 0 <= value <= 65535 else DEFAULT_PORT


def create_server(host: str = "127.0.0.1", port: int | None = None, *, public_demo: bool = False) -> DashboardServer:
    server = DashboardServer((host, configured_port(port)), DashboardHandler)
    server.public_demo = public_demo
    return server


def serve(host: str = "127.0.0.1", port: int | None = None, *, public_demo: bool = False) -> None:
    server = create_server(host, port, public_demo=public_demo)
    mode = "hosted read-only demo" if public_demo else "local dashboard"
    print(f"Clone to Confidence {mode}: http://{host}:{server.server_port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="clone-to-confidence web", description="Launch the local confidence dashboard.")
    parser.add_argument("--host", default="127.0.0.1", help="bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=None, help="bind port (default: PORT or 8765)")
    parser.add_argument("--public-demo", action="store_true", help="serve only the bundled read-only demo")
    args = parser.parse_args(argv)
    if args.port is not None and not 0 <= args.port <= 65535:
        parser.error("port must be between 0 and 65535")
    serve(args.host, args.port, public_demo=args.public_demo)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
