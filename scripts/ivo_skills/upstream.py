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
