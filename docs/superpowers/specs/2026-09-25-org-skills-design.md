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

1. A new team member gets our skills in the Claude app and Claude Code without manual install steps, because they are pushed by the organisation.
2. Codex needs one documented command. ChatGPT needs a documented upload from a release.
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
| ChatGPT | An admin uploads per-skill zips from the latest GitHub release | Manual, following the release checklist |

Conditions for the organisation sync (from Anthropic's help centre):

- Claude Team or Enterprise plan. Ivo Health is believed to be on Enterprise; to confirm.
- This repository must stay **private or internal**.
- The GitHub connector must be enabled for the organisation.
- External `github` sources in `marketplace.json` must be public repositories. `obra/superpowers` is public.

**To confirm during the build:** Codex skill paths and the ChatGPT skill upload process. OpenAI's documentation was not reachable from the design session, so `docs/install.md` must be checked against it before the first release.

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
  package                            # build dist/<skill>.zip for ChatGPT
.github/workflows/
  checks.yml                         # every PR
  upstream.yml                       # weekly
  release.yml                        # on tag: attach zips to the GitHub release
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
- When a `v*` tag is pushed, `release.yml` runs `scripts/package` and attaches `dist/<skill>.zip` for each skill to the GitHub release, for the ChatGPT upload.
- `docs/install.md` includes a short checklist for the ChatGPT upload.

## 8. Security

`SECURITY.md` states:

- No real patient data, credentials, internal hostnames or customer names in any file. Synthetic examples only.
- External skills are adopted only by a reviewed PR at a pinned commit.
- Branch protection on `main`: PR required, one approving review, `checks.yml` passing.
- If PII is found: do not push further commits containing it, tell the team's data protection lead, and follow the incident process. Removing it from history needs a force-push, which is agreed first.
- Skills are guidance, not controls.

## 9. Open items

1. Confirm the Claude plan (Enterprise), then connect the repo in organisation settings and set plugins to Required.
2. Confirm the Codex install paths and the ChatGPT upload process against OpenAI's documentation.
3. Decide who is the data protection lead named in `SECURITY.md`.
