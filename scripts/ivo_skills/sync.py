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
