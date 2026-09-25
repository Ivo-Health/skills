# Installing the skills

## Claude app (web, desktop and Cowork)

An organisation owner sets this up once:

1. Go to Organisation settings, then Plugins.
2. Choose Add plugins, then Sync from GitHub, and select `Ivo-Health/skills`.
3. Turn on Sync automatically from the marketplace menu.
4. Set `ivo-health` and `superpowers` to Required, so they also reach Claude Code for anyone signed in with their Claude account.

If the marketplace shows "Needs attention", choose re-sync from its menu. The first sync failed because the repository was empty.

## Claude Code

If you are signed in with your Ivo Health Claude account, the Required plugins arrive automatically.

Otherwise, run:

    claude plugin marketplace add Ivo-Health/skills
    claude plugin install ivo-health@ivo-health
    claude plugin install superpowers@ivo-health

To make cloud sessions in a product repository load the plugins, add this to that repository's `.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "ivo-health": {
      "source": { "source": "github", "repo": "Ivo-Health/skills" }
    }
  },
  "enabledPlugins": {
    "ivo-health@ivo-health": true,
    "superpowers@ivo-health": true
  }
}
```

The cloud environment needs GitHub access to `Ivo-Health/skills`, because it is private.

## ChatGPT

A workspace admin sets this up once:

1. Open the workspace plugin settings.
2. Import a marketplace from GitHub and select `Ivo-Health/skills`.
3. Daily sync is on by default. Use Sync now for an urgent change.
4. Set installation and access for each plugin. Importing does not give anyone access by itself.

This repository has two catalogues that point at the same skills:

- `.claude-plugin/marketplace.json` for Claude
- `.agents/plugins/marketplace.json` for Codex and ChatGPT

Both list `ivo-health`, and Superpowers pinned to the same commit. The Codex catalogue gives Superpowers as a git `url` with a `sha`, rather than the `github` source that ChatGPT rejected with "Marketplace entry `superpowers` uses an unsupported plugin source".

To confirm at the next sync, and record here:

- which catalogue ChatGPT reads
- whether the Superpowers error has gone

If the error is still there, import a second marketplace from `obra/superpowers` and enable only `superpowers`. Note that ChatGPT then follows upstream rather than our pin.

## Codex

Add this repository as a plugin marketplace, then install both plugins:

    codex plugin marketplace add Ivo-Health/skills
    codex plugin add ivo-health@ivo-health
    codex plugin add superpowers@ivo-health

`codex plugin list` should show `ivo-health` at the version in `plugins/ivo-health/.claude-plugin/plugin.json`, and `superpowers` at the pinned sha.

Codex has no equivalent of Claude's per-repository `enabledPlugins`, so each person adds the marketplace once. To update, run `codex plugin marketplace upgrade ivo-health`.
