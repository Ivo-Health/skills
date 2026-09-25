# Ivo Health organisation skills: design

- **Date:** 2026-09-25
- **Author:** Laurence Bargery (drafted with Claude Code)
- **Status:** Draft for review

## 1. Purpose

Give everyone at Ivo Health the same AI skills across every tool we use, from one private Git repository, with:

- our own skills written once
- external skills taken from their authors' repositories, pinned to a reviewed version
- a clear audit trail of what changed, when, who reviewed it and where it came from
- no patient-identifiable information anywhere in the repository

### Success criteria

1. A new team member gets our skills in the Claude app, Claude Code and ChatGPT without manual install steps, because both organisations sync from this repository.
2. Codex needs at most one documented command, and none if the ChatGPT workspace sync also covers Codex.
3. Adopting a new upstream version of an external skill always happens through a reviewed pull request.
4. CI blocks a pull request that contains an NHS number, a secret or a modified copy of an external skill.

### Out of scope

- Enforcing safety rules at runtime. Skills guide the model, but they are not a safety control. Real safeguards belong in product code, hooks and our DSPT (Data Security and Protection Toolkit) processes.
- Any automation that writes to ChatGPT or the Claude admin settings through an API.

## 2. Platforms and how each gets the skills

| Platform | How skills arrive | How updates arrive |
|---|---|---|
| Claude app (web, desktop, Cowork) | An organisation owner connects this repo under *Organisation settings → Plugins → Add plugins → Sync from GitHub* | Automatic when a merged PR bumps a plugin version ("Sync automatically" on) |
| Claude Code, local | The same organisation sync, with `ivo-health` and `superpowers` set to *Required* or *Installed by default* for users signed in with their Claude account | Automatic |
| Claude Code, cloud | As above when signed in. Fallback: a snippet in each product repo's `.claude/settings.json` (`extraKnownMarketplaces` and `enabledPlugins`) | At session start |
| Codex | `npx skills add ivo-health/skills` (the same installer Matt Pocock's README recommends), plus Superpowers' own Codex install | Re-run the command |
| ChatGPT (and possibly Codex) | A workspace admin imports this repo as a plugin marketplace from GitHub | Daily automatic sync, or "Sync now" |

Conditions for the organisation sync (from Anthropic's help centre):

- Claude Team or Enterprise plan. Ivo Health is believed to be on Enterprise; to confirm.
- This repository must stay **private or internal**.
- The GitHub connector must be enabled for the organisation.
- External `github` sources in `marketplace.json` must be public repositories. `obra/superpowers` is public.

Conditions for the ChatGPT sync (from OpenAI's help centre and release notes):

- ChatGPT Business or Enterprise workspace. The admin imports a marketplace from a public or private GitHub repository, and daily sync is on by default.
- The import can read Claude-compatible marketplaces, so the same `.claude-plugin/marketplace.json` should serve both.
- Importing does not grant anyone access. Admins set installation and access policy for each plugin.

**To confirm during the build** (OpenAI's detailed docs were not reachable from the design session):
1. Whether ChatGPT resolves external `github` sources, such as the Superpowers entry. If it does not, ChatGPT gets only the `ivo-health` plugin, and Superpowers is added in ChatGPT from obra's repo directly.
2. Whether workspace plugins also reach Codex. If they do not, Codex uses `npx skills add`.
3. Whether ChatGPT needs a Codex-format manifest in addition to the Claude one. If so, we add it alongside.

**Connecting the Claude sync:** the first sync failed with "Git Repository is empty" because the repo had no commits. Once `marketplace.json` is on the default branch, re-sync from the marketplace's menu in *Organisation settings → Plugins*.

## 3. Repository layout

```
.claude-plugin/marketplace.json      # lists ivo-health (relative path) and superpowers (github, pinned sha)
plugins/ivo-health/
  .claude-plugin/plugin.json         # version bumped on every skill change
  skills/
    patient-data-protection/SKILL.md # ours
    nhs-writing-style/SKILL.md       # ours
    clinical-safety/SKILL.md         # ours
    grill-me/                        # copied unmodified from mattpocock/skills
    grilling/                        # copied unmodified; grill-me depends on it
  THIRD_PARTY_NOTICES.md             # MIT notices for copied skills
external-skills.lock.json
scripts/
  check-skills                       # structure, PII and hash checks
  sync-external                      # re-fetch copied skills at their pinned commit
  check-upstream                     # compare pins with upstream HEAD
.github/workflows/
  checks.yml                         # every PR
  upstream.yml                       # weekly
docs/
  install.md                         # per-platform steps
  adding-a-skill.md
  reviewing-external-updates.md
README.md  SECURITY.md  CONTRIBUTING.md  CHANGELOG.md
```

We expect `npx skills add` to find `SKILL.md` folders under `plugins/ivo-health/skills/`, as it does for Matt Pocock's repo. If it does not, we add an `.agents/skills` symlink. This is to confirm during the build.

## 4. External skills

There are two ways to bring in an external skill. The choice depends on whether we want the whole pack or only chosen skills.

### 4.1 Whole pack: reference upstream (Superpowers)

This is an entry in `marketplace.json`:

```json
{
  "name": "superpowers",
  "source": { "source": "github", "repo": "obra/superpowers", "sha": "<reviewed commit>" },
  "description": "Superpowers by Jesse Vincent (MIT), pinned to a reviewed commit."
}
```

Nothing is copied. To adopt a new version, a PR changes the `sha`.

### 4.2 Chosen skills: copy unmodified (Matt Pocock's `grill-me`)

Matt's repo publishes about 20 skills as a single plugin, and we only want some of them. Chosen skill folders are copied **unmodified**, including any `agents/openai.yaml`, into `plugins/ivo-health/skills/`, and recorded in `external-skills.lock.json`:

```json
{
  "skills": {
    "grill-me": {
      "repo": "https://github.com/mattpocock/skills",
      "path": "skills/productivity/grill-me",
      "commit": "c55ee46073ed923f86ce59a5eb3b6d895095d1b7",
      "licence": "MIT",
      "requires": ["grilling"],
      "sha256": { "SKILL.md": "<hash>", "agents/openai.yaml": "<hash>" },
      "reviewed_by": "<name>",
      "reviewed_on": "YYYY-MM-DD"
    }
  }
}
```

The rules for copied skills:

- **Never edit a copied skill.** CI fails if any file hash differs from the lock file.
- **Ivo-specific limits go in our own skills,** never in the copied files. For example, "only grill technical and business decisions, never clinical ones" goes in `clinical-safety`.
- **Dependencies are listed in `requires`.** CI checks that every listed skill is present.
- **Licence notices** are kept in `THIRD_PARTY_NOTICES.md`.

### 4.3 Updating external skills

- `upstream.yml` runs weekly. It compares each pin, the Superpowers `sha` and each lock file `commit`, with upstream `HEAD`.
- If anything has moved, it opens or updates **one** GitHub issue listing a compare link for each skill. It never changes files.
- A person reads the upstream diff. If they are happy with it, they run `scripts/sync-external --to <commit>` (or edit the Superpowers `sha`), bump the plugin version, and open a PR.
- A second team member reviews the PR, and git history is the audit record.

## 5. Our starter skills

These are drafted by Claude and reviewed by the team before merge. Each skill cites its sources.

| Skill | Purpose | Sources |
|---|---|---|
| `patient-data-protection` | Never put patient-identifiable information in code, logs, commits, tests, prompts or tickets. Use synthetic data. What to do if PII is found. | UK GDPR, the Caldicott Principles, the NHS DSPT |
| `nhs-writing-style` | Plain English, and NHS terms and tone for UI text and documents | NHS digital service manual: content style guide and A to Z |
| `clinical-safety` | When a change may affect patient safety, prompt the user to consider the hazard log and DCB0129/DCB0160. Keeps AI tools out of clinical decisions. | DCB0129, DCB0160 (NHS England) |

Skill descriptions should be specific enough that the model loads each skill only when it is relevant.

## 6. Checks

`scripts/check-skills` runs locally and in `checks.yml` on every PR.

1. **Structure:** every `SKILL.md` has valid front matter, and `name` matches its folder. `marketplace.json` and `plugin.json` pass `claude plugin validate`.
2. **Version bump:** if anything under `plugins/ivo-health/` changed, `plugin.json` `version` must be higher than on `main`. Without a bump, the organisation auto-sync does not pick up the change.
3. **Patient data scan:** fail on any of:
   - 10-digit numbers, including the spaced 3-3-4 form, that pass the NHS number modulus-11 check
   - email addresses outside an allow-list (`example.com`, `example.org`, `example.nhs.uk`)
   - UK phone numbers outside the Ofcom drama ranges

   A small allow-list file covers deliberate synthetic examples. Any entry added to it must be justified in the PR.
4. **Secrets:** gitleaks.
5. **External integrity:** lock file hashes match, `requires` are present, and no copied file has been edited.

The scripts are Python 3 with no third-party dependencies apart from gitleaks in CI. Each check has unit tests that use synthetic fixtures only. NHS number fixtures use numbers that pass the check digit but are generated for testing and are not real.

## 7. Releases

- Versions follow semver in `plugin.json`, with an entry in `CHANGELOG.md` saying which skills changed.
- Claude syncs when a PR with a version bump is merged. ChatGPT syncs daily; use "Sync now" for an urgent change.
- No build artefacts or zips are needed.

## 8. Security

`SECURITY.md` states:

- No real patient data, credentials, internal hostnames or customer names in any file. Synthetic examples only.
- External skills are adopted only by a reviewed PR at a pinned commit.
- Branch protection on `main`: PR required, one approving review, `checks.yml` passing.
- If PII is found: do not push further commits containing it, tell the team's data protection lead, and follow the incident process. Removing it from history needs a force-push, which is agreed first.
- Skills are guidance, not controls.

## 9. Open items

1. Confirm the Claude plan (Enterprise). Once `marketplace.json` is merged, re-sync in organisation settings and set plugins to Required.
2. Connect the repo in the ChatGPT workspace, and confirm the three ChatGPT and Codex points in section 2.
3. Decide who is the data protection lead named in `SECURITY.md`.
