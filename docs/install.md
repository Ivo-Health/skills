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

ChatGPT does not support the `github` plugin source, so it reports "Marketplace entry `superpowers` uses an unsupported plugin source" and imports only `ivo-health`. This is expected. To add Superpowers in ChatGPT:

1. Import a second marketplace from GitHub, and select `obra/superpowers`.
2. Enable only the `superpowers` plugin.
3. Check that the version shown matches the one pinned in `.claude-plugin/marketplace.json`. ChatGPT follows the upstream repository rather than our pin, so review the Superpowers release notes before new versions reach staff.

Still to confirm, and record here: whether the workspace plugins also reach Codex.

## Codex

If the ChatGPT workspace plugins do not reach Codex, run this in each project:

    npx skills@latest add Ivo-Health/skills

For Superpowers, follow the Codex instructions in the Superpowers README.
