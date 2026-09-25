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

    def test_skips_local_superpowers_workspace(self):
        write(self.root, ".superpowers/sdd/plan/brief.md", "bob@gmail.com")
        self.assertEqual(scan_tree(self.root), [])

    def test_allowlist_file_with_reasons(self):
        write(self.root, "a.md", "owner bob@gmail.com")
        write(self.root, ".pii-allowlist", "bob@gmail.com # public maintainer address\n")
        self.assertEqual(scan_tree(self.root), [])

    def test_allowlist_entry_without_reason(self):
        write(self.root, ".pii-allowlist", "bob@gmail.com\n")
        self.assertEqual([f.message for f in scan_tree(self.root)],
                         ["each entry needs a reason: '<value> # <reason>'"])
