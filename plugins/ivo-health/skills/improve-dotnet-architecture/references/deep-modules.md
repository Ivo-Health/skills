# Lens: deep modules

A deep module gives a lot of behaviour through a small interface. Callers learn little and get much. Maintainers
find the behaviour in one place. Seemann asks whether code designed to fit in a person's head would also suit
AI tools, which can hold only so much at once
(https://blog.ploeh.dk/2026/02/02/code-that-fits-in-a-context-window/).

## What to look for

- **Concepts spread thin.** To understand one idea, such as "rescheduling a visit", you open five or more small types
  that each do one step and pass data on.
- **Pass-through methods.** A class whose methods mostly forward to another class with the same arguments.
- **Leaky interfaces.** Callers must call methods in a set order, check flags or know internal states to use a
  module correctly.
- **Single-implementation interfaces.** `IThing` with one `Thing`, no fake, no second adapter, and no outside system
  behind it.
- **Helpers extracted only to be tested.** A pure function lifted out so a test can reach it, which leaves the real
  behaviour split across two places.

## The deletion test

Imagine deleting the module and moving its code into its callers.

- If complexity **concentrates**, with callers repeating the same steps, the module was earning its place. Look at
  deepening it instead.
- If complexity just **moves**, with each caller getting a few lines, the module was shallow. It is a candidate to
  merge or remove.

## Seams

One adapter behind a seam is a hypothetical seam. Two adapters, such as the real one and a fake used by tests, make
it a real seam. A test double swapped in through the container in test set-up (for example `services.Replace(...)`)
counts as a second adapter.

- Keep an interface that is a real seam, or a port to a system outside your control, such as a clinical system's
  API.
- Suggest removing an interface with one implementation that fails the deletion test. Callers then use the class
  directly, and a reader has one fewer hop.
- If there are several such interfaces, report them as one candidate, ranked low, unless one sits in a hot spot.

To find implementations, search for `: IName` and `, IName` in the solution, and for the interface name in test
set-up code.

## Sketch (synthetic)

```csharp
// Shallow: three types, each a step, and every caller wires them in order.
var slots = slotFinder.Find(visit);
var chosen = slotRanker.Rank(slots, rules).First();
await visitWriter.MoveAsync(visit.Id, chosen, cancellationToken);

// Deeper: one interface that hides the steps and the order.
var result = await visitScheduler.RescheduleAsync(visitId, constraints, cancellationToken);
```

## Direction to suggest

- Merge shallow steps behind one interface that names the job, not the steps.
- Move the tests to that interface. Once tests cover it, delete tests of the old internal steps rather than keeping
  both.

## When not to suggest it

- The repository's conventions require the split, for example a rule that services sit in `Services/`.
- The module is shallow but stable and rarely changes. Note it, rank it low or leave it out.

## Splitting deployments

Never suggest splitting into separately deployed services. Make modules inside the one deployment first, such as a
namespace or project for each bounded context.
