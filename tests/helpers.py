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


def add_codex(root: Path, version: str = "0.1.0") -> None:
    """Codex marketplace and plugin manifest matching make_repo()."""
    write(root, ".agents/plugins/marketplace.json", json.dumps({
        "name": "ivo-health",
        "plugins": [
            {"name": "ivo-health", "source": "./plugins/ivo-health"},
            {"name": "superpowers", "source": {
                "source": "url", "url": "https://github.com/obra/superpowers.git",
                "sha": "5bf4e78011075bcfc0dc295f0724994cd123ee71"}},
        ],
    }))
    write(root, "plugins/ivo-health/.codex-plugin/plugin.json",
          json.dumps({"name": "ivo-health", "version": version, "skills": "./skills/"}))
