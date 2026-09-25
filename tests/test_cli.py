import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from ivo_skills.cli import check_skills_main
from tests.helpers import make_repo, write


class CheckSkillsCliTest(unittest.TestCase):
    def run_cli(self, root):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = check_skills_main(["--root", str(root)])
        return code, out.getvalue()

    def test_clean_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_repo(Path(tmp))
            self.assertEqual(self.run_cli(tmp), (0, "All checks passed\n"))

    def test_findings_exit_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_repo(Path(tmp))
            write(Path(tmp), "notes.md", "bob@gmail.com")
            code, out = self.run_cli(tmp)
            self.assertEqual(code, 1)
            self.assertIn("notes.md:1: [pii] email address outside the allowed example domains", out)
            self.assertTrue(out.endswith("1 problem(s) found\n"))

    def test_real_repository_passes(self):
        code, out = self.run_cli(Path(__file__).resolve().parents[1])
        self.assertEqual(code, 0, out)
