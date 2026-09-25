# Contributing

1. Create a branch from `main`.
2. Make your change. See `docs/adding-a-skill.md` or `docs/reviewing-external-updates.md`.
3. If anything under `plugins/ivo-health/` changed, raise `version` in `plugins/ivo-health/.claude-plugin/plugin.json`:
   - patch for wording fixes
   - minor for new or changed skills
   - major for removed or renamed skills

   The Claude organisation sync only picks up changes that come with a version bump.
4. Add a line to `CHANGELOG.md`.
5. Run the checks in `README.md`.
6. Open a pull request. Another team member must review it.
