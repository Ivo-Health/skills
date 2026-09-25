import tempfile
import unittest
from pathlib import Path

from ivo_skills.external import SKILLS_DIR, check_external, hash_tree, load_lock, save_lock
from tests.helpers import write

COMMIT = "c55ee46073ed923f86ce59a5eb3b6d895095d1b7"


class ExternalTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        for name in ("grill-me", "grilling"):
            write(self.root, f"{SKILLS_DIR}/{name}/SKILL.md", f"---\nname: {name}\n---\n")
            write(self.root, f"{SKILLS_DIR}/{name}/agents/openai.yaml", "interface: {}\n")
        save_lock(self.root, {"skills": {
            name: self.entry(name, requires=["grilling"] if name == "grill-me" else [])
            for name in ("grill-me", "grilling")}})

    def tearDown(self):
        self._tmp.cleanup()

    def entry(self, name, **overrides):
        entry = {
            "repo": "https://github.com/mattpocock/skills",
            "path": f"skills/productivity/{name}",
            "commit": COMMIT,
            "licence": "MIT",
            "requires": [],
            "sha256": hash_tree(self.root / SKILLS_DIR / name),
            "reviewed_by": "Test Reviewer",
            "reviewed_on": "2026-09-25",
        }
        entry.update(overrides)
        return entry

    def messages(self):
        return [f"{f.path}: {f.message}" for f in check_external(self.root)]

    def test_hash_tree_uses_posix_relative_paths(self):
        self.assertEqual(sorted(hash_tree(self.root / SKILLS_DIR / "grilling")),
                         ["SKILL.md", "agents/openai.yaml"])

    def test_clean_copy_has_no_findings(self):
        self.assertEqual(check_external(self.root), [])

    def test_no_lock_file_is_fine(self):
        (self.root / "external-skills.lock.json").unlink()
        self.assertEqual(check_external(self.root), [])

    def test_edited_file(self):
        write(self.root, f"{SKILLS_DIR}/grilling/SKILL.md", "---\nname: grilling\n---\nedited\n")
        self.assertEqual(self.messages(), [
            f"{SKILLS_DIR}/grilling/SKILL.md: file has been changed since it was copied; "
            "copied skills must not be edited"])

    def test_added_file(self):
        write(self.root, f"{SKILLS_DIR}/grilling/extra.md", "x")
        self.assertEqual(self.messages(),
                         [f"{SKILLS_DIR}/grilling/extra.md: file is not in the lock file"])

    def test_removed_file(self):
        (self.root / SKILLS_DIR / "grilling/agents/openai.yaml").unlink()
        self.assertEqual(self.messages(),
                         [f"{SKILLS_DIR}/grilling/agents/openai.yaml: file listed in the lock file is missing"])

    def test_missing_folder(self):
        for f in sorted((self.root / SKILLS_DIR / "grilling").rglob("*"), reverse=True):
            f.unlink() if f.is_file() else f.rmdir()
        (self.root / SKILLS_DIR / "grilling").rmdir()
        self.assertIn(f"{SKILLS_DIR}/grilling: copied skill folder is missing", self.messages())
        self.assertIn(f"{SKILLS_DIR}/grill-me: grill-me requires 'grilling', which is missing",
                      self.messages())

    def test_missing_fields(self):
        lock = load_lock(self.root)
        del lock["skills"]["grilling"]["licence"]
        del lock["skills"]["grilling"]["reviewed_by"]
        save_lock(self.root, lock)
        self.assertEqual(self.messages(),
                         ["external-skills.lock.json: grilling: missing licence, reviewed_by"])

    def test_short_commit_and_bad_date(self):
        lock = load_lock(self.root)
        lock["skills"]["grilling"].update(commit="c55ee46", reviewed_on="25/09/2026")
        save_lock(self.root, lock)
        self.assertEqual(self.messages(), [
            "external-skills.lock.json: grilling: 'commit' must be a full 40-character sha",
            "external-skills.lock.json: grilling: 'reviewed_on' must be YYYY-MM-DD"])

    def test_bad_skill_name_in_lock(self):
        lock = load_lock(self.root)
        lock["skills"]["../escape"] = lock["skills"]["grilling"]
        save_lock(self.root, lock)
        self.assertIn("external-skills.lock.json: '../escape' is not a valid skill name",
                      self.messages())
