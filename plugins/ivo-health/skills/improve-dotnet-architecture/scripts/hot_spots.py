#!/usr/bin/env python3
"""List the C# and Razor files that change most, and the pairs that change together.

Counts follow renames, treat X.razor and X.razor.cs as one file, and leave out tests, migrations, generated code and
files that no longer exist. Prints file paths and counts only.

Usage: python3 hot_spots.py [--repo PATH] [--since "6 months ago"] [--top 30] [--pairs 20] [--max-files 30]
                            [--include-tests]
"""

import argparse
import subprocess
from collections import Counter
from itertools import combinations
from pathlib import Path, PurePosixPath

COMMIT_MARK = "@@commit"
SOURCE_SUFFIXES = (".cs", ".razor")
GENERATED = ("/Migrations/", ".Designer.cs", ".g.cs", "ModelSnapshot.cs")


def _is_test(path: str) -> bool:
    parts = PurePosixPath(path).parts
    return any(p.endswith(".Tests") or p.lower() in ("test", "tests") for p in parts[:-1]) or path.endswith("Tests.cs")


def _key(path: str) -> str:
    """X.razor.cs is the code-behind of X.razor, so count them as one file."""
    return path[: -len(".cs")] if path.endswith(".razor.cs") else path


def _exists(repo: Path, key: str) -> bool:
    return (repo / key).exists() or (key.endswith(".razor") and (repo / (key + ".cs")).exists())


def _wanted(repo: Path, key: str, include_tests: bool) -> bool:
    if not key.endswith(SOURCE_SUFFIXES) or any(g in "/" + key for g in GENERATED):
        return False
    if not include_tests and _is_test(key):
        return False
    return _exists(repo, key)


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True, encoding="utf-8",
                          errors="replace").stdout


def _commits(top: Path, since: str):
    """Yield the set of paths each commit touched, newest first, with each path mapped to its latest name."""
    log = _git(top, "log", "-M", "--name-status", f"--pretty=format:{COMMIT_MARK}", f"--since={since}")
    renamed_to: dict[str, str] = {}

    def latest(path: str) -> str:
        seen = set()
        while path in renamed_to and path not in seen:
            seen.add(path)
            path = renamed_to[path]
        return path

    files: set[str] = set()
    for line in log.splitlines():
        if line == COMMIT_MARK:
            if files:
                yield files
            files = set()
            continue
        fields = line.split("\t")
        if len(fields) < 2:
            continue
        status, paths = fields[0], fields[1:]
        if status.startswith("R") and len(paths) == 2:
            old, new = paths
            renamed_to[old] = latest(new)
            files.add(latest(new))
        else:
            files.add(latest(paths[-1]))
    if files:
        yield files


def analyse(repo: Path, since: str = "6 months ago", max_files: int = 30, include_tests: bool = False):
    """Return (changes per file, changes per pair of files)."""
    repo = Path(repo).resolve()
    top = Path(_git(repo, "rev-parse", "--show-toplevel").strip())
    # Read the whole history, so files moved into the folder keep their earlier changes, then filter to the folder.
    sub = repo.relative_to(top).as_posix()
    churn: Counter = Counter()
    pairs: Counter = Counter()
    for touched in _commits(top, since):
        keys = sorted({k for k in map(_key, touched)
                       if (sub == "." or k.startswith(sub + "/")) and _wanted(top, k, include_tests)})
        churn.update(keys)
        # Judge commit size on everything it touched, so a repository-wide commit is skipped even in a subfolder.
        if len(touched) <= max_files:
            pairs.update(combinations(keys, 2))
    return dict(churn), dict(pairs)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", default=".", help="repository, or a folder in it to limit the counts to")
    parser.add_argument("--since", default="6 months ago")
    parser.add_argument("--top", type=int, default=30)
    parser.add_argument("--pairs", type=int, default=20)
    parser.add_argument("--max-files", type=int, default=30,
                        help="skip commits touching more files than this when counting pairs")
    parser.add_argument("--include-tests", action="store_true")
    args = parser.parse_args(argv)

    churn, pairs = analyse(Path(args.repo), args.since, args.max_files, args.include_tests)
    print(f"Files that change most (since {args.since})")
    print(f"Total file changes: {sum(churn.values())}")
    for path, count in sorted(churn.items(), key=lambda kv: (-kv[1], kv[0]))[: args.top]:
        print(f"{count:>4}  {path}")
    print()
    print(f"Files that change together (commits of {args.max_files} files or fewer)")
    for (a, b), count in sorted(pairs.items(), key=lambda kv: (-kv[1], kv[0]))[: args.pairs]:
        print(f"{count:>4}  {a}  {b}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
