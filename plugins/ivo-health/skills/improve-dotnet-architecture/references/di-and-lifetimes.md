# Lens: DI and lifetimes

Service lifetimes must be safe, especially in Blazor Server, where a DI scope lasts for the whole circuit. A circuit
is one open browser tab and can last for hours
(https://learn.microsoft.com/aspnet/core/blazor/fundamentals/dependency-injection).

Read the repository's conventions first. Many set their own lifetime rules, such as singletons by default. Check the
code against those rules as well as the general ones below.

## What to look for

### 1. Captive dependencies

A longer-lived service holds a shorter-lived one, such as a singleton taking a scoped service in its constructor
(https://blog.ploeh.dk/2014/06/02/captive-dependency/). Common captives: `DbContext`, `UserManager<T>`,
`SignInManager<T>`, `IOptionsSnapshot<T>` and any service the repository registers as scoped.

**How to check:** list the singleton registrations, then read each constructor. Then check once whether scope
validation is on where tests run. Microsoft suggests `ValidateScopes` to catch captives at start-up
(https://learn.microsoft.com/dotnet/core/extensions/dependency-injection/guidelines). The default host builders turn
it on only in the Development environment. If the test server runs in another environment and does not turn it on,
note that as evidence. Do not go further than this one check.

**Direction:** change the lifetime, or depend on a factory that creates the short-lived service per operation.

### 2. `DbContext` held beyond one operation

`DbContext` is not thread safe. In Blazor Server a scoped context is shared by every component on the circuit.
Microsoft recommends a context factory and one context per operation
(https://learn.microsoft.com/aspnet/core/blazor/blazor-ef-core).

**Look for:** a `DbContext` injected into a component or a long-lived service, or stored in a field. If the
repository has its own pattern for this, look for code that goes round it.

### 3. Service locator

`IServiceProvider.GetService`, `GetRequiredService` or `CreateScope` called inside application classes or components,
outside the composition root. It hides dependencies, so a missing one fails at run time instead of at start-up
(https://blog.ploeh.dk/2010/02/03/ServiceLocatorisanAnti-Pattern/). Microsoft also says to avoid it, and to avoid
calling `BuildServiceProvider` while registering services
(https://learn.microsoft.com/dotnet/core/extensions/dependency-injection/guidelines).

**Direction:** constructor injection, with registration in the composition root, near `Program.cs`
(https://blog.ploeh.dk/2011/07/28/CompositionRoot/). A singleton that must create scopes should own that work and
offer a method for it, so components never touch the container.

### 4. Constructor over-injection

A constructor with more than 4 or 5 dependencies is a sign the class does too much
(https://blog.ploeh.dk/2018/08/27/on-constructor-over-injection/).

**Direction:**
- Dependencies that are always used together → group them behind a **Facade Service** that names what they do
  together. This often makes a deeper module.
- Cross-cutting dependencies (logging, caching, authorisation, retries) → move into **Decorators**.
- Do not suggest a parameter object or "dependencies" bag. It hides the count without fixing the cause.

### 5. Hidden or wide dependencies

- Classes should state every dependency they need, in the constructor
  (https://learn.microsoft.com/dotnet/architecture/modern-web-apps-azure/architectural-principles).
- `IConfiguration` injected into a service, which can then read any setting. Use typed options, so each class depends
  only on the settings it uses (https://learn.microsoft.com/dotnet/core/extensions/options).

### 6. Sync over async

`.Result`, `.Wait()` or `GetAwaiter().GetResult()` on a task in request or component code. It blocks threads and can
cause deadlocks. Also `await Task.Run(...)` around code that is already running on the thread pool
(https://learn.microsoft.com/aspnet/core/fundamentals/best-practices).

## When not to suggest it

- The composition root itself, test set-up code and framework start-up hooks may use `IServiceProvider` directly.
- A singleton that creates a scope for each unit of work, such as each background job, is following the guidance
  above, not breaking it. Flag it only if it holds on to the scope or the services from it.
- A static page rendered per request may legitimately use scoped services, if the repository's conventions allow it.
