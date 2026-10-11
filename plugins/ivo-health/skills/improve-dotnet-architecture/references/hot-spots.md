# Finding hot spots

Code that changes often is where structural problems cost the most. Rank candidates higher when they sit in it.

## 1. Make sure there is enough history

```bash
git rev-parse --is-shallow-repository
git rev-list --count HEAD
git log --reverse --format=%cs | head -1
```

If the clone is shallow, fetch more history once, then count again:

```bash
git fetch --deepen=1000 origin
```

In the report's History field, say:
- how many commits were read
- whether the clone was shallow and was deepened
- if fewer than 200 commits could be read, that the ranking is based on limited history
- if the 6-month window starts before the first commit, that it covers the repository's whole history

## 2. Run the script

From the repository root:

```bash
python3 <skill folder>/scripts/hot_spots.py --since "6 months ago"
```

It prints the 30 files that changed most and the 20 pairs that changed together most often. It:
- follows renames, so a file moved between folders keeps its history
- counts `X.razor` and its code-behind `X.razor.cs` as one file
- leaves out tests, migrations, generated code and files that no longer exist
- skips commits of more than 30 files when counting pairs, because these are usually renames or formatting

Options: `--include-tests`, `--top`, `--pairs`, `--max-files`, `--repo`.

If `python3` is not available, use `git log -M --name-only` and count by hand. Say in the report that you did.

## 3. Use the results

- Start from the top 10 to 15 files and the modules they belong to.
- Pairs that cross modules show hidden coupling. Two files in different modules that change together suggest the
  module boundary is in the wrong place. Use them as evidence for deep-module and domain-model candidates.
- Churn is not a problem on its own. Features under active work change often for good reasons.
- Friction found outside the hot spots still counts. Record it with its evidence, and rank it lower.
