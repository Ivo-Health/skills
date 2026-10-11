# Finding hot spots

Code that changes often is where structural problems cost the most. Rank candidates higher when they sit in it.

## 1. Check the history is deep enough

```bash
git rev-parse --is-shallow-repository
git rev-list --count HEAD
```

If the clone is shallow, fetch more history before ranking:

```bash
git fetch --deepen=1000 origin
```

If you cannot fetch, or there are fewer than 200 commits, rank anyway and say in the report header that the ranking
is based on limited history.

## 2. Files that change most

Last 6 months, C# and Razor files only, top 30:

```bash
git log --since="6 months ago" --name-only --pretty=format: -- '*.cs' '*.razor' \
  | grep -v '^$' | grep -v '/Migrations/' | sort | uniq -c | sort -rn | head -30
```

Leave out generated code, migrations and snapshot files. Check the repository's conventions for other generated
folders.

## 3. Files that change together

Pairs of files that often appear in the same commit show hidden coupling. Two files in different modules that always
change together suggest the module boundary is in the wrong place.

```bash
git log --since="6 months ago" --name-only --pretty=format:'--' -- '*.cs' '*.razor' \
  | grep -v '/Migrations/' \
  | awk 'function flush(  i, j, a, b) {
           if (n <= 30) for (i = 1; i <= n; i++) for (j = i + 1; j <= n; j++) {
             a = f[i]; b = f[j]; if (a > b) { a = f[j]; b = f[i] }; c[a " " b]++ }
           n = 0 }
         /^--$/ { flush(); next }
         NF { f[++n] = $0 }
         END { flush(); for (k in c) if (c[k] >= 4) print c[k], k }' \
  | sort -rn | head -20
```

The command skips commits that touch more than 30 files. They are usually renames or formatting and add noise.

## 4. Use the results

- Start exploring from the top 10 to 15 files by change count, and the modules they belong to.
- Note co-change pairs that cross modules. They are evidence for deep-module and domain-model candidates.
- Do not treat churn as a problem on its own. Tests and actively developed features change often for good reasons.
