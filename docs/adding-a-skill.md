# Adding or changing a skill

1. Create a folder in `plugins/ivo-health/skills/`. Name it in lower case, with words separated by hyphens.
2. Add a `SKILL.md` file:

   ```markdown
   ---
   name: your-skill-name
   description: Use when ... Say exactly when the skill applies, so the AI loads it only when relevant.
   ---

   # Your skill title

   Instructions in plain English.

   ## Sources

   - Name of the source (organisation): link
   ```

3. Cite a source for every rule that comes from guidance or regulation.
4. Use synthetic examples only. See `SECURITY.md`.
5. Bump the plugin version, and follow `CONTRIBUTING.md`.
