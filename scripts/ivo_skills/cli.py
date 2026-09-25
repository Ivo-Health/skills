import argparse
from pathlib import Path

from .external import check_external
from .pii import scan_tree
from .structure import check_structure
from .version import check_version_bump

REPO_ROOT = Path(__file__).resolve().parents[2]


def check_skills_main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Check the Ivo Health skills repository.")
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--base-ref", help="git ref to compare the plugin version with, for example origin/main")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    findings = check_structure(root) + scan_tree(root) + check_external(root)
    if args.base_ref:
        findings += check_version_bump(root, args.base_ref)
    for finding in findings:
        print(finding)
    print(f"{len(findings)} problem(s) found" if findings else "All checks passed")
    return 1 if findings else 0
