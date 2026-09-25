---
name: "product-design-prototyping"
description: "Prototype and design Ivo Health product changes in Lovable: grill Laurence on an idea or page fix, read the code, build safely via Lovable, verify, then review how the skill could improve."
---

# Product design and prototyping (Ivo Health)

Use this whenever Laurence talks through a product idea, a new feature, or a fix to a page in an Ivo Health prototype built in Lovable, and wants it thought through and built. Trigger on "prototype", "product idea", "fix this page", "change the referral hub", "let's design", "product design", a screenshot of a prototype page with requested changes, or any request to change the H@H Operations Support app or the Ivo Health website.

Six stages: intake, grill, route, build, verify, improve. Never skip the grill. Never change anything until Laurence confirms the change brief.

## Laurence's working principles

- **Page by page.** Keep each change to the page in hand. Anything that changes a wider model (for example pathways versus care plans) is parked as its own session. Note it, do not build it.
- **Keep it simple.** It is a prototype. The smallest version that shows the idea wins. Fewer examples, fewer variants.
- **Restrained visuals.** Avoid lots of colours; they look amateur. Prefer one neutral chip style where the word does the work. Colour is reserved for meaning (RAG status, accepted in green, declined in grey, never red for a normal decision).
- **Own files for lists and logic.** Every reusable list or mapping (sources, reasons, labels, groups) lives in its own file under `src/lib/`, so later changes cannot break it. Say this in every Lovable instruction.
- **Real places, fictional people.** Real GP practices, hospitals, streets and postcodes for each demo location, each verified on nhs.uk, nidirect or NHS inform before sending. Never let Lovable invent real names. Patients are always fictional; new NHS numbers use the 999 test range. No clinician or GP names.
- **Clinical plausibility.** Check demo data makes clinical sense (a GP would not start IV antibiotics in an infant with suspected sepsis). Raise mismatches as a question with a recommended fix.
- **Demo-proof data.** Seeded "today" events sit between 08:00 and 09:00 UK time so a live decision in a demo is always the newest. Use Europe/London for all seeded and displayed times.
- **Language.** "Declined", not "rejected". NHS register, UK spelling, sentence case, no em dashes in UI text or in replies.

## Known projects and how they work

- H@H Operations Support (WardFlow, main prototype). The preview is password gated.
- IVO Health Website, in the same workspace.
- Find each project by name through the Lovable connection, and take the preview link from `get_project`. Do not write project IDs or preview links into this skill. If more than one project matches a name, ask Laurence which to use.
- Design system: the "Ivo Health" Design System artifact. Read its `project/README.md` before visual changes and use its token names.

H@H prototype architecture:

- Data lives in Supabase. Read via `src/lib/wf-db.ts` (row mappers), written via `src/lib/wf-actions.ts` and `src/lib/wf-data.server.ts`, whose patch keys are whitelisted (new columns must be added there).
- Demo data is seeded by the database function `reset_demo()`, which wraps `reset_demo_base()`. Data changes need a migration. `reset_demo()` must stay `REVOKE ALL ... FROM PUBLIC, anon, authenticated` and `GRANT EXECUTE ... TO service_role`, with no SECURITY DEFINER.
- Demo locations (sussex canonical, craigavon, lanarkshire, uclh, surrey-downs, oxford, kent, nca) switch by text replacement: `locations.replacements` maps canonical Sussex strings to local ones (`src/lib/locations.server.ts`, longest string first). Any new address, practice or place needs a pair in all seven non-Sussex packs, or it shows mixed locations. Use canonical town names (for example "Eastbourne UCR team") so existing town pairs localise them.
- Pathways and criteria (`src/lib/pathways/`, `src/lib/criteria/`) and the ReferralAcceptWizard are clinical logic.

## Tools

- If Lovable tools are missing, search with ToolSearch ("lovable"). If `ListConnectors` shows Lovable connected but off for the chat, ask Laurence to switch it on in the chat's connector menu, then search again.
- Reading: `list_files`, `read_file`. Building: `send_message` (uses Laurence's credits). Checking: `get_project` (`agentFinished`, `latest_commit_sha`), `get_diff` with `base_sha` and `sha`, `get_message`.
- Builds often exceed the 180 second tool limit. Send with `wait: false`, then sleep about 150 seconds in Bash and poll `get_project` until `agentFinished` is true. `list_messages` output is huge; save and extract with jq.
- Record `latest_commit_sha` before every send so you can diff exactly what changed.
- Never use `query_database`, `enable_database` or `deploy_project` unless Laurence asks for that exact action.

## Stage 1: Intake

- Let Laurence talk (often voice notes, sometimes with screenshots). Capture the page, the users (coordinator, clinical lead, nurse, commissioner) and each requested change as a numbered list.
- Read the relevant route, components and data path before asking anything. Facts are your job.
- Play back what you heard and what the code does today, including bugs you spotted, in plain words.

## Stage 2: Grill

Invoke the `grill-me` skill (`anthropic-skills:grill-me`) and follow its method: numbered frontier questions, each with a recommended answer; wait; recompute; repeat until nothing is open.

- Explain a question more plainly if Laurence skips it or is unsure. He sometimes shares context rather than a request ("that's the logic, maybe later"); confirm whether it is in scope.
- Look up facts yourself between rounds (code, data, real places) and bring findings back as questions only where a decision is needed.
- Cover where relevant: users and moment; outcome; scope in and out; clinical safety and plausibility; data and IG; states (empty, error, many, mobile); wording; visuals and design system; demo locations, resets and times.
- End with a **change brief**: goal, users, numbered changes, demo data table, how it is built (files, migration), what does not change, acceptance criteria, route. Get a clear yes.

## Stage 3: Route

- **Send directly** for small, bounded UI or style changes that touch no clinical logic, auth, schema or seed data.
- **Plan first** (`plan_mode: true`) for database, seed data, clinical logic, auth or multi-screen changes. Summarise Lovable's plan, surface any blocker it raises as a question, then ask Laurence whether you send the approval or he approves in the editor.
- **Paste prompt** when Laurence wants to run or edit the wording himself.

## Stage 4: Build

Every Lovable instruction contains: context; goal; numbered changes naming files, components and tokens; new files for lists and mappings; a "Do not change" list; acceptance criteria; data rules; style rules; and "make only these changes".

**Database rule.** Lovable improvises in SQL (it once opened `reset_demo()` to public callers and rewrote a patient's notes during a small time change). For any change to a database function or seed data, write the complete SQL yourself and tell Lovable to use it exactly, including the REVOKE and GRANT lines. Reuse the last verified function body and change only what was asked.

If Laurence sends a new request mid-build, let the current build finish, verify it, then handle the new request as its own small change.

## Stage 5: Verify and report

Diff `base_sha..sha` after every build and check:

1. Only the expected files changed; note extras (for example empty migrations, roadmap files).
2. Every acceptance criterion and every "do not change" item.
3. Security: grants and SECURITY DEFINER on functions, RLS, anything newly callable by anon or authenticated.
4. Seed data unchanged except where asked (names, NHS numbers, notes, canonical strings, coordinates, teams).
5. Times in Europe/London; contrast at least 4.5:1 for text (compute it; darken rather than accept a fail).
6. Location packs: new strings have pairs in all seven packs.

If anything regressed, fix it straight away with an exact corrective instruction, then tell Laurence plainly what went wrong and that it is fixed. Report: preview link, what changed, what to click, anything open. Keep it short.

## Stage 6: Improve this skill (every session)

At the end of each prototyping session, or after any mistake or correction, ask Laurence in one line whether to update this skill, and list the specific improvements you would make (new principles he stated, mistakes caught, process changes). If he agrees, propose the complete updated SKILL.md with `propose_skills`, keeping everything worth keeping.
