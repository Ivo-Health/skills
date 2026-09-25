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
