# Sources

Every source the skill cites, and how it was checked. Cite only sources in this table. To add one, read its
published text first and record how you checked it.

"Read from source repository" means the text was read from the public repository the page is published from, on
11 October 2026.

## Method

| Source | URL | Checked |
|---|---|---|
| Matt Pocock, improve-codebase-architecture skill | https://github.com/mattpocock/skills/tree/main/skills/engineering/improve-codebase-architecture | Read from the repository at commit 49dd158 |

## Mark Seemann (blog.ploeh.dk)

Read from source repository: `ploeh/ploeh.github.com`.

| Source | URL | Used for |
|---|---|---|
| Service Locator is an Anti-Pattern | https://blog.ploeh.dk/2010/02/03/ServiceLocatorisanAnti-Pattern/ | Hidden dependencies fail at run time, not compile time |
| Composition Root | https://blog.ploeh.dk/2011/07/28/CompositionRoot/ | Compose object graphs close to the entry point |
| Captive Dependency | https://blog.ploeh.dk/2014/06/02/captive-dependency/ | A longer-lived service holding a shorter-lived one |
| On Constructor Over-injection | https://blog.ploeh.dk/2018/08/27/on-constructor-over-injection/ | Facade Services and Decorators, not parameter objects |
| Impureim sandwich | https://blog.ploeh.dk/2020/03/02/impureim-sandwich/ | Read, decide in pure code, then write |
| Functional architecture is Ports and Adapters | https://blog.ploeh.dk/2016/03/18/functional-architecture-is-ports-and-adapters/ | Pure core keeps I/O at the edges |
| From Primitive Obsession to Domain Modelling | https://blog.ploeh.dk/2015/01/19/from-primitive-obsession-to-domain-modelling/ | Rules on primitives belong in domain types |
| Stubs and mocks break encapsulation | https://blog.ploeh.dk/2022/10/17/stubs-and-mocks-break-encapsulation/ | "Favour Fakes over dynamic mocks" |
| Code that fits in a context window | https://blog.ploeh.dk/2026/02/02/code-that-fits-in-a-context-window/ | Small, well-bounded modules help AI tools as well as people |

## Microsoft Learn

Read from source repositories: `dotnet/docs`, `dotnet/AspNetCore.Docs`, `dotnet/EntityFramework.Docs`.

| Source | URL | Used for |
|---|---|---|
| Dependency injection guidelines | https://learn.microsoft.com/dotnet/core/extensions/dependency-injection/guidelines | Captive dependency, `validateScopes`, avoid service locator and `BuildServiceProvider` |
| Blazor dependency injection | https://learn.microsoft.com/aspnet/core/blazor/fundamentals/dependency-injection | On the server, DI scope lasts for the circuit |
| Blazor with EF Core | https://learn.microsoft.com/aspnet/core/blazor/blazor-ef-core | `DbContext` is not thread safe; use a context factory, one context per operation |
| Choosing a testing strategy (EF Core) | https://learn.microsoft.com/ef/core/testing/choosing-a-testing-strategy | Test against a real database; in-memory provider "highly discouraged" as a fake |
| Options pattern | https://learn.microsoft.com/dotnet/core/extensions/options | Classes depend only on the settings they use |
| ASP.NET Core best practices | https://learn.microsoft.com/aspnet/core/fundamentals/best-practices | Do not block with `Task.Wait` or `Task.Result` |
| Architectural principles | https://learn.microsoft.com/dotnet/architecture/modern-web-apps-azure/architectural-principles | Explicit dependencies |
| Designing a microservice domain model | https://learn.microsoft.com/dotnet/architecture/microservices/microservice-ddd-cqrs-patterns/microservice-domain-model | Entities carry behaviour; quotes Fowler on anaemic models |
| Designing the infrastructure persistence layer | https://learn.microsoft.com/dotnet/architecture/microservices/microservice-ddd-cqrs-patterns/infrastructure-persistence-layer-design | "Repositories shouldn't be mandatory" |

## Martin Fowler

martinfowler.com could not be reached when this skill was written. Only text quoted word for word in a checked
source is used.

| Source | URL | Checked |
|---|---|---|
| Anemic Domain Model | https://martinfowler.com/bliki/AnemicDomainModel.html | Quoted in "Designing a microservice domain model" above; not read directly |

Fowler's other articles (for example on preparatory refactoring, Monolith First and Mocks Aren't Stubs) are not cited
until someone reads them and adds them here.
