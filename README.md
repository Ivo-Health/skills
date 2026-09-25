# Ivo Health skills

The AI skills we use at Ivo Health, in one place. Claude, Claude Code, ChatGPT and Codex all read them from this repository.

## What is here

| Plugin | What it contains | Where it comes from |
|---|---|---|
| `ivo-health` | `patient-data-protection`, `nhs-writing-style`, `clinical-safety`, `product-design-prototyping`, and unmodified copies of `grill-me` and `grilling` | This repository. Copied skills are listed in `external-skills.lock.json` |
| `superpowers` | Development workflow skills by Jesse Vincent | `obra/superpowers`, pinned in `.claude-plugin/marketplace.json` and `.agents/plugins/marketplace.json` |

## Getting the skills

- **Claude app and Claude Code:** you do not need to do anything. The organisation syncs this repository.
- **ChatGPT:** you do not need to do anything. The workspace syncs this repository daily.
- **Other set-ups and Codex:** see `docs/install.md`.

## Making changes

- To add or change a skill, see `docs/adding-a-skill.md` and `CONTRIBUTING.md`.
- To adopt a new version of an external skill, see `docs/reviewing-external-updates.md`.
- Before you start, read `SECURITY.md`. This repository must never contain patient data.

## Checks

Run these before you open a pull request:

    PYTHONPATH=scripts python3 -m unittest discover -s tests
    scripts/check-skills --base-ref origin/main
