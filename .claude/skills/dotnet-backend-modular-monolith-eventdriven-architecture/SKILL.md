---
name: dotnet-backend-modular-monolith-eventdriven-architecture
description: This skill should be used when the user asks about "modular monolith architecture", "choreography vs orchestration", "saga pattern", "module structure", "how modules communicate", "bounded context", "when to use this architecture", "layer dependencies", "module DI registration", "multi-tenancy", "tenant context", "migration service", "outbox", or asks for an architectural overview of the MediHub backend.
---

# MediHub Backend: Modular Monolith Architecture (.NET 10)

The MediHub backend is a **single deployable unit** (`MediHub.Api`) divided into strongly bounded modules.
Modules communicate only through **integration events, saga commands and request/response contracts**
over RabbitMQ (MassTransit), never through direct calls or shared DbContexts.

It is **multi-tenant with a database per tenant** (tenant = hospital). Inside each tenant database every
module owns its own schema.

> **Read first:** `references/medihub-platform-conventions.md` covers names, tenancy, migrations,
> messaging rules (IDs only), authorization, encryption and logging. Every other backend skill relies on it.
> The project-level source of truth is `architecture/high-level-architecture.md`.

> **Bootstrap status:** no backend code exists yet. Code in these skills is either a **template** to
> generate or an **illustrative example** (Inventory, Orders, Payments, `OrderSaga`). The examples are
> **not modules of this system**. They only show the shape of the code.

## Module Structure (5 projects per module)

```
src/Modules/<Name>/
  MediHub.Modules.<Name>.Domain            → Entities, value objects, domain events, repository interfaces, errors
  MediHub.Modules.<Name>.Application       → Commands, queries, MediatR handlers, validators, permissions, I<Name>UnitOfWork
  MediHub.Modules.<Name>.Infrastructure    → DbContext, EF configurations, repositories, consumers, DI + migration registration
  MediHub.Modules.<Name>.IntegrationEvents → Event / saga-command / request-response contracts (pure contract library)
  MediHub.Modules.<Name>.Presentation      → Minimal API endpoints
```

## Key Design Decisions

| Decision | Detail |
|---|---|
| **Database per tenant, schema per module** | Each hospital has its own Postgres database; each module owns a schema in it. No cross-module joins. A central **catalog** database holds the tenant registry. |
| **Tenant context everywhere** | Resolved from the validated token (HTTP), the `medihub-tenant-id` header (messages), or an explicit tenant loop (jobs). Never from client input. |
| **Migration service** | `MediHub.MigrationService` migrates the catalog and every tenant database. The API never migrates. |
| **Module-specific IUnitOfWork** | Each module declares `I<Module>UnitOfWork` to prevent DI conflicts. |
| **CQRS via MediatR** | Commands and queries return `Result<T>`; pipeline behaviours handle logging (no payloads) and validation. |
| **Transactional outbox** | Domain events are written as `OutboxMessage` rows in the same transaction; a Quartz job dispatches them to domain event handlers, which publish integration messages. |
| **Messages carry IDs only** | No personal data in events, commands, outbox rows or saga state; details are fetched by request/response. |
| **Saga persistence** | MassTransit state machines with EF Core persistence in the owning module's tenant schema; optimistic concurrency via Postgres `xmin`. |
| **Authorization in the app** | Granular permissions declared per module, checked per endpoint, list filtering inside the query. |
| **Application-level encryption** | Selected personal-data fields are encrypted by EF configuration (`IsEncrypted()`). |

## Distributed Transaction Patterns

### Choreography
Modules react to events autonomously; there is no central coordinator. Each module publishes an event on
success, and downstream modules subscribe and continue. New steps are easy to add, but the end-to-end flow
is harder to trace.

### Orchestration (Saga)
A state machine in the owning module sends commands to each participating module in sequence and runs
compensating actions on failure. The control flow is explicit, so failures and rollbacks are easier to reason about.

Choose per feature: choreography for independent reactions, a saga when several modules must succeed or
be compensated together.

## Layer Dependency Rules

```
Presentation      → Application → Domain           (always inward)
Infrastructure    → Application, Domain, Common.Infrastructure
IntegrationEvents → (no project references)
API host          → every module's Infrastructure + Presentation, Common.Infrastructure
```

Cross-module: a module may reference **only** another module's `IntegrationEvents` project (from its
Infrastructure, or from its Application layer for saga commands). Never another module's Domain,
Application, Infrastructure or Presentation.

## DI Registration Pattern

Each module's Infrastructure project has a `<Module>Module` static class with three entry points:

```csharp
// Infrastructure/Extensions/<Module>Module.cs
public static class InventoryModule
{
    // 1. Services
    public static IServiceCollection AddInventoryModule(this IServiceCollection services, IConfiguration configuration)
    {
        services.AddTenantDbContext<InventoryDbContext>(schema: "inventory");   // tenant connection + outbox interceptor
        services.AddScoped<IInventoryUnitOfWork>(sp => sp.GetRequiredService<InventoryDbContext>());
        services.AddScoped<IProductRepository, ProductRepository>();
        services.AddScoped<IOutboxMessageProcessor, OutboxMessageProcessor<InventoryDbContext>>();
        services.AddApplication(typeof(Application.AssemblyReference).Assembly);   // MediatR + validators
        services.AddPermissions(InventoryPermissions.All);
        return services;
    }

    // 2. Consumers (and saga state machines)
    public static void ConfigureConsumers(IRegistrationConfigurator configurator)
    {
        configurator.AddConsumer<SomeEventConsumer>();
    }

    // 3. Migrations — used by MediHub.MigrationService
    public static void ConfigureMigrations(MigrationRegistry registry) =>
        registry.Tenant<InventoryDbContext>();
}
```

## Host Wiring

```csharp
// src/Api/MediHub.Api/Program.cs
builder.AddServiceDefaults();                                   // Aspire: OpenTelemetry, health checks, resilience

builder.Services.AddInventoryModule(builder.Configuration);      // one call per module

builder.Services.AddInfrastructure(                             // Common.Infrastructure
    [
        InventoryModule.ConfigureConsumers,                     // one entry per module
    ],
    builder.Configuration);                                     // MassTransit/RabbitMQ (ConnectionStrings:rabbitmq),
                                                                // tenant filters, outbox job, permission policy provider

var app = builder.Build();
app.UseAuthentication();
app.UseTenantResolution();                                      // tenant from the validated token
app.UseAuthorization();
app.MapEndpoints();                                             // calls each module's Map<Module>Endpoints()
app.Run();
```

```csharp
// src/Tools/MediHub.MigrationService/Program.cs
builder.Services.AddMigrationService(
    [
        InventoryModule.ConfigureMigrations,                    // one entry per module
    ],
    builder.Configuration);
```

`MapEndpoints()` lives in `src/Api/MediHub.Api/Extensions/WebApplicationExtensions.cs`. The API host is the
only place that knows about every Presentation project.

## Transactional Outbox Pattern

### The dual-write problem

Publishing to the broker directly after `SaveChangesAsync()` is a **dual write**. If the publish fails,
the database row exists but no message was sent, and the event is lost silently.

### How the outbox solves it

```
entity.RaiseDomainEvent(...)                       (IDs only — the event is stored in the outbox row)
unitOfWork.SaveChangesAsync()
  └─ OutboxMessagesInterceptor (EF SaveChanges interceptor)
       → writes OutboxMessage rows in the SAME transaction
         ↓ (background, Quartz job)
OutboxMessageProcessor<TDbContext>
  → reads rows WHERE ProcessedOnUtc IS NULL
  → deserialises to IDomainEvent
  → publisher.Publish(DomainEventNotification<T>)   [MediatR]
    ↓
IDomainEventHandler<T>
  → IEventBus.PublishAsync(integration message)     [MassTransit → RabbitMQ, tenant header added by filter]
  → row marked ProcessedOnUtc = UtcNow
```

> **Open decision.** The processor above works per database. With a database per tenant, delivery must
> span **every tenant database**, and several API replicas must not deliver the same row twice. This
> design is **deferred until it is revisited with the project owner** (architecture document, open items).
> Don't implement a multi-tenant variant on your own. Raise it if a task depends on it.

### Outbox processor error handling: critical rule

The catch block must **never** set `ProcessedOnUtc` on failure; only `Error`. Rows with
`ProcessedOnUtc == null` are retried on every poll; rows with it set are skipped forever.

```csharp
catch (Exception ex)
{
    logger.LogError(ex, "Outbox: failed to process message {Id}", message.Id);   // ID only, no payload
    message.Error = ex.ToString();
    // ProcessedOnUtc intentionally NOT set
}
```

### Where integration messages are published

**Never** from command handlers. The entity raises a domain event, the outbox stores it atomically, and
an `IDomainEventHandler<T>` publishes the integration message through `IEventBus`.

## When This Architecture Fits

- Teams of 3–15 developers whose modules map to domain or team boundaries
- Clean separation without microservice operations (one deployment per hospital group)
- Modules may later be extracted; integration events already form their contract

## Key Files

| File | Purpose |
|---|---|
| `src/Api/MediHub.Api/Program.cs` | Module wiring, broker config, middleware order |
| `src/Api/MediHub.Api/Extensions/WebApplicationExtensions.cs` | `MapEndpoints()` |
| `src/Tools/MediHub.MigrationService/Program.cs` | Migration registration for catalog and tenant databases |
| `src/Common/MediHub.Common.Infrastructure/Extensions/InfrastructureExtensions.cs` | `AddInfrastructure()`: MassTransit, tenant filters, outbox job, authorization |
| `src/Modules/*/MediHub.Modules.*.Infrastructure/Extensions/<Module>Module.cs` | `Add<Module>Module()`, `ConfigureConsumers()`, `ConfigureMigrations()` |
| `src/Aspire/MediHub.AppHost/` | Local orchestration: Postgres, RabbitMQ, Redis, Keycloak, API, migration service |
| `Directory.Packages.props` | Centralised NuGet versions |

## Additional Resources

- `references/medihub-platform-conventions.md`: tenancy, migrations, messaging, authorization, encryption, logging
- `references/architecture-deep-dive.md`: shared libraries, persistence, CQRS, consumers, choreography and saga flows
