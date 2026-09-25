import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from ivo_skills.version import MANIFEST, check_version_bump, parse_semver
from tests.helpers import write


def git(root, *args):
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


class ParseSemverTest(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(parse_semver("1.2.30"), (1, 2, 30))

    def test_rejects_other_formats(self):
        for bad in ("1.2", "v1.2.3", "1.2.3-beta"):
            with self.assertRaises(ValueError):
                parse_semver(bad)


class VersionBumpTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        git(self.root, "init", "-q", "-b", "main")
        git(self.root, "config", "user.email", "test@example.com")
        git(self.root, "config", "user.name", "Test")
        write(self.root, "README.md", "readme\n")

    def tearDown(self):
        self._tmp.cleanup()

    def commit(self, message="change"):
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", message)

    def set_version(self, version):
        write(self.root, MANIFEST, json.dumps({"name": "ivo-health", "version": version}))

    def start_branch(self, version="0.1.0"):
        self.set_version(version)
        write(self.root, "plugins/ivo-health/skills/a/SKILL.md", "one\n")
        self.commit("base")
        git(self.root, "checkout", "-q", "-b", "feature")

    def test_no_plugin_change_passes(self):
        self.start_branch()
        write(self.root, "README.md", "changed\n")
        self.commit()
        self.assertEqual(check_version_bump(self.root, "main"), [])

    def test_change_without_bump_fails(self):
        self.start_branch()
        write(self.root, "plugins/ivo-health/skills/a/SKILL.md", "two\n")
        self.commit()
        findings = check_version_bump(self.root, "main")
        self.assertEqual(len(findings), 1)
        self.assertIn("must be higher than 0.1.0", findings[0].message)

    def test_lower_version_fails(self):
        self.start_branch("0.2.0")
        self.set_version("0.1.9")
        self.commit()
        self.assertEqual(len(check_version_bump(self.root, "main")), 1)

    def test_change_with_bump_passes(self):
        self.start_branch()
        write(self.root, "plugins/ivo-health/skills/a/SKILL.md", "two\n")
        self.set_version("0.1.1")
        self.commit()
        self.assertEqual(check_version_bump(self.root, "main"), [])

    def test_plugin_new_on_branch_passes(self):
        self.commit("base without plugin")
        git(self.root, "checkout", "-q", "-b", "feature")
        self.set_version("0.1.0")
        self.commit()
        self.assertEqual(check_version_bump(self.root, "main"), [])

    def test_unknown_base_ref_is_reported(self):
        self.start_branch()
        findings = check_version_bump(self.root, "origin/does-not-exist")
        self.assertIn("could not compare with origin/does-not-exist", findings[0].message)
