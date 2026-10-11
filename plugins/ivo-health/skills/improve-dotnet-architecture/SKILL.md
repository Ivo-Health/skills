---
name: improve-dotnet-architecture
description: Use when someone asks for an architecture health check or review of a C# or .NET codebase at Ivo Health. Finds the structural changes that would make the code easier to change, test and navigate, publishes them as a ranked report, then helps design the one chosen.
disable-model-invocation: true
---

# Improve .NET architecture

A periodic health check of a C# codebase. You find 5 to 8 structural improvements ("candidates"), rank them in a
report, help the team choose one, and shape its design. You do not change code. The design goes to
`writing-plans` to be built.

Run it as `/improve-dotnet-architecture`, optionally followed by an area, such as a project, folder or feature name.

## Words to use

Use these words with these meanings, in your notes and the report.

- **Module**: anything with an interface and an implementation, at any size: a method, a class, a namespace, a
  project.
- **Interface**: everything a caller must know to use a module: its signatures, and also its rules, order of calls,
  failure results and configuration.
- **Depth**: how much behaviour a module gives for the size of its interface. A **deep** module hides a lot behind a
  small interface. A **shallow** module's interface is nearly as complex as what it does.
- **Seam**: a place where behaviour can change without editing the code around it, such as a constructor parameter
  typed as an interface.
- **Adapter**: the code on the far side of a seam that talks to something outside, such as a database or another
  organisation's API.
- **Leverage**: what callers gain from a module.
- **Locality**: what maintainers gain: one change in one place.
- **Service**: a type registered with dependency injection (DI). Only in that sense.
- **Bounded context**: the domain-driven design (DDD) meaning only.

"It adds a layer" and "it's just a wrapper" are not reasons for a change. Say what it costs callers or maintainers.

## Process

### 1. Read the local rules and set the scope

Load `patient-data-protection` and `nhs-writing-style` now. They apply to everything below.

Read every `AGENTS.md` and `CLAUDE.md` in the repository, and every record in `docs/adr/`. These are the
**conventions**. Take them as given.

- If there is no `docs/adr/`, say so in the report header and carry on.
- If there is no `AGENTS.md` or `CLAUDE.md`, say so. Do not invent conventions. Infer the existing patterns from the
  code and label them as inferred.
- Review one .NET solution (`.sln` or `.slnx`) per run. If the user named an area, use the solution it is in.
  Otherwise use the solution with the most changes from step 2. List the other solutions, and any non-.NET folders,
  as out of scope in the report header.

### 2. Find where to look

If the user named an area, start there. Otherwise follow `references/hot-spots.md` to find the files that change
most and the files that change together. Say in the report which you used.

### 3. Explore through each lens

| Lens | Reference | Asks |
|---|---|---|
| Deep modules | `references/deep-modules.md` | Are modules deep? Does each seam earn its place? |
| Testability | `references/testability.md` | Can the logic be tested without the web host or database? Do tests check outcomes? |
| Domain model | `references/domain-model.md` | Does each rule live in one place? Can entities protect their invariants? |
| DI and lifetimes | `references/di-and-lifetimes.md` | Are service lifetimes safe, especially under Blazor Server circuits? |

- If you can start sub-agents, give each lens to its own read-only sub-agent, with its reference file and the hot
  spot list. Pass on the patient data rules below.
- If you cannot, load all four references, then read each hot spot once and apply every lens as you read.
- Stop exploring a lens when 5 more files in a row turn up nothing new. Expect to read 20 to 30 files in all.
- Record each piece of friction with its full repository-relative path, `file:line`, and the type and member names
  involved. Friction outside the hot spots counts too.

**Reading safely.** In seed data, test fixtures, test data builders and sample files, read only type and member
names and signatures. Search for the names you need rather than opening the whole file, so you do not read data
values.

### 4. Choose the candidates

- Merge friction that has one cause into one candidate. If two candidates overlap but have different causes, keep
  them apart and say on both cards that they overlap.
- Apply the **deletion test** from `references/deep-modules.md`.
- Drop anything a convention or architecture decision record (ADR) rules out. Keep it only when the evidence is
  strong, and then label it "Changes a convention" or "Reopens ADR-NNN" with the reason.
- Give each a strength: **Strong** (clear evidence, clear gain), **Worth exploring** (real friction, the fix needs
  discussion) or **Speculative** (real evidence, but the gain is uncertain). A hunch with no `file:line` evidence is
  not a candidate.
- Rank by gain. Judge gain by how many places the change simplifies, how often those places change, and the risk it
  removes, such as a rule that can be missed or a lifetime bug. Break ties by change count.
- Keep 5 to 8. If fewer than 5 have evidence, report fewer and say so. Never add a candidate just to reach 5.

### 5. Check patient safety and patient data

- Flag any candidate that touches clinical logic or patient details: what staff see about a patient (including
  names, dates of birth, addresses and contact details), observations, alerts, escalation, visit scheduling, task
  allocation or medication. Label it "Clinical logic: needs clinical-safety". Load the `clinical-safety` skill
  before designing it.
- The report names files, types and members only. Never copy data values, test fixture contents, seed data, log
  output or free text into it, even when they look synthetic.

### 6. Write and publish the report

1. Copy `references/report-template.html`. It already sets the design, so load `artifact-design` only for the page
   rules. Keep the `<title>` as the first line of the file.
2. Fill one card per candidate. Use more than one lens chip if a candidate spans lenses. Give every card evidence
   and a before and after diagram. Cite only sources listed in `references/sources.md`, using their exact URLs.
3. Check every `file:line` before you finish: open the file at that line and confirm it shows what the card says.
4. Do not design interfaces yet. Each card gives a direction, not a solution.
5. Publish the report as a private Artifact page. Never write it into the repository. If you cannot publish, or the
   user asked you not to, write it to your scratchpad or temporary directory and send it to the user. Diagrams then
   show as Mermaid text, which is still readable.
6. The report ends by asking which candidate to explore. Ask the same in your reply, with one line per candidate.

### 7. Shape the chosen candidate

Use the `grilling` skill to question the user on the chosen candidate until its shape is clear: what the new
interface hides, where the seams go, what tests prove it, and how to move to it in small safe steps. Write a short
design in the chat.

### 8. Record and hand over

- When the user accepts or rejects a candidate for a reason that will last, offer to write an ADR in `docs/adr/`.
  Number it after the highest existing record. Keep it short: context, decision, consequences. A rejected candidate
  with an ADR is not suggested again unless the friction has grown.
- Hand the design to `writing-plans`.

## Sources

Every source this skill relies on, with how it was checked, is in `references/sources.md`.
