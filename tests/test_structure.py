import json
import tempfile
import unittest
from pathlib import Path

from ivo_skills.structure import check_structure
from tests.helpers import make_repo, write


class CheckStructureTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        make_repo(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def messages(self):
        return [f.message for f in check_structure(self.root)]

    def edit_marketplace(self, change):
        path = self.root / ".claude-plugin/marketplace.json"
        data = json.loads(path.read_text())
        change(data)
        path.write_text(json.dumps(data))

    def test_valid_repo_has_no_findings(self):
        self.assertEqual(check_structure(self.root), [])

    def test_missing_marketplace(self):
        (self.root / ".claude-plugin/marketplace.json").unlink()
        self.assertEqual(self.messages(), ["file is missing"])

    def test_invalid_json(self):
        write(self.root, ".claude-plugin/marketplace.json", "{not json")
        self.assertIn("invalid JSON", self.messages()[0])

    def test_missing_owner(self):
        self.edit_marketplace(lambda d: d.pop("owner"))
        self.assertIn("missing 'owner.name'", self.messages())

    def test_unpinned_github_source(self):
        self.edit_marketplace(lambda d: d["plugins"][1]["source"].pop("sha"))
        self.assertIn("superpowers: github sources must be pinned with a full 40-character 'sha'",
                      self.messages())

    def test_relative_source_with_dot_dot(self):
        self.edit_marketplace(lambda d: d["plugins"][0].update(source="./../elsewhere"))
        self.assertIn("ivo-health: relative source must start with './' and not contain '..'",
                      self.messages())

    def test_plugin_name_mismatch(self):
        write(self.root, "plugins/ivo-health/.claude-plugin/plugin.json",
              json.dumps({"name": "other", "version": "0.1.0"}))
        self.assertIn("name 'other' must match the marketplace entry 'ivo-health'", self.messages())

    def test_bad_version(self):
        write(self.root, "plugins/ivo-health/.claude-plugin/plugin.json",
              json.dumps({"name": "ivo-health", "version": "1.0"}))
        self.assertIn("'version' must be MAJOR.MINOR.PATCH", self.messages())

    def test_skill_folder_without_skill_md(self):
        (self.root / "plugins/ivo-health/skills/empty").mkdir()
        self.assertIn("skill folder has no SKILL.md", self.messages())

    def test_skill_name_must_match_folder(self):
        write(self.root, "plugins/ivo-health/skills/example/SKILL.md",
              "---\nname: different\ndescription: x\n---\n")
        self.assertIn("'name' is 'different' but the folder is 'example'", self.messages())

    def test_skill_name_format(self):
        write(self.root, "plugins/ivo-health/skills/Bad_Name/SKILL.md",
              "---\nname: Bad_Name\ndescription: x\n---\n")
        self.assertIn("'name' must be lower-case letters, numbers and hyphens, 64 characters at most",
                      self.messages())

    def test_description_required(self):
        write(self.root, "plugins/ivo-health/skills/example/SKILL.md", "---\nname: example\n---\n")
        self.assertIn("'description' is required", self.messages())

    def test_description_too_long(self):
        write(self.root, "plugins/ivo-health/skills/example/SKILL.md",
              "---\nname: example\ndescription: " + "a" * 1025 + "\n---\n")
        self.assertIn("'description' must be 1024 characters or fewer", self.messages())

    def test_bad_front_matter_is_reported_not_raised(self):
        write(self.root, "plugins/ivo-health/skills/example/SKILL.md", "no front matter")
        self.assertIn("file must start with a '---' front matter line", self.messages())
