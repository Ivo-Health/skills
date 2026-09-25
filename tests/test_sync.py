import os
import subprocess
import tempfile
import unittest
from datetime import date
from pathlib import Path

from ivo_skills.external import SKILLS_DIR, check_external, load_lock
from ivo_skills.sync import SyncError, sync_skill
from tests.helpers import write


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True).stdout.strip()


class SyncTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name)
        self.upstream = base / "upstream"
        self.root = base / "repo"
        self.root.mkdir()
        self.upstream.mkdir()
        git(self.upstream, "init", "-q", "-b", "main")
        git(self.upstream, "config", "user.email", "test@example.com")
        git(self.upstream, "config", "user.name", "Test")
        write(self.upstream, "skills/grilling/SKILL.md", "---\nname: grilling\n---\nv1\n")
        write(self.upstream, "skills/grilling/agents/openai.yaml", "interface: {}\n")
        git(self.upstream, "add", "-A")
        git(self.upstream, "commit", "-q", "-m", "v1")
        self.v1 = git(self.upstream, "rev-parse", "HEAD")

    def tearDown(self):
        self._tmp.cleanup()

    def add(self, **kwargs):
        args = dict(repo=str(self.upstream), path="skills/grilling", licence="MIT",
                    reviewed_by="Test Reviewer", today=date(2026, 9, 25))
        args.update(kwargs)
        return sync_skill(self.root, "grilling", self.v1, **args)

    def test_new_skill_is_copied_and_locked(self):
        entry = self.add()
        self.assertEqual(entry["commit"], self.v1)
        self.assertEqual(entry["reviewed_on"], "2026-09-25")
        self.assertEqual(entry["requires"], [])
        self.assertEqual(sorted(entry["sha256"]), ["SKILL.md", "agents/openai.yaml"])
        self.assertEqual(load_lock(self.root)["skills"]["grilling"], entry)
        self.assertEqual(check_external(self.root), [])

    def test_short_commit_or_tag_is_stored_as_full_sha(self):
        git(self.upstream, "tag", "v1.0.0")
        entry = sync_skill(self.root, "grilling", "v1.0.0", repo=str(self.upstream),
                           path="skills/grilling", licence="MIT", reviewed_by="R")
        self.assertEqual(entry["commit"], self.v1)

    def test_update_uses_repo_and_path_from_lock_and_removes_old_files(self):
        self.add()
        (self.upstream / "skills/grilling/agents/openai.yaml").unlink()
        write(self.upstream, "skills/grilling/SKILL.md", "---\nname: grilling\n---\nv2\n")
        git(self.upstream, "add", "-A")
        git(self.upstream, "commit", "-q", "-m", "v2")
        v2 = git(self.upstream, "rev-parse", "HEAD")
        entry = sync_skill(self.root, "grilling", v2, reviewed_by="Second Reviewer")
        self.assertEqual(entry["commit"], v2)
        self.assertEqual(entry["licence"], "MIT")
        self.assertEqual(sorted(entry["sha256"]), ["SKILL.md"])
        self.assertFalse((self.root / SKILLS_DIR / "grilling/agents").exists())

    def test_new_skill_needs_repo_path_and_licence(self):
        with self.assertRaisesRegex(SyncError, "give --repo, --path and --licence"):
            sync_skill(self.root, "grilling", self.v1, reviewed_by="R")

    def test_rejects_bad_skill_name(self):
        with self.assertRaisesRegex(SyncError, "not a valid skill name"):
            sync_skill(self.root, "../escape", self.v1, repo=str(self.upstream),
                       path="skills/grilling", licence="MIT", reviewed_by="R")

    def test_rejects_path_outside_upstream_repo(self):
        with self.assertRaisesRegex(SyncError, "must stay inside the upstream repository"):
            self.add(path="../outside")

    def test_rejects_symlinks(self):
        os.symlink("/etc/hostname", self.upstream / "skills/grilling/link")
        git(self.upstream, "add", "-A")
        git(self.upstream, "commit", "-q", "-m", "link")
        self.v1 = git(self.upstream, "rev-parse", "HEAD")
        with self.assertRaisesRegex(SyncError, "contains a symlink"):
            self.add()
        self.assertFalse((self.root / SKILLS_DIR / "grilling").exists())

    def test_rejects_symlinked_parent_folder(self):
        outside = Path(self._tmp.name) / "outside" / "secret"
        write(outside.parent, "secret/SKILL.md", "---\nname: secret\n---\n")
        write(outside.parent, "secret/key", "private\n")
        os.symlink(str(outside.parent), self.upstream / "linked")
        git(self.upstream, "add", "-A")
        git(self.upstream, "commit", "-q", "-m", "link")
        self.v1 = git(self.upstream, "rev-parse", "HEAD")
        with self.assertRaisesRegex(SyncError, "symlink"):
            self.add(path="linked/secret")
        self.assertFalse((self.root / SKILLS_DIR / "grilling").exists())

    def test_rejects_folder_without_skill_md(self):
        with self.assertRaisesRegex(SyncError, "has no SKILL.md"):
            self.add(path="skills")

    def test_unknown_commit(self):
        with self.assertRaises(SyncError):
            sync_skill(self.root, "grilling", "0" * 40, repo=str(self.upstream),
                       path="skills/grilling", licence="MIT", reviewed_by="R")
