# Lens: domain model

Each business rule should live in one place, and each entity should be able to protect its own invariants.

## Position: rule locality, not methods

Fowler describes an "Anemic Domain Model" (anaemic, in UK spelling) as one whose objects are "little more than bags
of getters and setters", with the
behaviour in service classes (https://martinfowler.com/bliki/AnemicDomainModel.html, as quoted in
https://learn.microsoft.com/dotnet/architecture/microservices/microservice-ddd-cqrs-patterns/microservice-domain-model).

A functional style, with immutable records and pure functions grouped in one module, can look anaemic by that test
and still be well designed. So do not flag a type just because it has no methods. Flag these instead.

## What to look for

### A rule checked in two or more places

The same condition appears in several services, components or endpoints, such as "a completed visit cannot be
reassigned". When the rule changes, someone will miss a copy.

**Direction:** move the rule to the entity, as an intention-revealing method that returns a result, or to one pure
function in the module that owns the concept. Callers then ask; they do not check.

### An invariant the entity cannot protect

Public setters, or collections callers can add to, let any code put the entity into a state the business does not
allow.

**Direction:** private setters and methods that enforce the rule. Read the repository's conventions first: many
already set rules for setters and collections.

### Feature envy

A method that uses another type's data more than its own, often a service method that reads five properties of an
entity to make a decision.

**Direction:** move the method to the type whose data it uses.

### Primitive obsession

`string`, `int` or `Guid` where the domain has a concept with rules, so validation repeats at each call site
(https://blog.ploeh.dk/2015/01/19/from-primitive-obsession-to-domain-modelling/). If the repository already has
strong-typed IDs or value types, look for the gaps: raw `Guid` parameters, or the same `IsNullOrWhiteSpace` check
on the same field in several places.

**Direction:** a domain type that can only be created valid, parsed once at the edge.

## Position: repositories

Do not suggest a repository over EF Core by default. A `DbContext` already acts as a unit of work, and Microsoft's
own guidance says "Repositories shouldn't be mandatory"
(https://learn.microsoft.com/dotnet/architecture/microservices/microservice-ddd-cqrs-patterns/infrastructure-persistence-layer-design).

Suggest one only for a single aggregate that:
- needs a fake so its logic can be tested quickly, or
- really has two data sources

For a repository that already exists, apply the deletion test. Also check it against the repository's conventions:
one that takes a scoped `DbContext` where the conventions forbid it, or that has no callers, is a candidate.

## Clinical logic

Rules about patient details (names, dates of birth, addresses, contact details), observations, escalation,
scheduling, allocation or medication are clinical logic. Moving them can change
what staff see or when they are warned. Label the candidate "Clinical logic: needs clinical-safety".

## When not to suggest it

- The "duplicate" checks differ on purpose, for example a looser check for display than for saving. Ask before
  merging them.
- The type is a data transfer object (DTO) or read model. These are meant to carry data only.
