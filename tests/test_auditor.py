import json, subprocess, tempfile, unittest
from pathlib import Path
from clone_to_confidence.checks import audit
from clone_to_confidence.report import report
class AuditorTests(unittest.TestCase):
 def make(self, extra=""):
  d=Path(tempfile.mkdtemp(prefix="ctc-")); (d/"pyproject.toml").write_text("[project]\nname=\"x\"\n"); (d/"uv.lock").write_text("version = 1\n"); (d/".python-version").write_text("3.12\n"); (d/"Dockerfile").write_text("FROM python:3.12-slim\n"); (d/"README.md").write_text("# X\n## Setup\ninstall\n## Run\nrun\n## Test\npython -m unittest\n"+extra); (d/".env.example").write_text("TOKEN=YOUR_VALUE_HERE\n"); return d
 def test_healthy_and_json(self):
  d=self.make(); (d/".git").mkdir(); cs=audit(d); self.assertEqual(len(cs),8); self.assertTrue(json.loads(report(cs,d,"json"))["checks"])
 def test_missing_items_and_absolute_path(self):
  d=self.make("/home/" + "alice/project\n"); (d/"uv.lock").unlink(); (d/".python-version").unlink(); (d/"Dockerfile").unlink(); self.assertEqual(audit(d)[1].status,"FAIL"); self.assertEqual(audit(d)[2].status,"FAIL"); self.assertEqual(audit(d)[3].status,"FAIL"); self.assertEqual(audit(d)[7].status,"WARN")
 def test_secret_not_printed(self):
  d=self.make(); (d/".env.example").write_text("TOKEN=sk-12345678901234567890\n"); cs=audit(d); text=report(cs,d); self.assertNotIn("12345678901234567890",text); self.assertEqual(cs[6].status,"FAIL")
class CliTests(unittest.TestCase):
 def test_invalid_path(self):
  p=subprocess.run(["python3","-m","clone_to_confidence.cli","audit","/does/not/exist"],capture_output=True,text=True); self.assertNotEqual(p.returncode,0)
