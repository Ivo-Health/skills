import json
import tempfile
import unittest
from pathlib import Path

from ivo_skills.codex import check_codex
from tests.helpers import add_codex, make_repo, write


class CheckCodexTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        make_repo(self.root)
        add_codex(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def messages(self):
        return [f.message for f in check_codex(self.root)]

    def edit_marketplace(self, change):
        path = self.root / ".agents/plugins/marketplace.json"
        data = json.loads(path.read_text())
        change(data)
        path.write_text(json.dumps(data))

    def test_valid_codex_files_have_no_findings(self):
        self.assertEqual(check_codex(self.root), [])

    def test_no_codex_marketplace_is_fine(self):
        (self.root / ".agents/plugins/marketplace.json").unlink()
        self.assertEqual(check_codex(self.root), [])

    def test_local_source_must_start_with_dot_slash(self):
        self.edit_marketplace(lambda d: d["plugins"][0].update(source="plugins/ivo-health"))
        self.assertEqual(self.messages(), [
            "ivo-health: source must be './<folder>' in this repository, or a git url pinned with 'sha'"])

    def test_local_source_must_not_escape(self):
        self.edit_marketplace(lambda d: d["plugins"][0].update(source="./../x"))
        self.assertEqual(len(self.messages()), 1)

    def test_git_source_must_be_pinned(self):
        self.edit_marketplace(lambda d: d["plugins"][1]["source"].pop("sha"))
        self.assertEqual(self.messages(), [
            "superpowers: source must be './<folder>' in this repository, or a git url pinned with 'sha'"])

    def test_git_pin_must_match_claude_marketplace(self):
        self.edit_marketplace(lambda d: d["plugins"][1]["source"].update(sha="b" * 40))
        self.assertEqual(self.messages(), [
            "superpowers: pinned to bbbbbbbbbbbb but .claude-plugin/marketplace.json pins "
            "5bf4e7801107; keep them the same"])

    def test_missing_codex_manifest(self):
        (self.root / "plugins/ivo-health/.codex-plugin/plugin.json").unlink()
        self.assertEqual(self.messages(), ["file is missing"])

    def test_name_must_match(self):
        write(self.root, "plugins/ivo-health/.codex-plugin/plugin.json",
              json.dumps({"name": "other", "version": "0.1.0", "skills": "./skills/"}))
        self.assertIn("name 'other' must match the marketplace entry 'ivo-health'", self.messages())

    def test_version_must_match_claude_manifest(self):
        add_codex(self.root, version="0.2.0")
        self.assertEqual(self.messages(), [
            "'version' is '0.2.0' but .claude-plugin/plugin.json says '0.1.0'; keep them the same"])

    def test_skills_folder_must_exist(self):
        write(self.root, "plugins/ivo-health/.codex-plugin/plugin.json",
              json.dumps({"name": "ivo-health", "version": "0.1.0", "skills": "./missing/"}))
        self.assertEqual(self.messages(), ["'skills' must point to a folder in the plugin"])
