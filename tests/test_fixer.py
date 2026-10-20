import tempfile, unittest
from pathlib import Path
from clone_to_confidence.fixer import apply
class FixerTests(unittest.TestCase):
 def test_dry_run_does_not_write_or_copy_secret(self):
  d=Path(tempfile.mkdtemp()); (d/"pyproject.toml").write_text("[project]\nname=\"x\"\n"); changes=apply(d,True); self.assertFalse((d/".env.example").exists()); self.assertIn("YOUR_VALUE_HERE", changes[0][2]); self.assertNotIn("sk-", changes[0][2])
 def test_apply_create_only(self):
  d=Path(tempfile.mkdtemp()); (d/"pyproject.toml").write_text("x"); apply(d,False); old=(d/".env.example").read_text(); apply(d,False); self.assertEqual(old,(d/".env.example").read_text())
