# Design: improve-dotnet-architecture skill

Date: 2026-10-11
Status: draft for review

## Purpose

A periodic health check of an Ivo Health C# codebase. It produces a ranked list of structural improvements
("candidates"), helps the team choose one, shapes its design, and hands over to the normal planning flow.

It adapts the method of Matt Pocock's `improve-codebase-architecture` skill
(https://github.com/mattpocock/skills/tree/main/skills/engineering/improve-codebase-architecture) for .NET, with
guidance from Martin Fowler, Mark Seemann and Microsoft Learn. It is an adaptation, not a copy: no text is copied
from the original, and `THIRD_PARTY_NOTICES.md` credits the idea.

## Decisions

| Topic | Decision |
|---|---|
| Use | Periodic health check. Not a pre-feature or bug-diagnosis tool. |
| Invocation | Explicit only: `/improve-dotnet-architecture [optional area]` (`disable-model-invocation: true`). |
| Scope | Any Ivo C# codebase. General .NET guidance lives in the skill; local rules come from each repo's `AGENTS.md` and `CLAUDE.md`. Nothing specific to Coordinate is written into the skill. |
| Output | A private Artifact page. Nothing is written to the repository. |
| Memory | ADRs in the target repo's `docs/adr/`. Read before review; offered after a lasting decision. |
| After the report | Question the user on the chosen candidate, write a short design, hand over to `writing-plans`. The skill does not change code. |
| Conventions | Documented conventions and ADRs are taken as given. A candidate that would change one needs strong evidence and is labelled. |
| Size | 5 to 8 candidates per report. |

## File layout

`plugins/ivo-health/skills/improve-dotnet-architecture/`

| File | Contents |
|---|---|
| `SKILL.md` | Process, vocabulary, when to load each reference file, sources. |
| `references/deep-modules.md` | Depth, seams, adapters, the deletion test, "one adapter is a hypothetical seam, two is a real one". |
| `references/testability.md` | Impureim sandwich, test doubles position, dependency categories. |
| `references/domain-model.md` | Rule locality, feature envy, primitive obsession, invariants. |
| `references/di-and-lifetimes.md` | Captive dependencies, Blazor circuit scope, `DbContext` per operation, service locator, over-injection, options pattern, sync over async. |
| `references/hot-spots.md` | How to find churn and files that change together; shallow clone handling. |
| `scripts/hot_spots.py` | Rename-aware churn and co-change counts, leaving out tests and generated code. Added after the trial run. |
| `references/sources.md` | Every cited source with its URL and how it was checked. |
| `references/report-template.html` | Artifact page skeleton; any script it loads is pinned to an exact version. |

## Process

1. **Read local rules.** `AGENTS.md` and `CLAUDE.md` files in the repo, and `docs/adr/`. If there are no ADRs, say so
   and continue.
2. **Find hot spots.** Start from the area the user named. Otherwise rank by git churn. In a shallow clone, fetch more
   history or state that the ranking is limited.
3. **Explore.** A sub-agent walks the hot spots, one pass per lens, and records friction with `file:line` evidence.
4. **Filter.** Remove candidates that conflict with a convention or ADR, unless the evidence is strong; then label them
   "Changes a convention" or "Reopens ADR-NNN". Apply the deletion test. Keep 5 to 8.
5. **Check clinical safety and patient data.** Flag candidates touching clinical logic (observations, escalation,
   visit scheduling, task allocation, medication); load `clinical-safety` before designing them. The report uses
   type, file and member names only — never data values, fixtures or log content.
6. **Publish** the report and ask which candidate to explore.
7. **Question the user** on the chosen candidate with `grilling` until the target shape is clear, then write a short
   design in chat.
8. **Record and hand over.** Offer an ADR for any lasting decision, accepted or rejected. Hand over to
   `writing-plans`.

## Lenses

1. **Deep modules** (Pocock, after Ousterhout): small interface, much behaviour behind it.
2. **Testability** (Seemann): logic testable without the web host or database; impure work at the edges.
3. **Domain model** (Fowler, Microsoft DDD guidance): each rule in one place; entities protect their invariants.
4. **DI and lifetimes** (Microsoft Learn, Seemann): lifetimes are safe under Blazor Server circuits.
5. **Change hot spots** (Fowler on the cost of cruft): rank higher where code changes often or together.

### Highest-value .NET checks

1. Captive dependencies: a singleton holding a scoped service (`DbContext`, `IOptionsSnapshot`, `UserManager`).
2. `DbContext` held beyond one operation, or used in a component outside the repo's chosen pattern.
3. Service locator: `IServiceProvider` or `GetRequiredService` outside the composition root.
4. Constructor over-injection: group into a Facade Service, or move cross-cutting concerns into Decorators.
5. Domain logic mixed with database calls: restructure as read, decide in a pure function returning a result, write.
6. A rule checked in two or more places, or an invariant the entity cannot protect.
7. Primitive obsession: `string` or `Guid` where a strong-typed ID or value type belongs.
8. Tests that verify calls instead of outcomes, or logic tested only against mocks.
9. Single-implementation interfaces that fail the deletion test.
10. Sync over async (`.Result`, `.Wait()`); `IConfiguration` injected where typed options belong.

## Positions where sources disagree

1. **Test doubles (provisional).** Mocks are not a candidate on their own; updating them is cheap. Flag only tests that
   verify calls instead of outcomes, and logic tested only against mocks with no test against real Postgres. Prefer
   real collaborators, then real Postgres, then fakes, then mocks; mocks are right for true external systems. Revisit
   after the first few reviews.
2. **Repositories.** None over EF Core by default. Suggest one only for a single aggregate that needs a fake for fast
   tests or that has two real data sources.
3. **Interfaces.** A single-implementation interface that fails the deletion test is a candidate for removal. Keep it
   where it is a real test seam or a port to an outside system.
4. **Anaemic model or functional core.** Judge rule locality and invariants, not whether entities have methods.
5. **Vocabulary.** Use Pocock's terms (module, interface, depth, seam, adapter, leverage, locality). "Service" means a
   DI registration; "bounded context" keeps its DDD meaning. "Layer" and "wrapper" are not reasons for a change.
6. **Microservices.** Never suggest splitting a deployment. Modules inside one deployment first.

## Report

- Private Artifact page following the artifact design guidance; light and dark modes; Mermaid diagrams rendered by the Artifact page itself, so no script is loaded.
- Header: repo and commit, date, scope, ADRs and conventions read.
- Card per candidate: title; lens; strength (Strong, Worth exploring, Speculative); files with `file:line` evidence;
  problem in one sentence; proposed direction (no interface design yet); gains (leverage, locality, tests);
  before/after diagram; flags ("Changes a convention", "Reopens ADR-NNN", "Clinical logic: needs clinical-safety");
  one or two checked sources.
- Footer: top recommendation with reason; candidates considered and rejected, one line each.
- NHS writing style: plain, short sentences, no hype.

## Sources

Only sources checked against their published text are cited in the skill. Seemann's blog and Microsoft Learn were read
from their source repositories. Fowler pages confirmed only by search are checked again before citing; any that cannot
be checked are left out.

## Repository changes

- New skill folder as above.
- `plugins/ivo-health/.claude-plugin/plugin.json` (and the Codex manifest if it carries a version): minor bump.
- `CHANGELOG.md` entry; `THIRD_PARTY_NOTICES.md` credit to Matt Pocock's skill.
- Checks: `PYTHONPATH=scripts python3 -m unittest discover -s tests` and `scripts/check-skills --base-ref origin/main`.

## Testing the skill

Run it against `ivo-health/coordinate` `src/web` once drafted. Check that the report:
- has 5 to 8 candidates with real `file:line` evidence
- does not suggest anything `src/web/AGENTS.md` already rules out without labelling it
- contains no data values
- cites only sources in `references/sources.md`

## Out of scope

Pre-feature and bug-driven modes; making code changes; a separate shared vocabulary skill; the mobile (TypeScript)
and infrastructure (Terraform) deliverables.
