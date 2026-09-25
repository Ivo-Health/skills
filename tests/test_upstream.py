import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from ivo_skills.external import save_lock
from ivo_skills.upstream import build_report, latest_tag
from tests.helpers import write


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True).stdout.strip()


def make_upstream(path: Path) -> str:
    path.mkdir()
    git(path, "init", "-q", "-b", "main")
    git(path, "config", "user.email", "test@example.com")
    git(path, "config", "user.name", "Test")
    write(path, "skills/grilling/SKILL.md", "v1\n")
    write(path, "skills/other/SKILL.md", "v1\n")
    git(path, "add", "-A")
    git(path, "commit", "-q", "-m", "v1")
    return git(path, "rev-parse", "HEAD")


def commit_change(path: Path, rel: str) -> str:
    write(path, rel, "changed\n")
    git(path, "add", "-A")
    git(path, "commit", "-q", "-m", "change")
    return git(path, "rev-parse", "HEAD")


class LatestTagTest(unittest.TestCase):
    def test_picks_highest_semver_and_peels_annotated_tags(self):
        with tempfile.TemporaryDirectory() as tmp:
            up = Path(tmp) / "up"
            first = make_upstream(up)
            git(up, "tag", "v1.9.0")
            second = commit_change(up, "README.md")
            git(up, "tag", "-a", "v1.10.0", "-m", "release")
            git(up, "tag", "not-a-version")
            self.assertEqual(latest_tag(str(up)), ("v1.10.0", second))
            self.assertNotEqual(first, second)

    def test_no_tags(self):
        with tempfile.TemporaryDirectory() as tmp:
            up = Path(tmp) / "up"
            make_upstream(up)
            self.assertIsNone(latest_tag(str(up)))


class BuildReportTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name)
        self.skills_up = base / "skills-up"
        self.plugin_up = base / "plugin-up"
        self.pinned = make_upstream(self.skills_up)
        self.plugin_sha = make_upstream(self.plugin_up)
        git(self.plugin_up, "tag", "v1.0.0")
        self.root = base / "repo"
        write(self.root, ".claude-plugin/marketplace.json", json.dumps({"plugins": [
            {"name": "ivo-health", "source": "./plugins/ivo-health"},
            {"name": "superpowers", "source": {"source": "github", "repo": "obra/superpowers",
                                               "sha": self.plugin_sha}}]}))
        save_lock(self.root, {"skills": {"grilling": {
            "repo": str(self.skills_up), "path": "skills/grilling", "commit": self.pinned}}})
        self.url_for = lambda repo: str(self.plugin_up)

    def tearDown(self):
        self._tmp.cleanup()

    def report(self):
        return build_report(self.root, url_for=self.url_for)

    def test_nothing_changed(self):
        self.assertEqual(self.report(), "")

    def test_unrelated_upstream_change_is_ignored(self):
        commit_change(self.skills_up, "skills/other/SKILL.md")
        self.assertEqual(self.report(), "")

    def test_copied_skill_changed(self):
        head = commit_change(self.skills_up, "skills/grilling/SKILL.md")
        report = self.report()
        self.assertIn("**grilling** (copied skill)", report)
        self.assertIn(f"compare/{self.pinned}...{head}", report)

    def test_new_plugin_release(self):
        new = commit_change(self.plugin_up, "README.md")
        git(self.plugin_up, "tag", "v1.1.0")
        report = self.report()
        self.assertIn("**superpowers** (whole plugin)", report)
        self.assertIn("latest release is `v1.1.0`", report)
        self.assertIn(new[:12], report)

    def test_missing_pinned_commit_is_reported(self):
        save_lock(self.root, {"skills": {"grilling": {
            "repo": str(self.skills_up), "path": "skills/grilling", "commit": "0" * 40}}})
        self.assertIn("could not compare", self.report())
