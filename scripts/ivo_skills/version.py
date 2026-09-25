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
