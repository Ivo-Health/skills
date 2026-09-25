# Security

## Rules for this repository

- Never add real patient data, credentials, internal hostnames or customer names to any file. Use synthetic examples only.
- Adopt external skills only through a reviewed pull request, pinned to a commit.
- Never edit a copied external skill. Put Ivo Health rules in our own skills instead.
- Skills guide AI tools. They are not a safety control. Real safeguards belong in product code, hooks and our Data Security and Protection Toolkit processes.

## Branch protection

The `main` branch requires a pull request, one approving review and the `Checks` workflow passing.

## If you find patient data or a secret in this repository

1. Do not push further commits that contain it.
2. Tell the data protection lead straight away: [name to be agreed by the team].
3. Follow the Ivo Health incident process.
4. Rotate any exposed secret.
5. Removing data from git history needs a force-push. Agree this with the team first.

## Reporting a problem with a skill

Open an issue in this repository. Do not include patient data in the issue.
