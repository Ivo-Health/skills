# Lens: testability

Logic should be testable through the interface people actually use, without starting the web host. Tests should
check outcomes, so they keep passing when the internals change.

## What to look for

### Decisions mixed with database calls

A method reads data, decides something, reads more, decides again, then writes. The decisions can only be tested
by running all the I/O or by mocking it.

```csharp
// Mixed: the rule is buried between awaits.
var visit = await db.Visits.SingleAsync(v => v.Id == visitId, cancellationToken);
if (visit.Status == VisitStatus.Completed) return Result.Fail(...);
var clash = await db.Visits.AnyAsync(v => v.StaffId == staffId && v.Start == visit.Start, cancellationToken);
if (clash) return Result.Fail(...);
visit.Assign(staffId);
await db.SaveChangesAsync(cancellationToken);
```

**Direction:** an impureim sandwich (https://blog.ploeh.dk/2020/03/02/impureim-sandwich/). Read everything the
decision needs first. Decide in a pure function that takes those values and returns a result. Then write. The pure
middle is tested with plain values. A functional core like this leaves I/O at the edges
(https://blog.ploeh.dk/2016/03/18/functional-architecture-is-ports-and-adapters/).

Keep the sandwich inside one module. Do not lift the pure function into a separate helper class just to test it.
That splits the behaviour in two (see `deep-modules.md`).

### Tests that check calls, not outcomes

Tests that assert `Verify(x => x.SaveAsync(...), Times.Once)` or the order of calls fail when the internals change,
even when the behaviour is still right.

### Logic tested only against mocks

A query or rule whose only tests use a mocked data source. The mock returns what the test told it to, so the test
passes even if the real query is wrong.

## Position on test doubles (provisional)

This position will be reviewed after the first few health checks.

- Mocks are not a candidate on their own. Updating them is cheap.
- Flag only:
  - tests that verify calls instead of outcomes, where the call is not itself the behaviour
  - logic tested only against mocks, with no test against the real database
- Prefer, in this order:
  1. real collaborators
  2. the real database, through the repository's own integration test set-up
  3. hand-written fakes that obey the real contract (https://blog.ploeh.dk/2022/10/17/stubs-and-mocks-break-encapsulation/)
  4. mocks
- Mocks are right for systems you do not own, such as another organisation's API, and where the call is the outcome,
  such as "a message was sent".
- Do not suggest the EF Core in-memory provider as a test database. Microsoft "highly discouraged" using it as a fake
  and recommends testing against a real database
  (https://learn.microsoft.com/ef/core/testing/choosing-a-testing-strategy).

## Kinds of dependency

Use these to say how a candidate would be tested.

| Kind | Example | How to test |
|---|---|---|
| In process | Pure logic, domain types | Directly |
| Local stand-in available | PostgreSQL in a container | The real thing, locally |
| Owned but remote | Your own other service | Port and adapter, with a fake |
| Not owned | A clinical system's API | Mock or fake at the adapter |

## When not to suggest it

- The logic is trivial and already covered by integration tests through its public interface.
- The repository's conventions already set a test approach. Work within it.
