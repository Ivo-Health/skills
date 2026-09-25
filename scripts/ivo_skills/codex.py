"""Check the Codex marketplace and plugin manifests, which ChatGPT and Codex read.

They sit beside the Claude ones and point at the same skills folder, so names and
versions must match.
"""
import json
from pathlib import Path, PurePosixPath
from typing import Optional

from .findings import Finding
from .structure import MARKETPLACE, SHA_RE

CODEX_MARKETPLACE = Path(".agents/plugins/marketplace.json")


def _load(path: Path, root: Path, findings: list) -> Optional[dict]:
    rel = path.relative_to(root).as_posix()
    if not path.is_file():
        findings.append(Finding("codex", rel, "file is missing"))
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        findings.append(Finding("codex", rel, f"invalid JSON: {e.msg}", e.lineno))
        return None


def _local(url) -> Optional[PurePosixPath]:
    if not isinstance(url, str) or not url.startswith("./"):
        return None
    path = PurePosixPath(url)
    return None if ".." in path.parts else path


def check_codex(root: Path) -> list[Finding]:
    if not (root / CODEX_MARKETPLACE).is_file():
        return []
    findings: list[Finding] = []
    market = _load(root / CODEX_MARKETPLACE, root, findings)
    if market is None:
        return findings
    rel = CODEX_MARKETPLACE.as_posix()
    claude_pins = _claude_pins(root)
    for i, entry in enumerate(market.get("plugins") or []):
        name = entry.get("name") if isinstance(entry, dict) else None
        if not name:
            findings.append(Finding("codex", rel, f"plugins[{i}] is missing 'name'"))
            continue
        source = entry.get("source")
        folder = _local(source)
        if folder is not None:
            findings += _check_plugin(root, root / folder, name)
        elif _pinned_git(source):
            pin = claude_pins.get(name)
            if pin and pin != source["sha"]:
                findings.append(Finding(
                    "codex", rel,
                    f"{name}: pinned to {source['sha'][:12]} but {MARKETPLACE.as_posix()} pins "
                    f"{pin[:12]}; keep them the same"))
        else:
            findings.append(Finding(
                "codex", rel,
                f"{name}: source must be './<folder>' in this repository, or a git url pinned with 'sha'"))
    return findings


def _pinned_git(source) -> bool:
    return (isinstance(source, dict) and source.get("source") == "url"
            and str(source.get("url", "")).startswith("https://")
            and bool(SHA_RE.match(str(source.get("sha", "")))))


def _claude_pins(root: Path) -> dict[str, str]:
    try:
        market = json.loads((root / MARKETPLACE).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}  # Reported by the structure check.
    return {e["name"]: e["source"]["sha"] for e in market.get("plugins", [])
            if isinstance(e.get("source"), dict) and e["source"].get("sha")}


def _check_plugin(root: Path, plugin_dir: Path, name: str) -> list[Finding]:
    findings: list[Finding] = []
    manifest_path = plugin_dir / ".codex-plugin" / "plugin.json"
    manifest = _load(manifest_path, root, findings)
    if manifest is None:
        return findings
    rel = manifest_path.relative_to(root).as_posix()
    if manifest.get("name") != name:
        findings.append(Finding("codex", rel,
                                f"name {manifest.get('name')!r} must match the marketplace entry {name!r}"))
    claude_path = plugin_dir / ".claude-plugin" / "plugin.json"
    if claude_path.is_file():
        claude_version = json.loads(claude_path.read_text(encoding="utf-8")).get("version")
        if manifest.get("version") != claude_version:
            findings.append(Finding(
                "codex", rel,
                f"'version' is {manifest.get('version')!r} but .claude-plugin/plugin.json says "
                f"{claude_version!r}; keep them the same"))
    skills = _local(manifest.get("skills"))
    if skills is None or not (plugin_dir / skills).is_dir():
        findings.append(Finding("codex", rel, "'skills' must point to a folder in the plugin"))
    return findings
