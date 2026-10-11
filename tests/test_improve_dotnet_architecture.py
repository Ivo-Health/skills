import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "plugins/ivo-health/skills/improve-dotnet-architecture"
URL_RE = re.compile(r"https?://[^\s)`|>\"']+")


def _unpinned_scripts(html: str) -> list[str]:
    """Script URLs, from src attributes or module imports, that are not pinned to an exact version."""
    urls = re.findall(r"""<script[^>]+src\s*=\s*["']([^"']+)["']""", html)
    urls += re.findall(r"""(?:import\s[^;]*?\sfrom\s*|import\s*\(?\s*)["'](https?://[^"']+)["']""", html)
    return [u for u in urls if not re.search(r"@\d+\.\d+\.\d+/|/\d+\.\d+\.\d+/", u)]


def _urls(text: str) -> set[str]:
    return {u.rstrip(".,;:") for u in URL_RE.findall(text)}


class ImproveDotnetArchitectureTest(unittest.TestCase):
    def test_every_cited_url_is_in_sources(self):
        listed = _urls((SKILL / "references/sources.md").read_text(encoding="utf-8"))
        cited = set()
        for path in [SKILL / "SKILL.md", *SKILL.glob("references/*.md")]:
            if path.name != "sources.md":
                cited |= _urls(path.read_text(encoding="utf-8"))
        self.assertEqual(cited - listed, set())

    def test_template_scripts_pin_exact_versions(self):
        html = (SKILL / "references/report-template.html").read_text(encoding="utf-8")
        # Artifact pages render Mermaid themselves, so the template should need no scripts. Any added must be pinned.
        self.assertEqual(_unpinned_scripts(html), [])

    def test_pin_check_catches_unpinned_loaders(self):
        self.assertEqual(len(_unpinned_scripts(
            '<script type="module">import mermaid from "https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.esm.min.mjs"'
            "</script>")), 1)
        self.assertEqual(len(_unpinned_scripts("<script src='https://unpkg.com/mermaid/dist/mermaid.min.js'></script>")), 1)
        self.assertEqual(_unpinned_scripts(
            '<script src="https://cdnjs.cloudflare.com/ajax/libs/mermaid/11.4.1/mermaid.min.js"></script>'), [])

    def test_template_has_dark_mode_tokens(self):
        html = (SKILL / "references/report-template.html").read_text(encoding="utf-8")
        self.assertIn("prefers-color-scheme: dark", html)
        self.assertIn(':root[data-theme="dark"]', html)


if __name__ == "__main__":
    unittest.main()
