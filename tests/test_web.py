import http.client
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path

from clone_to_confidence.web import MAX_BODY_BYTES, configured_port, create_server

ASSETS = Path(__file__).parents[1] / "src" / "clone_to_confidence" / "web_assets"


class DashboardRouteTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="ctc-web-"))
        (self.root / "pyproject.toml").write_text('[project]\nname = "web-fixture"\n')
        self.server = create_server("127.0.0.1", 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.client = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)

    def tearDown(self):
        self.client.close()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def request(self, method, path, payload=None):
        body = json.dumps(payload).encode() if payload is not None else None
        headers = {"Content-Type": "application/json"} if body is not None else {}
        self.client.request(method, path, body=body, headers=headers)
        response = self.client.getresponse()
        raw = response.read()
        content_type = response.headers.get_content_type()
        return response.status, content_type, json.loads(raw) if content_type == "application/json" and raw else raw

    def test_serves_dashboard_and_health(self):
        status, content_type, body = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertEqual(content_type, "text/html")
        self.assertIn(b"Clone to Confidence", body if isinstance(body, bytes) else b"")

        status, _, body = self.request("GET", "/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")

        index = (ASSETS / "index.html").read_text(encoding="utf-8")
        styles = (ASSETS / "styles.css").read_text(encoding="utf-8")
        self.assertIn('id="verify-button" type="button" disabled', index)
        self.assertIn("Run an audit first to unlock explicit verification.", index)
        self.assertIn(".topbar nav{display:flex", styles)

    def test_audit_requires_existing_explicit_directory(self):
        status, _, body = self.request("POST", "/api/audit", {"path": str(self.root)})
        self.assertEqual(status, 200)
        self.assertEqual(len(body["checks"]), 8)
        self.assertEqual(body["repository"], str(self.root.resolve()))

        status, _, body = self.request("POST", "/api/audit", {"path": str(self.root / "missing")})
        self.assertEqual(status, 400)
        self.assertIn("does not exist", body["error"])

    def test_fixes_need_confirmation_before_writing(self):
        payload = {"path": str(self.root), "dryRun": True}
        status, _, body = self.request("POST", "/api/fixes", payload)
        self.assertEqual(status, 200)
        self.assertTrue(body["dryRun"])
        self.assertFalse((self.root / ".env.example").exists())

        status, _, body = self.request("POST", "/api/fixes", {"path": str(self.root), "dryRun": False})
        self.assertEqual(status, 400)
        self.assertIn("confirmation", body["error"])
        self.assertFalse((self.root / ".env.example").exists())

        status, _, _ = self.request("POST", "/api/fixes", {"path": str(self.root), "dryRun": False, "confirm": True})
        self.assertEqual(status, 200)
        self.assertTrue((self.root / ".env.example").exists())

    def test_verify_route_returns_separate_execution_statuses(self):
        status, _, body = self.request("POST", "/api/verify", {"path": str(self.root)})
        self.assertEqual(status, 200)
        self.assertIn(body["docker"]["status"], {"UNAVAILABLE", "PASS", "FAIL"})
        self.assertIn(body["tests"]["status"], {"SKIPPED", "UNAVAILABLE", "PASS", "FAIL"})
        if body["tests"]["status"] == "SKIPPED":
            self.assertIn("No allowlisted documented test command", body["tests"]["evidence"])
        self.assertEqual(len(body["checks"]), 8)

    def test_unknown_routes_return_json_errors(self):
        status, _, body = self.request("GET", "/api/not-a-route")
        self.assertEqual(status, 404)
        self.assertIn("not found", body["error"].lower())

    def test_invalid_method_and_request_validation(self):
        status, _, body = self.request("PUT", "/api/audit")
        self.assertEqual(status, 405)
        self.assertEqual(body["error"], "Method not allowed.")

        self.client.request("POST", "/api/audit", body=b"{}")
        response = self.client.getresponse()
        self.assertEqual(response.status, 415)
        response.read()

        self.client.request("POST", "/api/audit", body=b"{", headers={"Content-Type": "application/json"})
        response = self.client.getresponse()
        self.assertEqual(response.status, 400)
        response.read()

        oversized = b"{" + b"x" * MAX_BODY_BYTES + b"}"
        self.client.close()
        self.client = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        self.client.request("POST", "/api/audit", body=oversized, headers={"Content-Type": "application/json"})
        response = self.client.getresponse()
        self.assertEqual(response.status, 413)
        response.read()

    def test_static_asset_containment_and_report_shape(self):
        for path in ("/%2e%2e/web.py", "/..%2Fweb.py", "/styles.css/../web.py"):
            status, _, body = self.request("GET", path)
            self.assertEqual(status, 404)
            self.assertIn("not found", body["error"].lower())
        status, _, body = self.request("POST", "/api/audit", {"path": str(self.root)})
        self.assertEqual(status, 200)
        self.assertIn("checks", body)
        self.assertIn("summary", body)


class PublicDashboardRouteTests(unittest.TestCase):
    def setUp(self):
        self.server = create_server("127.0.0.1", 0, public_demo=True)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.client = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)

    def tearDown(self):
        self.client.close()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def request(self, method, path, payload=None):
        body = json.dumps(payload).encode() if payload is not None else None
        headers = {"Content-Type": "application/json"} if body is not None else {}
        self.client.request(method, path, body=body, headers=headers)
        response = self.client.getresponse()
        raw = response.read()
        content_type = response.headers.get_content_type()
        return response.status, response.headers, json.loads(raw) if content_type == "application/json" and raw else raw

    def test_demo_is_redacted_and_public_actions_are_read_only(self):
        status, headers, body = self.request("GET", "/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(body["mode"], "public-demo")
        self.assertTrue(body["readOnly"])
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(headers["X-Frame-Options"], "DENY")

        status, _, body = self.request("GET", "/api/demo")
        self.assertEqual(status, 200)
        self.assertTrue(body["demo"])
        self.assertEqual(body["repository"], "bundled-demo")
        self.assertNotIn("omnirush.ai", json.dumps(body))

        for route in ("/api/audit", "/api/verify", "/api/fixes"):
            status, _, body = self.request("POST", route, {"path": str(Path.home() / "victim")})
            self.assertEqual(status, 403)
            self.assertIn("read-only", body["error"])

    def test_public_static_traversal_and_methods_are_blocked(self):
        status, _, body = self.request("GET", "/%2e%2e/web.py")
        self.assertEqual(status, 404)
        self.assertIn("not found", body["error"].lower())
        status, _, body = self.request("PUT", "/api/demo")
        self.assertEqual(status, 405)
        self.assertEqual(body["error"], "Method not allowed.")


class ServerConfigurationTests(unittest.TestCase):
    def test_port_uses_explicit_value_then_environment(self):
        self.assertEqual(configured_port(4321), 4321)
        old = os.environ.get("PORT")
        try:
            os.environ["PORT"] = "4322"
            self.assertEqual(configured_port(), 4322)
        finally:
            if old is None:
                os.environ.pop("PORT", None)
            else:
                os.environ["PORT"] = old


if __name__ == "__main__":
    unittest.main()
