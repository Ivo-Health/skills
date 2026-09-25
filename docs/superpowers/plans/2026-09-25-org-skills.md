# Organisation Skills Repository Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn `ivo-health/skills` into a private plugin marketplace. The Claude organisation sync, the ChatGPT workspace sync, Claude Code and Codex all read our own skills and pinned external skills from it. CI checks keep patient data, secrets and edited copies of external skills out.

**Architecture:** `.claude-plugin/marketplace.json` lists two plugins: our `ivo-health` plugin (a folder in this repo) and Superpowers (a `github` source pinned to a commit). Chosen external skills (Matt Pocock's `grill-me` and `grilling`) are copied unmodified into our plugin and recorded in `external-skills.lock.json`. A small stdlib-only Python package in `scripts/ivo_skills/` implements the checks, the sync script and the upstream check. GitHub Actions run them.

**Tech Stack:** Python 3.11 standard library (`unittest`, `json`, `re`, `subprocess`), git, GitHub Actions, gitleaks 8.30.1, Claude Code CLI 2.1.282 (`claude plugin validate`).

**Spec:** `docs/superpowers/specs/2026-09-25-org-skills-design.md`

## Global Constraints

- No third-party Python packages. Standard library only.
- No real patient data anywhere, including tests. Test NHS numbers are **generated at test time** by a helper, never written into files.
- A finding message must never contain the matched value (NHS number, email or phone), so CI logs cannot leak PII.
- Plain English in all docs and skill text. Follow the NHS service manual content style: sentence case headings, no exclamation marks, no "e.g." or "i.e.", and no flashy language.
- Plugin name `ivo-health`, marketplace name `ivo-health`, skills folder `plugins/ivo-health/skills/`.
- Superpowers pin: `obra/superpowers` at `5bf4e78011075bcfc0dc295f0724994cd123ee71` (tag `v6.4.1`).
- Matt Pocock pin: `https://github.com/mattpocock/skills` at `c55ee46073ed923f86ce59a5eb3b6d895095d1b7`, paths `skills/productivity/grill-me` and `skills/productivity/grilling`, MIT licence.
- GitHub Actions pinned by commit: `actions/checkout@fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09 # v5.1.0`.
- Every commit message ends with the two trailer lines:
  ```
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01Sd9cXfYMCwtEwRTGVY4q2t
  ```
- Unit tests run with: `PYTHONPATH=scripts python3 -m unittest discover -s tests -v`

## Review Focus

1. **Hex hashes and commit SHAs:** 40- and 64-character hex strings in the lock file and `marketplace.json` must not be reported as NHS numbers or phone numbers, even when they contain long runs of digits. Test in Task 2.
2. **CI logs:** a finding must not print the matched PII value. Test in Task 2.
3. **Hostile sync input:** `sync-external` must refuse a skill name or upstream path that escapes its folder (`../x`), and an upstream skill containing symlinks, because `copytree` would otherwise copy files from the machine running it. Test in Task 6.
4. **Version check edge cases:** the check passes when the plugin folder did not change, or when the plugin does not exist on the base branch (the first PR). It fails when the version is unchanged or lower. Test in Task 4.
5. **Multi-line descriptions:** a `SKILL.md` using a folded block (`description: >`) must parse to the joined text, not `">"`. Test in Task 1.

## Prerequisite (human, before Task 1)

The repo has only one branch, `claude/vigilant-shannon-7rqxkc`. Before building:

1. Create `main` from the first commit (the spec commit), and set it as the default branch in GitHub settings.
2. After Task 5, add branch protection on `main`: require a PR, one approval and the `Checks` workflow.

All tasks commit to `claude/vigilant-shannon-7rqxkc`. The PR targets `main`.

---

### Task 1: Findings, front matter parser and structure checks

**Files:**
- Create: `scripts/ivo_skills/__init__.py` (empty)
- Create: `scripts/ivo_skills/findings.py`
- Create: `scripts/ivo_skills/frontmatter.py`
- Create: `scripts/ivo_skills/structure.py`
- Create: `tests/__init__.py` (empty)
- Create: `tests/helpers.py`
- Test: `tests/test_frontmatter.py`, `tests/test_structure.py`

**Interfaces:**
- Produces:
  - `Finding(check: str, path: str, message: str, line: int | None = None)`, a frozen dataclass whose `str()` is `"path:line: [check] message"`
  - `parse_frontmatter(text: str) -> dict[str, str]`, which raises `FrontmatterError(ValueError)`
  - `check_structure(root: Path) -> list[Finding]`
  - constants in `structure.py`: `MARKETPLACE = Path(".claude-plugin/marketplace.json")`, `NAME_RE`, `SHA_RE`
  - `tests/helpers.py`: `write(root: Path, rel: str, text: str) -> Path`, `make_repo(root: Path) -> None` (a minimal valid marketplace)

- [ ] **Step 1: Write the test helpers**

`tests/helpers.py`:

```python
import json
from pathlib import Path

VALID_SKILL = """---
name: {name}
description: Use when testing the Ivo Health skill checks.
---

# Test skill
"""


def write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def make_repo(root: Path) -> None:
    """A minimal valid marketplace with one local plugin and one skill."""
    write(root, ".claude-plugin/marketplace.json", json.dumps({
        "name": "ivo-health",
        "owner": {"name": "Ivo Health"},
        "plugins": [
            {"name": "ivo-health", "source": "./plugins/ivo-health"},
            {"name": "superpowers", "source": {
                "source": "github", "repo": "obra/superpowers",
                "sha": "5bf4e78011075bcfc0dc295f0724994cd123ee71"}},
        ],
    }))
    write(root, "plugins/ivo-health/.claude-plugin/plugin.json",
          json.dumps({"name": "ivo-health", "version": "0.1.0"}))
    write(root, "plugins/ivo-health/skills/example/SKILL.md",
          VALID_SKILL.format(name="example"))
```

- [ ] **Step 2: Write the failing front matter tests**

`tests/test_frontmatter.py`:

```python
import unittest

from ivo_skills.frontmatter import FrontmatterError, parse_frontmatter


class ParseFrontmatterTest(unittest.TestCase):
    def test_simple_fields(self):
        text = "---\nname: grill-me\ndescription: A relentless interview.\n---\nBody"
        self.assertEqual(parse_frontmatter(text),
                         {"name": "grill-me", "description": "A relentless interview."})

    def test_value_containing_colon(self):
        text = "---\ndescription: Use when: planning\n---\n"
        self.assertEqual(parse_frontmatter(text)["description"], "Use when: planning")

    def test_quoted_value(self):
        text = '---\nname: "grilling"\n---\n'
        self.assertEqual(parse_frontmatter(text)["name"], "grilling")

    def test_folded_block_description(self):
        text = "---\nname: x\ndescription: >\n  First line\n  second line.\n---\n"
        self.assertEqual(parse_frontmatter(text)["description"], "First line second line.")

    def test_nested_values_are_ignored(self):
        text = "---\nname: x\nmetadata:\n  owner: someone\n---\n"
        self.assertEqual(parse_frontmatter(text), {"name": "x", "metadata": ""})

    def test_missing_opening_line(self):
        with self.assertRaises(FrontmatterError):
            parse_frontmatter("name: x\n")

    def test_unclosed(self):
        with self.assertRaises(FrontmatterError):
            parse_frontmatter("---\nname: x\n")

    def test_line_without_colon(self):
        with self.assertRaises(FrontmatterError):
            parse_frontmatter("---\njust words\n---\n")
```

- [ ] **Step 3: Run it to confirm it fails**

Run: `PYTHONPATH=scripts python3 -m unittest tests.test_frontmatter -v`
Expected: ERROR, `ModuleNotFoundError: No module named 'ivo_skills'`

- [ ] **Step 4: Implement `findings.py` and `frontmatter.py`**

`scripts/ivo_skills/findings.py`:

```python
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Finding:
    check: str
    path: str
    message: str
    line: Optional[int] = None

    def __str__(self) -> str:
        where = f"{self.path}:{self.line}" if self.line else self.path
        return f"{where}: [{self.check}] {self.message}"
```

`scripts/ivo_skills/frontmatter.py`:

```python
"""Read the simple YAML front matter used in SKILL.md files, without PyYAML."""

BLOCK_MARKERS = (">", "|", ">-", "|-")


class FrontmatterError(ValueError):
    pass


def parse_frontmatter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise FrontmatterError("file must start with a '---' front matter line")
    fields: dict[str, str] = {}
    block_key = None
    for line in lines[1:]:
        if line.strip() == "---":
            return fields
        if line[:1] in (" ", "\t"):
            # Continuation of a block value, or part of a nested value we do not need.
            if block_key:
                fields[block_key] = (fields[block_key] + " " + line.strip()).strip()
            continue
        block_key = None
        if not line.strip() or line.startswith("#"):
            continue
        key, sep, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if not sep or not key:
            raise FrontmatterError(f"expected 'key: value', got {line!r}")
        if value in BLOCK_MARKERS:
            fields[key] = ""
            block_key = key
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        fields[key] = value
    raise FrontmatterError("front matter is not closed with '---'")
```

Also create an empty `scripts/ivo_skills/__init__.py` and an empty `tests/__init__.py`.

- [ ] **Step 5: Run the front matter tests**

Run: `PYTHONPATH=scripts python3 -m unittest tests.test_frontmatter -v`
Expected: 8 tests, OK

- [ ] **Step 6: Write the failing structure tests**

`tests/test_structure.py`:

```python
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
```

- [ ] **Step 7: Run it to confirm it fails**

Run: `PYTHONPATH=scripts python3 -m unittest tests.test_structure -v`
Expected: ERROR, `No module named 'ivo_skills.structure'`

- [ ] **Step 8: Implement `structure.py`**

`scripts/ivo_skills/structure.py`:

```python
"""Check marketplace.json, plugin.json and SKILL.md files."""
import json
import re
from pathlib import Path
from typing import Optional

from .findings import Finding
from .frontmatter import FrontmatterError, parse_frontmatter

MARKETPLACE = Path(".claude-plugin/marketplace.json")
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def _load_json(path: Path, root: Path, findings: list) -> Optional[dict]:
    rel = path.relative_to(root).as_posix()
    if not path.is_file():
        findings.append(Finding("structure", rel, "file is missing"))
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        findings.append(Finding("structure", rel, f"invalid JSON: {e.msg}", e.lineno))
        return None


def check_structure(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    market = _load_json(root / MARKETPLACE, root, findings)
    if market is None:
        return findings
    rel = MARKETPLACE.as_posix()
    if not market.get("name"):
        findings.append(Finding("structure", rel, "missing 'name'"))
    owner = market.get("owner")
    if not isinstance(owner, dict) or not owner.get("name"):
        findings.append(Finding("structure", rel, "missing 'owner.name'"))
    plugins = market.get("plugins")
    if not isinstance(plugins, list) or not plugins:
        findings.append(Finding("structure", rel, "'plugins' must be a non-empty list"))
        return findings
    for i, entry in enumerate(plugins):
        name = entry.get("name") if isinstance(entry, dict) else None
        if not name:
            findings.append(Finding("structure", rel, f"plugins[{i}] is missing 'name'"))
            continue
        source = entry.get("source")
        if isinstance(source, str):
            findings += _check_local_plugin(root, name, source)
        elif isinstance(source, dict) and source.get("source") == "github":
            if not SHA_RE.match(str(source.get("sha", ""))):
                findings.append(Finding(
                    "structure", rel,
                    f"{name}: github sources must be pinned with a full 40-character 'sha'"))
        else:
            findings.append(Finding(
                "structure", rel,
                f"{name}: source must be a relative path or a pinned github source"))
    return findings


def _check_local_plugin(root: Path, name: str, source: str) -> list[Finding]:
    if not source.startswith("./") or ".." in Path(source).parts:
        return [Finding("structure", MARKETPLACE.as_posix(),
                        f"{name}: relative source must start with './' and not contain '..'")]
    findings: list[Finding] = []
    plugin_dir = root / source
    manifest_path = plugin_dir / ".claude-plugin" / "plugin.json"
    manifest = _load_json(manifest_path, root, findings)
    if manifest is None:
        return findings
    rel = manifest_path.relative_to(root).as_posix()
    if manifest.get("name") != name:
        findings.append(Finding(
            "structure", rel,
            f"name {manifest.get('name')!r} must match the marketplace entry {name!r}"))
    if not SEMVER_RE.match(str(manifest.get("version", ""))):
        findings.append(Finding("structure", rel, "'version' must be MAJOR.MINOR.PATCH"))
    skills_dir = plugin_dir / "skills"
    if skills_dir.is_dir():
        for skill_dir in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
            findings += check_skill_dir(root, skill_dir)
    return findings


def check_skill_dir(root: Path, skill_dir: Path) -> list[Finding]:
    path = skill_dir / "SKILL.md"
    rel = path.relative_to(root).as_posix()
    if not path.is_file():
        return [Finding("structure", rel, "skill folder has no SKILL.md")]
    try:
        fields = parse_frontmatter(path.read_text(encoding="utf-8"))
    except FrontmatterError as e:
        return [Finding("structure", rel, str(e))]
    findings = []
    name = fields.get("name", "")
    if name != skill_dir.name:
        findings.append(Finding("structure", rel,
                                f"'name' is {name!r} but the folder is {skill_dir.name!r}"))
    if not NAME_RE.match(name) or len(name) > 64:
        findings.append(Finding(
            "structure", rel,
            "'name' must be lower-case letters, numbers and hyphens, 64 characters at most"))
    description = fields.get("description", "")
    if not description:
        findings.append(Finding("structure", rel, "'description' is required"))
    elif len(description) > 1024:
        findings.append(Finding("structure", rel, "'description' must be 1024 characters or fewer"))
    return findings
```

- [ ] **Step 9: Run all tests**

Run: `PYTHONPATH=scripts python3 -m unittest discover -s tests -v`
Expected: 22 tests, OK

- [ ] **Step 10: Commit**

```bash
git add scripts/ivo_skills tests
git commit -m "Add structure checks for marketplace, plugin and skill files" -m "<trailer lines>"
```

---

### Task 2: Patient data scanner

**Files:**
- Create: `scripts/ivo_skills/pii.py`
- Test: `tests/test_pii.py`

**Interfaces:**
- Consumes: `Finding` (Task 1)
- Produces:
  - `nhs_number_is_valid(digits: str) -> bool`
  - `scan_text(text: str, rel: str, allowed: frozenset[str] | set[str] = frozenset()) -> list[Finding]`
  - `load_allowlist(root: Path) -> tuple[set[str], list[Finding]]`
  - `scan_tree(root: Path) -> list[Finding]`
  - constant `ALLOWLIST_FILE = ".pii-allowlist"`

- [ ] **Step 1: Write the failing tests**

`tests/test_pii.py`:

```python
import tempfile
import unittest
from pathlib import Path

from ivo_skills.pii import nhs_number_is_valid, scan_text, scan_tree
from tests.helpers import write


def synthetic_nhs_number(prefix: str = "999000001") -> str:
    """Build a number that passes the NHS check digit, from a 9-digit prefix.

    Generated at test time so no NHS-number-shaped value is stored in the repo.
    """
    for p in range(int(prefix), int(prefix) + 100):
        stem = f"{p:09d}"
        total = sum(int(d) * w for d, w in zip(stem, range(10, 1, -1)))
        check = (11 - total % 11) % 11
        if check != 10:
            return stem + str(check)
    raise AssertionError("no valid number found")


def failing_nhs_number() -> str:
    good = synthetic_nhs_number()
    return good[:9] + str((int(good[9]) + 1) % 10)


class NhsNumberTest(unittest.TestCase):
    def test_valid_check_digit(self):
        self.assertTrue(nhs_number_is_valid(synthetic_nhs_number()))

    def test_wrong_check_digit(self):
        self.assertFalse(nhs_number_is_valid(failing_nhs_number()))

    def test_wrong_length(self):
        self.assertFalse(nhs_number_is_valid("12345"))


class ScanTextTest(unittest.TestCase):
    def checks(self, text, allowed=frozenset()):
        return [f.message for f in scan_text(text, "file.md", allowed)]

    def test_plain_nhs_number(self):
        self.assertEqual(self.checks(f"Patient {synthetic_nhs_number()} seen"),
                         ["possible NHS number (passes the check digit)"])

    def test_spaced_nhs_number(self):
        n = synthetic_nhs_number()
        self.assertEqual(len(self.checks(f"{n[:3]} {n[3:6]} {n[6:]}")), 1)

    def test_ten_digits_failing_check_digit_is_ignored(self):
        self.assertEqual(self.checks(failing_nhs_number()), [])

    def test_hex_hashes_are_ignored(self):
        n = synthetic_nhs_number()
        text = f'"sha": "{n}abcdef{n}0123456789abcdef0123", "sha256": "ff{n}ee"'
        self.assertEqual(self.checks(text), [])

    def test_message_does_not_contain_the_value(self):
        n = synthetic_nhs_number()
        findings = scan_text(f"id {n}", "file.md")
        self.assertNotIn(n, str(findings[0]))
        self.assertEqual(findings[0].line, 1)

    def test_allowlisted_value(self):
        n = synthetic_nhs_number()
        self.assertEqual(self.checks(f"id {n}", {n}), [])

    def test_email_outside_example_domains(self):
        self.assertEqual(self.checks("contact jane.smith@gmail.com"),
                         ["email address outside the allowed example domains"])

    def test_example_emails_are_allowed(self):
        self.assertEqual(self.checks("a@example.com b@team.example.org c@trust.example.nhs.uk"), [])

    def test_npm_package_versions_are_not_emails(self):
        self.assertEqual(self.checks("npx -y @anthropic-ai/claude-code@2.1.282 and skills@latest"), [])

    def test_mobile_number(self):
        self.assertEqual(self.checks("call 07123 456789"),
                         ["UK phone number outside the Ofcom drama ranges"])

    def test_international_format(self):
        self.assertEqual(len(self.checks("+44 (0)161 234 5678")), 1)

    def test_drama_numbers_are_allowed(self):
        self.assertEqual(self.checks("07700 900123, 020 7946 0123, 0161 496 0000"), [])

    def test_dates_and_versions_are_ignored(self):
        self.assertEqual(self.checks("2026-09-25 version 0.1.0 and 1234567"), [])


class ScanTreeTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_reports_relative_path_and_line(self):
        write(self.root, "docs/a.md", "fine\nemail bob@gmail.com\n")
        findings = scan_tree(self.root)
        self.assertEqual([(f.path, f.line) for f in findings], [("docs/a.md", 2)])

    def test_skips_git_directory_and_binary_files(self):
        write(self.root, ".git/config", "bob@gmail.com")
        (self.root / "image.png").write_bytes(b"\xff\xfe\x00bob@gmail.com")
        self.assertEqual(scan_tree(self.root), [])

    def test_allowlist_file_with_reasons(self):
        write(self.root, "a.md", "owner bob@gmail.com")
        write(self.root, ".pii-allowlist", "bob@gmail.com # public maintainer address\n")
        self.assertEqual(scan_tree(self.root), [])

    def test_allowlist_entry_without_reason(self):
        write(self.root, ".pii-allowlist", "bob@gmail.com\n")
        self.assertEqual([f.message for f in scan_tree(self.root)],
                         ["each entry needs a reason: '<value> # <reason>'"])
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `PYTHONPATH=scripts python3 -m unittest tests.test_pii -v`
Expected: ERROR, `No module named 'ivo_skills.pii'`

- [ ] **Step 3: Implement `pii.py`**

`scripts/ivo_skills/pii.py`:

```python
"""Scan files for values that could identify a patient.

Messages never include the matched value, so CI logs cannot leak it.
"""
import os
import re
from pathlib import Path

from .findings import Finding

ALLOWLIST_FILE = ".pii-allowlist"
EXCLUDED_DIRS = {".git", "__pycache__", "node_modules"}

NHS_RE = re.compile(r"(?<![0-9A-Za-z])(\d{3})([ -]?)(\d{3})\2(\d{4})(?![0-9A-Za-z])")
EMAIL_RE = re.compile(r"(?<![\w.+-])[\w.+-]+@((?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,})(?![\w-])")
PHONE_RE = re.compile(r"(?<![\w+])(?:\+44[ -]?(?:\(0\)[ -]?)?|0)[127]\d(?:[ -]?\d){8}(?!\w)")

ALLOWED_EMAIL_DOMAINS = ("example.com", "example.org", "example.net", "example.nhs.uk")

# Ofcom numbers reserved for TV and radio drama, in national format.
# Source: https://www.ofcom.org.uk/phones-and-broadband/phone-numbers/numbers-for-drama
DRAMA_PREFIXES = (
    "07700900", "02079460", "01134960", "01144960", "01154960", "01174960",
    "01184960", "01214960", "01314960", "01414960", "01514960", "01614960",
    "02890180", "02920180", "01632960",
)


def nhs_number_is_valid(digits: str) -> bool:
    """Modulus 11 check digit, as defined in the NHS Data Model and Dictionary."""
    if len(digits) != 10 or not digits.isdigit():
        return False
    total = sum(int(d) * w for d, w in zip(digits[:9], range(10, 1, -1)))
    check = 11 - total % 11
    if check == 11:
        check = 0
    return check != 10 and check == int(digits[9])


def _national(phone: str) -> str:
    digits = re.sub(r"\D", "", phone.replace("(0)", ""))
    return "0" + digits[2:] if phone.startswith("+44") else digits


def _email_allowed(domain: str) -> bool:
    domain = domain.lower()
    return any(domain == d or domain.endswith("." + d) for d in ALLOWED_EMAIL_DOMAINS)


def scan_text(text: str, rel: str, allowed=frozenset()) -> list[Finding]:
    findings = []
    for n, line in enumerate(text.splitlines(), 1):
        for m in NHS_RE.finditer(line):
            if m.group(0) in allowed:
                continue
            if nhs_number_is_valid(m.group(1) + m.group(3) + m.group(4)):
                findings.append(Finding("pii", rel, "possible NHS number (passes the check digit)", n))
        for m in EMAIL_RE.finditer(line):
            if m.group(0) not in allowed and not _email_allowed(m.group(1)):
                findings.append(Finding("pii", rel, "email address outside the allowed example domains", n))
        for m in PHONE_RE.finditer(line):
            if m.group(0) not in allowed and not _national(m.group(0)).startswith(DRAMA_PREFIXES):
                findings.append(Finding("pii", rel, "UK phone number outside the Ofcom drama ranges", n))
    return findings


def load_allowlist(root: Path) -> tuple[set[str], list[Finding]]:
    path = root / ALLOWLIST_FILE
    if not path.is_file():
        return set(), []
    allowed, findings = set(), []
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        value, sep, reason = raw.partition(" # ")
        if not sep or not reason.strip():
            findings.append(Finding("pii", ALLOWLIST_FILE,
                                    "each entry needs a reason: '<value> # <reason>'", n))
            continue
        allowed.add(value.strip())
    return allowed, findings


def scan_tree(root: Path) -> list[Finding]:
    allowed, findings = load_allowlist(root)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDED_DIRS)
        for filename in sorted(filenames):
            path = Path(dirpath) / filename
            rel = path.relative_to(root).as_posix()
            if rel == ALLOWLIST_FILE or path.is_symlink():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            findings += scan_text(text, rel, allowed)
    return findings
```

- [ ] **Step 4: Run the tests**

Run: `PYTHONPATH=scripts python3 -m unittest tests.test_pii -v`
Expected: 20 tests, OK. If `test_hex_hashes_are_ignored` fails, fix the lookarounds in `NHS_RE` and do not weaken the test.

- [ ] **Step 5: Commit**

```bash
git add scripts/ivo_skills/pii.py tests/test_pii.py
git commit -m "Add patient data scanner for NHS numbers, emails and phone numbers" -m "<trailer lines>"
```

---

### Task 3: External skills lock check

**Files:**
- Create: `scripts/ivo_skills/external.py`
- Test: `tests/test_external.py`

**Interfaces:**
- Consumes: `Finding`, and `SHA_RE` and `NAME_RE` from `structure.py`
- Produces:
  - `LOCK_FILE = "external-skills.lock.json"`, `SKILLS_DIR = Path("plugins/ivo-health/skills")`
  - `hash_tree(folder: Path) -> dict[str, str]` (POSIX relative path to sha256 hex)
  - `load_lock(root: Path) -> dict` (returns `{"skills": {}}` when there is no file)
  - `save_lock(root: Path, lock: dict) -> None` (2-space indent, sorted keys, trailing newline)
  - `check_external(root: Path) -> list[Finding]`

Lock entry fields: `repo`, `path`, `commit`, `licence`, `requires` (list), `sha256` (dict), `reviewed_by`, `reviewed_on` (`YYYY-MM-DD`).

- [ ] **Step 1: Write the failing tests**

`tests/test_external.py`:

```python
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
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `PYTHONPATH=scripts python3 -m unittest tests.test_external -v`
Expected: ERROR, `No module named 'ivo_skills.external'`

- [ ] **Step 3: Implement `external.py`**

`scripts/ivo_skills/external.py`:

```python
"""Check that copied external skills match external-skills.lock.json exactly."""
import hashlib
import json
import re
from pathlib import Path

from .findings import Finding
from .structure import NAME_RE, SHA_RE

LOCK_FILE = "external-skills.lock.json"
SKILLS_DIR = Path("plugins/ivo-health/skills")
REQUIRED = ("repo", "path", "commit", "licence", "sha256", "reviewed_by", "reviewed_on")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def hash_tree(folder: Path) -> dict[str, str]:
    return {
        p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(folder.rglob("*")) if p.is_file()
    }


def load_lock(root: Path) -> dict:
    path = root / LOCK_FILE
    if not path.is_file():
        return {"skills": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def save_lock(root: Path, lock: dict) -> None:
    text = json.dumps(lock, indent=2, sort_keys=True) + "\n"
    (root / LOCK_FILE).write_text(text, encoding="utf-8")


def check_external(root: Path) -> list[Finding]:
    if not (root / LOCK_FILE).is_file():
        return []
    try:
        lock = load_lock(root)
    except json.JSONDecodeError as e:
        return [Finding("external", LOCK_FILE, f"invalid JSON: {e.msg}", e.lineno)]
    findings: list[Finding] = []
    for name, entry in sorted(lock.get("skills", {}).items()):
        if not NAME_RE.match(name):
            findings.append(Finding("external", LOCK_FILE, f"{name!r} is not a valid skill name"))
            continue
        missing = [k for k in REQUIRED if not entry.get(k)]
        if missing:
            findings.append(Finding("external", LOCK_FILE, f"{name}: missing {', '.join(missing)}"))
            continue
        if not SHA_RE.match(entry["commit"]):
            findings.append(Finding("external", LOCK_FILE,
                                    f"{name}: 'commit' must be a full 40-character sha"))
        if not DATE_RE.match(entry["reviewed_on"]):
            findings.append(Finding("external", LOCK_FILE, f"{name}: 'reviewed_on' must be YYYY-MM-DD"))
        findings += _check_files(root, name, entry["sha256"])
        for required in entry.get("requires", []):
            if not (root / SKILLS_DIR / required / "SKILL.md").is_file():
                findings.append(Finding("external", (SKILLS_DIR / name).as_posix(),
                                        f"{name} requires {required!r}, which is missing"))
    return findings


def _check_files(root: Path, name: str, expected: dict) -> list[Finding]:
    folder = root / SKILLS_DIR / name
    rel = (SKILLS_DIR / name).as_posix()
    if not folder.is_dir():
        return [Finding("external", rel, "copied skill folder is missing")]
    actual = hash_tree(folder)
    findings = []
    for f in sorted(set(actual) | set(expected)):
        path = f"{rel}/{f}"
        if f not in actual:
            findings.append(Finding("external", path, "file listed in the lock file is missing"))
        elif f not in expected:
            findings.append(Finding("external", path, "file is not in the lock file"))
        elif actual[f] != expected[f]:
            findings.append(Finding("external", path,
                                    "file has been changed since it was copied; "
                                    "copied skills must not be edited"))
    return findings
```

- [ ] **Step 4: Run the tests**

Run: `PYTHONPATH=scripts python3 -m unittest tests.test_external -v`
Expected: 10 tests, OK

- [ ] **Step 5: Commit**

```bash
git add scripts/ivo_skills/external.py tests/test_external.py
git commit -m "Add lock file check for copied external skills" -m "<trailer lines>"
```

---

### Task 4: Version bump check

**Files:**
- Create: `scripts/ivo_skills/version.py`
- Test: `tests/test_version.py`

**Interfaces:**
- Consumes: `Finding`
- Produces:
  - `PLUGIN_DIR = "plugins/ivo-health"`, `MANIFEST = "plugins/ivo-health/.claude-plugin/plugin.json"`
  - `parse_semver(value: str) -> tuple[int, int, int]` (raises `ValueError`)
  - `check_version_bump(root: Path, base_ref: str) -> list[Finding]`

- [ ] **Step 1: Write the failing tests**

`tests/test_version.py`:

```python
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
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `PYTHONPATH=scripts python3 -m unittest tests.test_version -v`
Expected: ERROR, `No module named 'ivo_skills.version'`

- [ ] **Step 3: Implement `version.py`**

`scripts/ivo_skills/version.py`:

```python
"""Require a plugin version bump when the plugin changes.

The Claude organisation sync only picks up changes merged with a version bump.
"""
import json
import subprocess
from pathlib import Path

from .findings import Finding

PLUGIN_DIR = "plugins/ivo-health"
MANIFEST = f"{PLUGIN_DIR}/.claude-plugin/plugin.json"


def parse_semver(value: str) -> tuple[int, int, int]:
    parts = value.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        raise ValueError(f"not a MAJOR.MINOR.PATCH version: {value!r}")
    return tuple(int(p) for p in parts)


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)


def check_version_bump(root: Path, base_ref: str) -> list[Finding]:
    diff = _git(root, "diff", "--name-only", f"{base_ref}...HEAD", "--", PLUGIN_DIR)
    if diff.returncode != 0:
        return [Finding("version", MANIFEST, f"could not compare with {base_ref}: {diff.stderr.strip()}")]
    if not diff.stdout.strip():
        return []
    base = _git(root, "show", f"{base_ref}:{MANIFEST}")
    if base.returncode != 0:
        return []  # The plugin is new on this branch.
    try:
        old = parse_semver(json.loads(base.stdout)["version"])
        new = parse_semver(json.loads((root / MANIFEST).read_text(encoding="utf-8"))["version"])
    except (ValueError, KeyError, OSError) as e:
        return [Finding("version", MANIFEST, f"could not read version: {e}")]
    if new <= old:
        return [Finding(
            "version", MANIFEST,
            f"files under {PLUGIN_DIR} changed, so 'version' must be higher than "
            f"{'.'.join(map(str, old))} (the Claude organisation sync only picks up version bumps)")]
    return []
```

- [ ] **Step 4: Run the tests**

Run: `PYTHONPATH=scripts python3 -m unittest tests.test_version -v`
Expected: 8 tests, OK

- [ ] **Step 5: Commit**

```bash
git add scripts/ivo_skills/version.py tests/test_version.py
git commit -m "Add plugin version bump check" -m "<trailer lines>"
```

---

### Task 5: `check-skills` command, marketplace scaffold and CI checks

**Files:**
- Create: `scripts/ivo_skills/cli.py`
- Create: `scripts/check-skills` (executable)
- Create: `.claude-plugin/marketplace.json`
- Create: `plugins/ivo-health/.claude-plugin/plugin.json`
- Create: `.github/workflows/checks.yml`
- Create: `.gitignore`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `check_structure`, `scan_tree`, `check_external`, `check_version_bump`
- Produces: `check_skills_main(argv: list[str] | None = None) -> int` in `cli.py` (0 when clean, 1 when there are findings). Arguments: `--root PATH` (default: repo root) and `--base-ref REF` (optional).

- [ ] **Step 1: Write the failing CLI test**

`tests/test_cli.py`:

```python
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
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `PYTHONPATH=scripts python3 -m unittest tests.test_cli -v`
Expected: ERROR, `No module named 'ivo_skills.cli'`

- [ ] **Step 3: Implement the CLI and entry script**

`scripts/ivo_skills/cli.py`:

```python
import argparse
from pathlib import Path

from .external import check_external
from .pii import scan_tree
from .structure import check_structure
from .version import check_version_bump

REPO_ROOT = Path(__file__).resolve().parents[2]


def check_skills_main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Check the Ivo Health skills repository.")
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--base-ref", help="git ref to compare the plugin version with, for example origin/main")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    findings = check_structure(root) + scan_tree(root) + check_external(root)
    if args.base_ref:
        findings += check_version_bump(root, args.base_ref)
    for finding in findings:
        print(finding)
    print(f"{len(findings)} problem(s) found" if findings else "All checks passed")
    return 1 if findings else 0
```

`scripts/check-skills`:

```python
#!/usr/bin/env python3
"""Run all repository checks. Usage: scripts/check-skills [--base-ref origin/main]"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ivo_skills.cli import check_skills_main  # noqa: E402

sys.exit(check_skills_main())
```

Run: `chmod +x scripts/check-skills`

- [ ] **Step 4: Create the marketplace and plugin manifests**

`.claude-plugin/marketplace.json`:

```json
{
  "name": "ivo-health",
  "description": "Ivo Health's approved AI skills, plus pinned external skills.",
  "owner": {
    "name": "Ivo Health"
  },
  "plugins": [
    {
      "name": "ivo-health",
      "source": "./plugins/ivo-health",
      "description": "Ivo Health skills: patient data protection, NHS writing style, clinical safety, and reviewed copies of chosen external skills."
    },
    {
      "name": "superpowers",
      "source": {
        "source": "github",
        "repo": "obra/superpowers",
        "sha": "5bf4e78011075bcfc0dc295f0724994cd123ee71"
      },
      "description": "Superpowers by Jesse Vincent (MIT), pinned to v6.4.1 after review."
    }
  ]
}
```

`plugins/ivo-health/.claude-plugin/plugin.json`:

```json
{
  "name": "ivo-health",
  "version": "0.1.0",
  "description": "Ivo Health's approved AI skills.",
  "author": {
    "name": "Ivo Health"
  },
  "repository": "https://github.com/Ivo-Health/skills",
  "license": "UNLICENSED"
}
```

Create `plugins/ivo-health/skills/.gitkeep` (empty) so the folder exists until Task 6.

`.pii-allowlist` (the scanner's test fixtures and this plan contain made-up values that must be flagged in unit tests but not in the real repository scan):

```
# <exact value> # <reason>
bob@gmail.com # made-up address used in scanner tests and the implementation plan
jane.smith@gmail.com # made-up address used in scanner tests and the implementation plan
07123 456789 # made-up number used in scanner tests and the implementation plan
+44 (0)161 234 5678 # made-up number used in scanner tests and the implementation plan
noreply@anthropic.com # commit trailer address quoted in the implementation plan
```

`.gitignore`:

```
__pycache__/
*.pyc
report.md
```

- [ ] **Step 5: Run the tests and the command**

Run: `PYTHONPATH=scripts python3 -m unittest discover -s tests -v`
Expected: all tests OK, including `test_real_repository_passes`

Run: `scripts/check-skills`
Expected: `All checks passed`

Run: `claude plugin validate .`
Expected: last line `✔ Validation passed`. If validation warns about `license` or another field, remove that field. Don't ignore the warning.

- [ ] **Step 6: Add the CI workflow**

`.github/workflows/checks.yml`:

```yaml
name: Checks

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  checks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09 # v5.1.0
        with:
          fetch-depth: 0

      - name: Unit tests
        run: PYTHONPATH=scripts python3 -m unittest discover -s tests -v

      - name: Skill checks
        env:
          EVENT_NAME: ${{ github.event_name }}
          BASE_REF: ${{ github.base_ref }}
        run: |
          if [ "$EVENT_NAME" = "pull_request" ]; then
            python3 scripts/check-skills --base-ref "origin/$BASE_REF"
          else
            python3 scripts/check-skills
          fi

      - name: Claude plugin validation
        run: npx -y @anthropic-ai/claude-code@2.1.282 plugin validate .

      - name: Secret scan (gitleaks)
        env:
          GITLEAKS_VERSION: 8.30.1
        run: |
          base="https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}"
          curl -sSfLO "$base/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz"
          curl -sSfLO "$base/gitleaks_${GITLEAKS_VERSION}_checksums.txt"
          sha256sum --check --ignore-missing "gitleaks_${GITLEAKS_VERSION}_checksums.txt"
          tar -xzf "gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz" gitleaks
          ./gitleaks git --redact --verbose .
```

Run locally, if the network allows: `curl -sSfI https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/gitleaks_8.30.1_checksums.txt`
Expected: HTTP 200 or a 302 redirect. If you get 404, check the asset names on the release page and correct both names.

- [ ] **Step 7: Commit**

```bash
git add scripts tests .claude-plugin plugins .github .gitignore .pii-allowlist
git commit -m "Add check-skills command, marketplace manifests and CI checks" -m "<trailer lines>"
```

---

### Task 6: `sync-external` and importing Matt Pocock's grilling skills

**Files:**
- Create: `scripts/ivo_skills/sync.py`
- Create: `scripts/sync-external` (executable)
- Create: `external-skills.lock.json` (generated)
- Create: `plugins/ivo-health/skills/grill-me/` and `plugins/ivo-health/skills/grilling/` (copied by the script)
- Create: `plugins/ivo-health/THIRD_PARTY_NOTICES.md`
- Modify: `plugins/ivo-health/.claude-plugin/plugin.json` (version `0.1.0` → `0.2.0`)
- Delete: `plugins/ivo-health/skills/.gitkeep`
- Test: `tests/test_sync.py`

**Interfaces:**
- Consumes: `hash_tree`, `load_lock`, `save_lock`, `SKILLS_DIR`, `NAME_RE`
- Produces:
  - `class SyncError(Exception)`
  - `fetch_skill(repo: str, commit: str, path: str, dest: Path) -> tuple[str, dict[str, str]]` (full commit sha and file hashes)
  - `sync_skill(root: Path, name: str, commit: str, reviewed_by: str, repo: str | None = None, path: str | None = None, licence: str | None = None, requires: list[str] | None = None, today: date | None = None) -> dict` (the lock entry)
  - `sync_main(argv: list[str] | None = None) -> int`

- [ ] **Step 1: Write the failing tests**

`tests/test_sync.py`:

```python
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

    def test_rejects_folder_without_skill_md(self):
        with self.assertRaisesRegex(SyncError, "has no SKILL.md"):
            self.add(path="skills")

    def test_unknown_commit(self):
        with self.assertRaises(SyncError):
            sync_skill(self.root, "grilling", "0" * 40, repo=str(self.upstream),
                       path="skills/grilling", licence="MIT", reviewed_by="R")
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `PYTHONPATH=scripts python3 -m unittest tests.test_sync -v`
Expected: ERROR, `No module named 'ivo_skills.sync'`

- [ ] **Step 3: Implement `sync.py` and the entry script**

`scripts/ivo_skills/sync.py`:

```python
"""Copy an external skill, unmodified, at a pinned commit, and record it in the lock file."""
import argparse
import shutil
import subprocess
import tempfile
from datetime import date
from pathlib import Path, PurePosixPath

from .external import SKILLS_DIR, hash_tree, load_lock, save_lock
from .structure import NAME_RE

REPO_ROOT = Path(__file__).resolve().parents[2]


class SyncError(Exception):
    pass


def _run(*args: str, cwd=None) -> str:
    result = subprocess.run(list(args), cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise SyncError(f"{' '.join(args[:3])} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def fetch_skill(repo: str, commit: str, path: str, dest: Path) -> tuple[str, dict[str, str]]:
    rel = PurePosixPath(path)
    if rel.is_absolute() or ".." in rel.parts:
        raise SyncError(f"path {path!r} must stay inside the upstream repository")
    with tempfile.TemporaryDirectory() as tmp:
        _run("git", "clone", "--quiet", repo, tmp)
        full = _run("git", "rev-parse", "--verify", f"{commit}^{{commit}}", cwd=tmp)
        _run("git", "checkout", "--quiet", full, cwd=tmp)
        src = Path(tmp) / rel
        if not (src / "SKILL.md").is_file():
            raise SyncError(f"{path} at {full[:12]} has no SKILL.md")
        if src.is_symlink() or any(p.is_symlink() for p in src.rglob("*")):
            raise SyncError(f"{path} at {full[:12]} contains a symlink; refusing to copy it")
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest)
    return full, hash_tree(dest)


def sync_skill(root: Path, name: str, commit: str, reviewed_by: str, repo=None, path=None,
               licence=None, requires=None, today=None) -> dict:
    if not NAME_RE.match(name):
        raise SyncError(f"{name!r} is not a valid skill name")
    lock = load_lock(root)
    entry = dict(lock["skills"].get(name, {}))
    repo = repo or entry.get("repo")
    path = path or entry.get("path")
    licence = licence or entry.get("licence")
    if not (repo and path and licence):
        raise SyncError(f"{name} is not in the lock file yet; give --repo, --path and --licence")
    full, hashes = fetch_skill(repo, commit, path, root / SKILLS_DIR / name)
    entry.update(repo=repo, path=path, licence=licence, commit=full, sha256=hashes,
                 reviewed_by=reviewed_by, reviewed_on=(today or date.today()).isoformat())
    if requires is not None:
        entry["requires"] = requires
    entry.setdefault("requires", [])
    lock["skills"][name] = entry
    save_lock(root, lock)
    return entry


def sync_main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Copy an external skill at a reviewed commit and record it in external-skills.lock.json.")
    parser.add_argument("name", help="skill folder name, for example grill-me")
    parser.add_argument("--commit", required=True, help="commit sha or tag you have reviewed")
    parser.add_argument("--reviewed-by", required=True, help="full name of the person who reviewed the upstream diff")
    parser.add_argument("--repo", help="upstream git URL (needed for a new skill)")
    parser.add_argument("--path", help="skill folder inside the upstream repo (needed for a new skill)")
    parser.add_argument("--licence", help="upstream licence, for example MIT (needed for a new skill)")
    parser.add_argument("--requires", nargs="*", help="other skills this one calls")
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    args = parser.parse_args(argv)
    try:
        entry = sync_skill(args.root.resolve(), args.name, args.commit, args.reviewed_by,
                           args.repo, args.path, args.licence, args.requires)
    except SyncError as e:
        print(f"sync-external: {e}")
        return 1
    print(f"Copied {args.name} at {entry['commit']}. Now bump the plugin version and open a PR.")
    return 0
```

`scripts/sync-external`:

```python
#!/usr/bin/env python3
"""Copy an external skill at a reviewed commit. See docs/reviewing-external-updates.md."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ivo_skills.sync import sync_main  # noqa: E402

sys.exit(sync_main())
```

Run: `chmod +x scripts/sync-external`

- [ ] **Step 4: Run the tests**

Run: `PYTHONPATH=scripts python3 -m unittest tests.test_sync -v`
Expected: 9 tests, OK

- [ ] **Step 5: Import the two skills**

Use the reviewer name the user gives, for example `Laurence Bargery`:

```bash
scripts/sync-external grilling --commit c55ee46073ed923f86ce59a5eb3b6d895095d1b7 \
  --repo https://github.com/mattpocock/skills --path skills/productivity/grilling \
  --licence MIT --reviewed-by "Laurence Bargery"
scripts/sync-external grill-me --commit c55ee46073ed923f86ce59a5eb3b6d895095d1b7 \
  --repo https://github.com/mattpocock/skills --path skills/productivity/grill-me \
  --licence MIT --requires grilling --reviewed-by "Laurence Bargery"
rm plugins/ivo-health/skills/.gitkeep
```

Expected: two `Copied ...` lines. Each folder has `SKILL.md` and `agents/openai.yaml`.

- [ ] **Step 6: Add licence notices and bump the version**

Create `plugins/ivo-health/THIRD_PARTY_NOTICES.md` using the licence text at the pinned commit:

```bash
{
  printf '# Third-party notices\n\n'
  printf 'The skills `grill-me` and `grilling` are copied unmodified from\n'
  printf 'https://github.com/mattpocock/skills at commit c55ee46073ed923f86ce59a5eb3b6d895095d1b7.\n'
  printf 'They are used under the MIT licence below.\n\n```\n'
  curl -sSf https://raw.githubusercontent.com/mattpocock/skills/c55ee46073ed923f86ce59a5eb3b6d895095d1b7/LICENSE
  printf '```\n'
} > plugins/ivo-health/THIRD_PARTY_NOTICES.md
```

In `plugins/ivo-health/.claude-plugin/plugin.json`, change `"version": "0.1.0"` to `"version": "0.2.0"`.

- [ ] **Step 7: Run everything**

Run: `PYTHONPATH=scripts python3 -m unittest discover -s tests -v && scripts/check-skills && claude plugin validate .`
Expected: all tests OK, `All checks passed`, `✔ Validation passed`

- [ ] **Step 8: Commit**

```bash
git add scripts tests external-skills.lock.json plugins
git commit -m "Add sync-external and copy grill-me and grilling from mattpocock/skills" -m "<trailer lines>"
```

---

### Task 7: Starter skills

**Files:**
- Create: `plugins/ivo-health/skills/patient-data-protection/SKILL.md`
- Create: `plugins/ivo-health/skills/nhs-writing-style/SKILL.md`
- Create: `plugins/ivo-health/skills/clinical-safety/SKILL.md`
- Modify: `plugins/ivo-health/.claude-plugin/plugin.json` (version `0.2.0` → `0.3.0`)

**Interfaces:**
- Consumes: the structure and PII checks from `scripts/check-skills` (these files must pass them)

The skill text below is a draft for the team to review. Every source URL must be opened in a browser and confirmed before merge; the design session could not reach them. Correct any rule that the source does not support, and don't add rules without a source.

- [ ] **Step 1: Write `patient-data-protection/SKILL.md`**

```markdown
---
name: patient-data-protection
description: Use when writing or reviewing code, tests, fixtures, logs, commits, tickets, prompts or documents at Ivo Health that could involve patient information, or when someone shares data that might identify a patient. Keeps patient-identifiable information out of code and AI tools.
---

# Patient data protection

Ivo Health builds software for hospital at home teams. Patient-identifiable information must only ever be in the systems approved to hold it. It must never be in our code, our tooling or conversations with AI tools.

## What counts as patient-identifiable

Treat these as identifiable, on their own or combined:

- NHS number, hospital number or any other patient identifier
- name, address, postcode, date of birth, phone number or email address
- photos, scans or free-text clinical notes
- details that could identify someone when combined, such as a rare condition and a small area

If you are not sure, treat it as identifiable.

## Rules

1. Never put real patient information in code, tests, fixtures, seed data, logs, error messages, analytics events, commit messages, branch names, pull requests, tickets or prompts.
2. Use synthetic data only:
   - generate NHS-number-shaped values in code at test time, rather than writing them into files
   - use `example.com` email addresses
   - use Ofcom drama phone numbers, such as 07700 900123
   - use names that are obviously made up
3. Log internal identifiers, such as database IDs, rather than NHS numbers or names. Do not log request or response bodies that may contain patient data.
4. Use the minimum information needed for the task, and be able to say why it is needed (Caldicott Principles 1 to 3).
5. Do not copy production data into development, test or demo environments.

## If someone shares real patient information

1. Stop. Do not repeat the information or write it to any file.
2. Tell them it looks like real patient information and should be removed from the conversation or file.
3. Point them to the incident steps in `SECURITY.md` in the `Ivo-Health/skills` repository.

## When reviewing a change

Check for:

- identifiers in logs
- real-looking data in fixtures
- data sent to third-party services
- new fields that store patient data without a clear purpose

Raise anything you find before the change is merged.

## Sources

- The Caldicott Principles (UK Caldicott Guardian Council and Department of Health and Social Care): https://www.gov.uk/government/publications/the-caldicott-principles
- UK GDPR guidance (Information Commissioner's Office): https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/
- Data Security and Protection Toolkit (NHS England): https://www.dsptoolkit.nhs.uk/
- NHS number format (NHS Data Model and Dictionary): https://www.datadictionary.nhs.uk/attributes/nhs_number.html
- Numbers for drama (Ofcom): https://www.ofcom.org.uk/phones-and-broadband/phone-numbers/numbers-for-drama
```

- [ ] **Step 2: Write `nhs-writing-style/SKILL.md`**

```markdown
---
name: nhs-writing-style
description: Use when writing or reviewing user interface text, help content, documentation, emails or any text that NHS staff or patients will read at Ivo Health. Applies the NHS digital service manual content style.
---

# NHS writing style

Our users are hospital at home teams and their patients. Write so that busy staff can understand text quickly, and so that patients with low health literacy can follow it. Follow the NHS digital service manual. When this skill and the service manual disagree, the service manual is right.

## Principles

- Use plain English. Choose common words, such as "use" not "utilise" and "help" not "facilitate".
- Keep sentences short, ideally under 25 words.
- Use the active voice: "The nurse assigns the visit" not "The visit is assigned by the nurse".
- Address the reader as "you".
- Put the most important information first.
- Be calm and factual. Do not use marketing language, hype or exclamation marks.

## Formatting

- Use sentence case for headings, buttons and labels: "Add a visit" not "Add A Visit".
- Do not use full stops in headings.
- Write "and", not "&".
- Do not use "e.g.", "i.e." or "etc.". Write "for example", "that is" or list the items.
- Write dates as "25 September 2026" and times as "9am" or "5:30pm".
- Make link text describe where the link goes. Never use "click here".
- Use bold sparingly, and never for whole sentences.

## Terms

- Check the NHS A to Z of health writing for how to write medical and NHS terms.
- Explain abbreviations the first time you use them, unless they are well known to the reader.

## Sources

- NHS digital service manual, content guide: https://service-manual.nhs.uk/content
- NHS A to Z of health writing: https://service-manual.nhs.uk/content/a-to-z-of-nhs-health-writing
```

- [ ] **Step 3: Write `clinical-safety/SKILL.md`**

```markdown
---
name: clinical-safety
description: Use when a change at Ivo Health could affect patient care or clinical information, such as what staff see about a patient, alerts, observations, escalation, visit scheduling, task allocation or medication. Also use when an AI tool is asked to make or judge a clinical decision.
---

# Clinical safety

Ivo Health makes health IT for hospital at home teams. As the manufacturer, we must manage clinical risk under DCB0129. The NHS organisations that deploy our software manage their own risk under DCB0160.

## When a change may affect patient safety

Examples:

- showing, hiding or changing clinical information
- alerts, reminders or escalation
- visit scheduling or task allocation
- anything that could cause a delay in care
- data migration or integration with other clinical systems

When a change is like this:

1. Say so clearly, before writing or approving the code.
2. Ask what could go wrong for a patient if the change fails, is misread or is unavailable.
3. Suggest the change is reviewed by our Clinical Safety Officer, and that the hazard log is checked for affected hazards and controls.
4. Suggest tests that show each relevant control works.
5. Do not describe the change as "clinically safe" or "compliant". Only the Clinical Safety Officer can make that judgement.

## AI tools and clinical decisions

AI tools must not make clinical decisions or give clinical advice about real patients. This applies to every skill, including `grill-me` and `grilling`. Question technical, product and business decisions freely, but send clinical questions to a clinician or the Clinical Safety Officer.

## Sources

- DCB0129: Clinical risk management, its application in the manufacture of health IT systems (NHS England): https://digital.nhs.uk/data-and-information/information-standards/governance/latest-activity/standards-and-collections/dcb0129-clinical-risk-management-its-application-in-the-manufacture-of-health-it-systems
- DCB0160: Clinical risk management, its application in the deployment and use of health IT systems (NHS England): https://digital.nhs.uk/data-and-information/information-standards/governance/latest-activity/standards-and-collections/dcb0160-clinical-risk-management-its-application-in-the-deployment-and-use-of-health-it-systems
```

- [ ] **Step 4: Bump the version and run the checks**

Change `plugins/ivo-health/.claude-plugin/plugin.json` `version` to `0.3.0`.

Run: `scripts/check-skills && claude plugin validate .`
Expected: `All checks passed` and `✔ Validation passed`

- [ ] **Step 5: Commit**

```bash
git add plugins/ivo-health
git commit -m "Add patient data protection, NHS writing style and clinical safety skills" -m "<trailer lines>"
```

---

### Task 8: Weekly upstream check

**Files:**
- Create: `scripts/ivo_skills/upstream.py`
- Create: `scripts/check-upstream` (executable)
- Create: `.github/workflows/upstream.yml`
- Test: `tests/test_upstream.py`

**Interfaces:**
- Consumes: `load_lock`, `MARKETPLACE`
- Produces:
  - `class UpstreamError(Exception)`
  - `latest_tag(repo_url: str) -> tuple[str, str] | None` (tag name and peeled commit sha)
  - `path_changed(clone_dir: Path, old: str, new: str, path: str) -> bool`
  - `build_report(root: Path, url_for=github_url) -> str` (empty string when nothing has changed)
  - `github_url(repo: str) -> str` (`"owner/repo"` becomes `"https://github.com/owner/repo"`)
  - `upstream_main(argv: list[str] | None = None) -> int`, with `--output FILE`

- [ ] **Step 1: Write the failing tests**

`tests/test_upstream.py`:

```python
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
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `PYTHONPATH=scripts python3 -m unittest tests.test_upstream -v`
Expected: ERROR, `No module named 'ivo_skills.upstream'`

- [ ] **Step 3: Implement `upstream.py` and the entry script**

`scripts/ivo_skills/upstream.py`:

```python
"""Report external skills whose upstream has moved on since we pinned them."""
import argparse
import json
import re
import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path

from .external import load_lock
from .structure import MARKETPLACE

REPO_ROOT = Path(__file__).resolve().parents[2]
TAG_RE = re.compile(r"^refs/tags/v?(\d+)\.(\d+)\.(\d+)(\^\{\})?$")
INTRO = ("Upstream changes are available for these external skills. Review each diff before "
         "adopting it. See docs/reviewing-external-updates.md.\n\n")


class UpstreamError(Exception):
    pass


def github_url(repo: str) -> str:
    return f"https://github.com/{repo}"


def _git(*args: str, cwd=None) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


def latest_tag(repo_url: str):
    result = _git("ls-remote", "--tags", repo_url)
    if result.returncode != 0:
        raise UpstreamError(f"could not list tags for {repo_url}: {result.stderr.strip()}")
    tags = {}
    for line in result.stdout.splitlines():
        sha, ref = line.split("\t")
        m = TAG_RE.match(ref)
        if not m:
            continue
        version = tuple(int(x) for x in m.groups()[:3])
        name = ref[len("refs/tags/"):].removesuffix("^{}")
        if m.group(4) or version not in tags:  # The peeled line gives the commit sha.
            tags[version] = (name, sha)
    return tags[max(tags)] if tags else None


def path_changed(clone_dir: Path, old: str, new: str, path: str) -> bool:
    result = _git("diff", "--quiet", old, new, "--", path, cwd=clone_dir)
    if result.returncode not in (0, 1):
        raise UpstreamError(f"could not compare {old[:12]} with {new[:12]}: {result.stderr.strip()}")
    return result.returncode == 1


def build_report(root: Path, url_for=github_url) -> str:
    lines = []
    market = json.loads((root / MARKETPLACE).read_text(encoding="utf-8"))
    for entry in market.get("plugins", []):
        source = entry.get("source")
        if not (isinstance(source, dict) and source.get("source") == "github"):
            continue
        url = url_for(source["repo"])
        try:
            latest = latest_tag(url)
        except UpstreamError as e:
            lines.append(f"- **{entry['name']}**: {e}")
            continue
        if latest and latest[1] != source["sha"]:
            lines.append(
                f"- **{entry['name']}** (whole plugin): pinned `{source['sha'][:12]}`, latest release is "
                f"`{latest[0]}` (`{latest[1][:12]}`). Compare: {url}/compare/{source['sha']}...{latest[0]}")

    by_repo = defaultdict(list)
    for name, entry in sorted(load_lock(root).get("skills", {}).items()):
        by_repo[entry["repo"]].append((name, entry))
    for repo, entries in by_repo.items():
        with tempfile.TemporaryDirectory() as tmp:
            if _git("clone", "--quiet", repo, tmp).returncode != 0:
                lines.append(f"- {repo}: could not clone")
                continue
            head = _git("rev-parse", "HEAD", cwd=tmp).stdout.strip()
            for name, entry in entries:
                try:
                    changed = path_changed(Path(tmp), entry["commit"], head, entry["path"])
                except UpstreamError as e:
                    lines.append(f"- **{name}**: {e}")
                    continue
                if changed:
                    lines.append(
                        f"- **{name}** (copied skill): `{entry['path']}` has changed upstream since "
                        f"`{entry['commit'][:12]}`. Compare: {repo}/compare/{entry['commit']}...{head}")
    return INTRO + "\n".join(lines) + "\n" if lines else ""


def upstream_main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Report external skills with upstream changes.")
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--output", type=Path, help="also write the report to this file")
    args = parser.parse_args(argv)
    report = build_report(args.root.resolve())
    print(report or "No upstream changes.")
    if args.output:
        args.output.write_text(report, encoding="utf-8")
    return 0
```

`scripts/check-upstream`:

```python
#!/usr/bin/env python3
"""Report external skills whose upstream has changed. Never changes files."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ivo_skills.upstream import upstream_main  # noqa: E402

sys.exit(upstream_main())
```

Run: `chmod +x scripts/check-upstream`

- [ ] **Step 4: Run the tests**

Run: `PYTHONPATH=scripts python3 -m unittest tests.test_upstream -v`
Expected: 7 tests, OK

- [ ] **Step 5: Try it against the real upstreams**

Run: `scripts/check-upstream`
Expected: either `No upstream changes.` or a list of links. It must not change any files (`git status` shows them clean).

- [ ] **Step 6: Add the weekly workflow**

`.github/workflows/upstream.yml`:

```yaml
name: Upstream skill updates

on:
  schedule:
    - cron: "17 7 * * 1" # Mondays 07:17 UTC
  workflow_dispatch:

permissions:
  contents: read
  issues: write

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09 # v5.1.0

      - name: Check upstream repositories
        run: python3 scripts/check-upstream --output report.md

      - name: Open or update the tracking issue
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          if [ ! -s report.md ]; then
            echo "No upstream changes."
            exit 0
          fi
          title="Upstream skill updates available"
          number=$(gh issue list --state open --search "\"$title\" in:title" --json number --jq '.[0].number // empty')
          if [ -n "$number" ]; then
            gh issue edit "$number" --body-file report.md
          else
            gh issue create --title "$title" --body-file report.md
          fi
```

- [ ] **Step 7: Commit**

```bash
git add scripts tests .github/workflows/upstream.yml
git commit -m "Add weekly check for upstream changes to external skills" -m "<trailer lines>"
```

---

### Task 9: Documentation

**Files:**
- Create: `README.md`, `SECURITY.md`, `CONTRIBUTING.md`, `CHANGELOG.md`
- Create: `docs/install.md`, `docs/adding-a-skill.md`, `docs/reviewing-external-updates.md`

**Interfaces:**
- Consumes: the command names and flags from Tasks 5, 6 and 8, and the plugin and marketplace names

- [ ] **Step 1: Write `README.md`**

```markdown
# Ivo Health skills

The AI skills we use at Ivo Health, in one place. Claude, Claude Code, ChatGPT and Codex all read them from this repository.

## What is here

| Plugin | What it contains | Where it comes from |
|---|---|---|
| `ivo-health` | `patient-data-protection`, `nhs-writing-style`, `clinical-safety`, and unmodified copies of `grill-me` and `grilling` | This repository. Copied skills are listed in `external-skills.lock.json` |
| `superpowers` | Development workflow skills by Jesse Vincent | `obra/superpowers`, pinned in `.claude-plugin/marketplace.json` |

## Getting the skills

- **Claude app and Claude Code:** you do not need to do anything. The organisation syncs this repository.
- **ChatGPT:** you do not need to do anything. The workspace syncs this repository daily.
- **Other set-ups and Codex:** see `docs/install.md`.

## Making changes

- To add or change a skill, see `docs/adding-a-skill.md` and `CONTRIBUTING.md`.
- To adopt a new version of an external skill, see `docs/reviewing-external-updates.md`.
- Before you start, read `SECURITY.md`. This repository must never contain patient data.

## Checks

Run these before you open a pull request:

    PYTHONPATH=scripts python3 -m unittest discover -s tests
    scripts/check-skills --base-ref origin/main
```

- [ ] **Step 2: Write `SECURITY.md`**

```markdown
# Security

## Rules for this repository

- Never add real patient data, credentials, internal hostnames or customer names to any file. Use synthetic examples only.
- Adopt external skills only through a reviewed pull request, pinned to a commit.
- Never edit a copied external skill. Put Ivo Health rules in our own skills instead.
- Skills guide AI tools. They are not a safety control. Real safeguards belong in product code, hooks and our Data Security and Protection Toolkit processes.

## Branch protection

The `main` branch requires a pull request, one approving review and the `Checks` workflow passing.

## If you find patient data or a secret in this repository

1. Do not push further commits that contain it.
2. Tell the data protection lead straight away: [name to be agreed by the team].
3. Follow the Ivo Health incident process.
4. Rotate any exposed secret.
5. Removing data from git history needs a force-push. Agree this with the team first.

## Reporting a problem with a skill

Open an issue in this repository. Do not include patient data in the issue.
```

- [ ] **Step 3: Write `CONTRIBUTING.md` and `CHANGELOG.md`**

`CONTRIBUTING.md`:

```markdown
# Contributing

1. Create a branch from `main`.
2. Make your change. See `docs/adding-a-skill.md` or `docs/reviewing-external-updates.md`.
3. If anything under `plugins/ivo-health/` changed, raise `version` in `plugins/ivo-health/.claude-plugin/plugin.json`:
   - patch for wording fixes
   - minor for new or changed skills
   - major for removed or renamed skills

   The Claude organisation sync only picks up changes that come with a version bump.
4. Add a line to `CHANGELOG.md`.
5. Run the checks in `README.md`.
6. Open a pull request. Another team member must review it.
```

`CHANGELOG.md`:

```markdown
# Changelog

## 0.3.0

- Added `patient-data-protection`, `nhs-writing-style` and `clinical-safety`.

## 0.2.0

- Added unmodified copies of `grill-me` and `grilling` from `mattpocock/skills` at `c55ee46`.

## 0.1.0

- Set up the marketplace, with Superpowers pinned at v6.4.1.
```

- [ ] **Step 4: Write `docs/install.md`**

````markdown
# Installing the skills

## Claude app (web, desktop and Cowork)

An organisation owner sets this up once:

1. Go to Organisation settings, then Plugins.
2. Choose Add plugins, then Sync from GitHub, and select `Ivo-Health/skills`.
3. Turn on Sync automatically from the marketplace menu.
4. Set `ivo-health` and `superpowers` to Required, so they also reach Claude Code for anyone signed in with their Claude account.

If the marketplace shows "Needs attention", choose re-sync from its menu. The first sync failed because the repository was empty.

## Claude Code

If you are signed in with your Ivo Health Claude account, the Required plugins arrive automatically.

Otherwise, run:

    claude plugin marketplace add Ivo-Health/skills
    claude plugin install ivo-health@ivo-health
    claude plugin install superpowers@ivo-health

To make cloud sessions in a product repository load the plugins, add this to that repository's `.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "ivo-health": {
      "source": { "source": "github", "repo": "Ivo-Health/skills" }
    }
  },
  "enabledPlugins": {
    "ivo-health@ivo-health": true,
    "superpowers@ivo-health": true
  }
}
```

The cloud environment needs GitHub access to `Ivo-Health/skills`, because it is private.

## ChatGPT

A workspace admin sets this up once:

1. Open the workspace plugin settings.
2. Import a marketplace from GitHub and select `Ivo-Health/skills`.
3. Daily sync is on by default. Use Sync now for an urgent change.
4. Set installation and access for each plugin. Importing does not give anyone access by itself.

To confirm when first connected, and record the answers here:

- whether ChatGPT loads Superpowers from its GitHub source
- whether the plugins also reach Codex

## Codex

If the ChatGPT workspace plugins do not reach Codex, run this in each project:

    npx skills@latest add Ivo-Health/skills

For Superpowers, follow the Codex instructions in the Superpowers README.
````

- [ ] **Step 5: Write `docs/adding-a-skill.md`**

````markdown
# Adding or changing a skill

1. Create a folder in `plugins/ivo-health/skills/`. Name it in lower case, with words separated by hyphens.
2. Add a `SKILL.md` file:

   ```markdown
   ---
   name: your-skill-name
   description: Use when ... Say exactly when the skill applies, so the AI loads it only when relevant.
   ---

   # Your skill title

   Instructions in plain English.

   ## Sources

   - Name of the source (organisation): link
   ```

3. Cite a source for every rule that comes from guidance or regulation.
4. Use synthetic examples only. See `SECURITY.md`.
5. Bump the plugin version, and follow `CONTRIBUTING.md`.
````

- [ ] **Step 6: Write `docs/reviewing-external-updates.md`**

````markdown
# Reviewing external updates

Each Monday, a workflow checks whether an external skill has changed upstream. If one has, it opens or updates an issue called "Upstream skill updates available", with a compare link for each change. It never changes files.

## To adopt a change

1. Open the compare link and read the whole diff. Look for:
   - new instructions that send data to other services
   - instructions to run scripts
   - changes to how the skill decides when to run
   - anything that conflicts with `SECURITY.md` or our own skills
2. **For a copied skill** (in `external-skills.lock.json`), run:

       scripts/sync-external <skill-name> --commit <reviewed commit> --reviewed-by "<your full name>"

   If a skill now calls another skill, add `--requires <other-skill>`, and copy that skill too.
3. **For Superpowers**, change `sha` in `.claude-plugin/marketplace.json` to the reviewed commit, and update the description with the new version.
4. Bump the plugin version, update `CHANGELOG.md`, and open a pull request. Another team member reviews it.

## To add a new external skill

- **A whole plugin:** add a `github` entry to `.claude-plugin/marketplace.json` with a full `sha`.
- **A single skill:**

      scripts/sync-external <name> --repo <git URL> --path <folder> --licence <licence> --commit <sha> --reviewed-by "<name>"

  Then add its licence to `plugins/ivo-health/THIRD_PARTY_NOTICES.md`.
````

- [ ] **Step 7: Run the checks and commit**

Run: `scripts/check-skills`
Expected: `All checks passed`. The docs contain no real email addresses or phone numbers.

```bash
git add README.md SECURITY.md CONTRIBUTING.md CHANGELOG.md docs/install.md docs/adding-a-skill.md docs/reviewing-external-updates.md
git commit -m "Add README, security, contributing and install documentation" -m "<trailer lines>"
```

---

### Task 10: End-to-end verification and pull request

**Files:**
- Modify: `docs/install.md` (only if a verification step shows the documented command is wrong)

- [ ] **Step 1: Full local check**

Run: `PYTHONPATH=scripts python3 -m unittest discover -s tests -v && scripts/check-skills && claude plugin validate .`
Expected: all tests OK, `All checks passed`, `✔ Validation passed`

- [ ] **Step 2: Install from the local marketplace in a throwaway home directory**

```bash
export SCRATCH_HOME=$(mktemp -d)
HOME=$SCRATCH_HOME claude plugin marketplace add "$PWD"
HOME=$SCRATCH_HOME claude plugin install ivo-health@ivo-health
HOME=$SCRATCH_HOME claude plugin install superpowers@ivo-health
HOME=$SCRATCH_HOME claude plugin details ivo-health
```

Expected:
- Both installs succeed. Superpowers is fetched from GitHub at the pinned sha.
- The details list 5 skills: `clinical-safety`, `grill-me`, `grilling`, `nhs-writing-style` and `patient-data-protection`.

If the environment has no Claude credentials and a step needs them, record which step and continue.

- [ ] **Step 3: Check the Codex installer finds the skills**

```bash
cd "$(mktemp -d)" && git init -q && npx -y skills@1.7.0 add /workspace/skills --help
```

Read the help output for the non-interactive listing flag, then run the listing. Expected: the 5 skills are found.

If they are not found:
- add `.agents/skills/<name>` symlinks pointing to `../../plugins/ivo-health/skills/<name>`
- re-run
- make `check-skills` still pass (`scan_tree` skips symlinks)
- update `docs/install.md`

- [ ] **Step 4: Adversarial self-review of the diff**

Run: `git diff main...HEAD --stat` and read the full diff. Confirm:
- no real names other than team members as reviewers
- no emails or phone numbers
- every workflow action is pinned by sha
- no `${{ }}` expression is used directly inside a `run:` script (they go through `env:`)

- [ ] **Step 5: Push and open a draft PR into `main`**

```bash
git push -u origin claude/vigilant-shannon-7rqxkc
```

Open a draft PR from `claude/vigilant-shannon-7rqxkc` into `main`. Title: "Set up organisation skills marketplace". The body summarises Tasks 1 to 9 and lists the open items from spec section 9.
