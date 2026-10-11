# improve-dotnet-architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an explicitly invoked skill that runs a periodic architecture health check of an Ivo C# codebase and
publishes a ranked report as a private Artifact page.

**Architecture:** A short `SKILL.md` holds the process and vocabulary; lens detail, sources and the report template sit
in `references/` and are loaded only when needed. A skill-specific unit test keeps citations and pinned library
versions honest. Repo housekeeping (version, changelog, notices) rides with the skill.

**Tech Stack:** Markdown skill files, an HTML template, Python `unittest` for checks.

**Spec:** `docs/superpowers/specs/2026-10-11-improve-dotnet-architecture-design.md`

## Global Constraints

- Skill folder: `plugins/ivo-health/skills/improve-dotnet-architecture/`; `name: improve-dotnet-architecture`.
- Front matter includes `disable-model-invocation: true`; `description` 1024 characters or fewer.
- General .NET guidance only. No Coordinate-specific names (`IIvoContextService`, `Result<T>`, `PrefixedId`) as rules;
  they may appear only as illustrations of "read the repo's own `AGENTS.md`".
- No text copied from Matt Pocock's skill. Credit the idea in `THIRD_PARTY_NOTICES.md`.
- Every URL in the skill also appears in `references/sources.md` with how it was checked. Fowler URLs confirmed only by
  search are fetched again; any that cannot be fetched are removed.
- Report: 5 to 8 candidates; strengths "Strong", "Worth exploring", "Speculative"; flags "Changes a convention",
  "Reopens ADR-NNN", "Clinical logic: needs clinical-safety".
- Test doubles position is marked provisional.
- Plain NHS writing style (load `nhs-writing-style`). Synthetic examples only; no data values.
- Plugin version 0.5.1 → 0.6.0 in both `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json`.

## Review Focus

1. Target repo has no `docs/adr/` or no `AGENTS.md` → skill says so and carries on, does not invent conventions.
2. Shallow clone (few commits) → skill deepens history or states the hot-spot ranking is limited.
3. Fewer than 5 credible candidates → report says so rather than padding with Speculative filler.
4. A candidate whose evidence comes from a test fixture or log → report cites the file and member name only.
5. CDN script in the template without an exact version → test fails.

Lines 1–4 are covered by explicit instructions in `SKILL.md` (Task 1) and checked in the dry run (Task 4); line 5 by
the unit test in Task 3.

---

### Task 1: SKILL.md and repo housekeeping

**Files:**
- Create: `plugins/ivo-health/skills/improve-dotnet-architecture/SKILL.md`
- Modify: `plugins/ivo-health/.claude-plugin/plugin.json`, `plugins/ivo-health/.codex-plugin/plugin.json` (version
  `0.6.0`; Codex `shortDescription` adds "architecture review")
- Modify: `CHANGELOG.md` (new `## 0.6.0` entry), `plugins/ivo-health/THIRD_PARTY_NOTICES.md` (idea credit, no MIT
  text needed since nothing is copied)

**Interfaces:**
- Produces: reference file names used by later tasks — `references/deep-modules.md`, `references/testability.md`,
  `references/domain-model.md`, `references/di-and-lifetimes.md`, `references/hot-spots.md`,
  `references/sources.md`, `references/report-template.html`.

- [ ] **Step 1:** Write `SKILL.md`: front matter; purpose; vocabulary (spec position 5); the eight process steps from the
  spec, including Review Focus lines 1–4; which reference to load at which step; hand-off to `grilling` and
  `writing-plans`; `## Sources` linking to `references/sources.md`. Target under 200 lines.
- [ ] **Step 2:** Bump versions, add changelog and notice.
- [ ] **Step 3:** Run `scripts/check-skills --base-ref origin/main`. Expected: missing reference files are not checked,
  so "All checks passed".
- [ ] **Step 4:** Commit `feat: add improve-dotnet-architecture skill`.

### Task 2: Lens reference files and sources

**Files:**
- Create: the five lens files and `references/sources.md` under the skill folder.

**Interfaces:**
- Consumes: file names from Task 1.
- Produces: `sources.md` as a table `| Source | URL | Checked |`, where Checked is "Read from source repo",
  "Fetched" or "Fetched from published page".

- [ ] **Step 1:** Re-check Fowler URLs from the spec research (Anemic Domain Model, Is High Quality Software Worth the
  Cost, Preparatory Refactoring, Monolith First, Bounded Context, Mocks Aren't Stubs, Unit Test). Remove any that
  cannot be fetched.
- [ ] **Step 2:** Write each lens file: what to look for (C# smell with a short synthetic code sketch), why (cited
  source), the suggested direction, and when not to suggest it. `di-and-lifetimes.md` carries checks 1–4 and 10;
  `testability.md` checks 5 and 8 plus positions 1 (marked provisional) and 3; `domain-model.md` checks 6–7 and
  positions 2 and 4; `deep-modules.md` check 9, deletion test and position 6; `hot-spots.md` churn and co-change
  `git log` commands and shallow-clone handling.
- [ ] **Step 3:** Commit `feat: add lens references for improve-dotnet-architecture`.

### Task 3: Report template and citation test

**Files:**
- Create: `references/report-template.html`
- Test: `tests/test_improve_dotnet_architecture.py`

- [ ] **Step 1: Write the failing tests**

```python
SKILL = ROOT / "plugins/ivo-health/skills/improve-dotnet-architecture"

def test_every_cited_url_is_in_sources(self):
    # URLs found in SKILL.md and references/*.md (excluding sources.md) ⊆ URLs in sources.md
    self.assertEqual(cited - listed, set())

def test_template_scripts_pin_exact_versions(self):
    # every <script src> in report-template.html matches @\d+\.\d+\.\d+/
    self.assertEqual(unpinned, [])

def test_template_has_dark_mode_tokens(self):
    self.assertIn("prefers-color-scheme: dark", html)
    self.assertIn(':root[data-theme="dark"]', html)
```

- [ ] **Step 2:** Run `PYTHONPATH=scripts python3 -m unittest tests.test_improve_dotnet_architecture -v`. Expected:
  template tests FAIL (file missing).
- [ ] **Step 3:** Write the template following the `artifact-design` skill: tokens on `:root`, dark mode, 16px gutter,
  header, card markup with slots for each spec field, footer; Mermaid from cdnjs or jsDelivr at an exact version.
- [ ] **Step 4:** Run the full checks: unit tests and `scripts/check-skills --base-ref origin/main`. Expected: all pass.
- [ ] **Step 5:** Commit `test: check improve-dotnet-architecture citations and template`.

### Task 4: Dry run against Coordinate

**Files:** none committed (report is a private Artifact).

- [ ] **Step 1:** Follow the skill against `ivo-health/coordinate` `src/web`, from a fresh agent that has only the skill.
- [ ] **Step 2:** Check the report against the spec's "Testing the skill" list and Review Focus 1–4.
- [ ] **Step 3:** Fix skill wording for anything the run got wrong; re-run checks; commit
  `fix: tighten improve-dotnet-architecture after dry run`.
- [ ] **Step 4:** Push the branch and open a draft PR `feat(ivo-health): add improve-dotnet-architecture skill`.
