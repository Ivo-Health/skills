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
