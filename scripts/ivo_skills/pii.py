"""Scan files for values that could identify a patient.

Messages never include the matched value, so CI logs cannot leak it.
"""
import os
import re
import subprocess
from pathlib import Path

from .findings import Finding

ALLOWLIST_FILE = ".pii-allowlist"

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


def _files(root: Path) -> list[str]:
    """Every file git would commit (tracked or new, not ignored), or every file outside a git repo."""
    if (root / ".git").exists():
        result = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                                cwd=root, capture_output=True)
        if result.returncode == 0:
            paths = result.stdout.split(b"\0")
            return sorted(set(p.decode("utf-8", "surrogateescape") for p in paths if p))
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        files += [(Path(dirpath) / f).relative_to(root).as_posix() for f in filenames]
    return sorted(files)


def scan_tree(root: Path) -> list[Finding]:
    allowed, findings = load_allowlist(root)
    for rel in _files(root):
        path = root / rel
        if rel == ALLOWLIST_FILE or path.is_symlink() or not path.is_file():
            continue
        data = path.read_bytes()
        if b"\0" in data:
            if rel not in allowed:
                findings.append(Finding(
                    "pii", rel,
                    "binary file cannot be scanned for patient data; remove it or allowlist its path"))
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            text = data.decode("latin-1")  # For example a Windows-1252 CSV export.
        findings += scan_text(text, rel, allowed)
    return findings


HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)")


def scan_history(root: Path, base_ref: str) -> list[Finding]:
    """Scan lines added by each commit since base_ref, so data added and later removed is still caught."""
    allowed, _ = load_allowlist(root)
    result = subprocess.run(
        ["git", "log", "-p", "--no-color", "--unified=0", "--format=commit %H", f"{base_ref}..HEAD"],
        cwd=root, capture_output=True)
    if result.returncode != 0:
        return [Finding("pii", ".", f"could not read commits since {base_ref}")]
    findings, commit, rel, line = [], "", None, 0
    for raw in result.stdout.decode("utf-8", "replace").splitlines():
        if raw.startswith("commit "):
            commit = raw[7:19]
        elif raw.startswith("+++ "):
            rel = raw[6:] if raw.startswith("+++ b/") else None
        elif m := HUNK_RE.match(raw):
            line = int(m.group(1))
        elif raw.startswith("+") and rel and rel != ALLOWLIST_FILE:
            for f in scan_text(raw[1:], f"{rel} (commit {commit})", allowed):
                findings.append(Finding(f.check, f.path, f.message, line))
            line += 1
    return findings
