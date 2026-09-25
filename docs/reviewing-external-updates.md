# Reviewing external updates

Each Monday, a workflow checks whether an external skill has changed upstream. If one has, it opens or updates an issue called "Upstream skill updates available", with a compare link for each change. It never changes files.

## To adopt a change

1. Open the compare link and read the whole diff. Look for:
   - new instructions that send data to other services
   - instructions to run scripts
   - changes to how the skill decides when to run
   - anything that conflicts with `SECURITY.md` or our own skills
2. **For a copied skill** (in `external-skills.lock.json`), run:

       scripts/sync-external <skill-name> --commit <reviewed commit> --reviewed-by "<your full name>"

   If a skill now calls another skill, add `--requires <other-skill>`, and copy that skill too.
3. **For Superpowers**, change `sha` in `.claude-plugin/marketplace.json` to the reviewed commit, and update the description with the new version.
4. Bump the plugin version, update `CHANGELOG.md`, and open a pull request. Another team member reviews it.

## To add a new external skill

- **A whole plugin:** add a `github` entry to `.claude-plugin/marketplace.json` with a full `sha`.
- **A single skill:**

      scripts/sync-external <name> --repo <git URL> --path <folder> --licence <licence> --commit <sha> --reviewed-by "<name>"

  Then add its licence to `plugins/ivo-health/THIRD_PARTY_NOTICES.md`.
