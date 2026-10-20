import tempfile
import unittest
from pathlib import Path
from unittest.mock import call, patch
from subprocess import CompletedProcess

from clone_to_confidence.verifier import _documented_test, verify


class VerifierTests(unittest.TestCase):
    def test_detects_uv_run_documented_test_command(self):
        root = Path(tempfile.mkdtemp())
        (root / "README.md").write_text("## Test\nuv run python -m unittest discover -s tests -v\n")
        self.assertEqual(
            _documented_test(root),
            ["uv", "run", "python", "-m", "unittest", "discover", "-s", "tests", "-v"],
        )

    def test_prefers_uv_run_when_readme_also_has_bare_test_command(self):
        root = Path(tempfile.mkdtemp())
        (root / "README.md").write_text(
            "docker run image python -m unittest discover -s tests -v\n"
            "uv run python -m unittest discover -s tests -v\n"
        )
        self.assertEqual(
            _documented_test(root),
            ["uv", "run", "python", "-m", "unittest", "discover", "-s", "tests", "-v"],
        )

    def test_failed_test_reports_redacted_evidence(self):
        root = Path(tempfile.mkdtemp())
        (root / "README.md").write_text("## Test\nuv run python -m unittest discover -s tests -v\n")
        fake_secret = "sk-" + "x" * 20
        completed = CompletedProcess(
            args=[], returncode=1, stdout=f"failure output TOKEN={fake_secret}\n", stderr="traceback evidence\n"
        )
        with patch("clone_to_confidence.verifier.shutil.which", side_effect=lambda name: "/usr/bin/uv" if name == "uv" else None), patch(
            "clone_to_confidence.verifier.subprocess.run", return_value=completed
        ) as run:
            result = verify(root)
        self.assertEqual(result["tests"]["status"], "FAIL")
        self.assertIn("traceback evidence", result["tests"]["evidence"])
        self.assertIn("[REDACTED_SECRET]", result["tests"]["evidence"])
        self.assertNotIn(fake_secret, result["tests"]["evidence"])
        self.assertEqual(run.call_args_list[-1], call(
            ["uv", "run", "python", "-m", "unittest", "discover", "-s", "tests", "-v"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=120,
        ))

    def test_skipped_tests_explain_why_nothing_ran(self):
        root = Path(tempfile.mkdtemp())
        result = verify(root)
        self.assertEqual(result["tests"]["status"], "SKIPPED")
        self.assertIn("No allowlisted documented test command", result["tests"]["evidence"])
