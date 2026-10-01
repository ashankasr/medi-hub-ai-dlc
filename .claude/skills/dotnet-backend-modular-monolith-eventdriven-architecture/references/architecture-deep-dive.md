# Architecture Deep Dive

Cross-cutting rules (tenancy, migrations, IDs-only messages, authorization, encryption, logging) are in
`medihub-platform-conventions.md`. This file covers the internal structure.

Module names used below (Inventory, Orders, Payments, Notifications) are **illustrative examples**, not
modules of MediHub.

---

## Layer Dependency Rules (strictly enforced)

```
Presentation       →  Application  →  Domain
Infrastructure     →  Application + Domain + Common.Infrastructure
IntegrationEvents  →  (no project references)
API host           →  all module Infrastructure + Presentation projects, Common.Infrastructure
MigrationService   →  all module Infrastructure projects, Common.Infrastructure
```

**Cross-module rules:**
- Module A's Infrastructure **may** reference module B's `IntegrationEvents` (to consume B's events or call B via request/response)
- Module A's Application may reference module B's `IntegrationEvents` only for saga commands
- Never reference another module's `Domain`, `Application`, `Infrastructure` or `Presentation`

These rules are to be enforced by architecture tests (NetArchTest or ArchUnitNET) once the solution exists.

---

## Common Shared Libraries

```
MediHub.Common.Domain
  └── Primitives/
      ├── Entity<T>              → Id, DomainEvents list, equality by Id
      ├── AuditableEntity<T>     → + CreatedAt, UpdatedAt (UTC, set by BaseDbContext)
      ├── AuditableGuidEntity    → AuditableEntity<Guid> (default for aggregate roots)
      ├── DomainEvent / IDomainEvent → EventId, OccurredOn
      └── Results/
          ├── Result / Result<T> → Success(value) | Failure(error)
          └── Error              → (code, description, type): NotFound | Validation | Conflict | Failure

MediHub.Common.Application
  └── Abstractions/
      ├── ICommand / ICommand<T>, ICommandHandler<…>
      ├── IQuery<T>, IQueryHandler<…>
      ├── IRepository<T, TKey>, IUnitOfWork
      ├── IDomainEventHandler<T>, DomainEventNotification<T>
      ├── IEventBus              → abstraction over MassTransit publish
      ├── Tenancy/ITenantContext
      └── Identity/ICurrentUser, AccessScope
  └── Behaviors/
      ├── LoggingBehavior        → request TYPE name, elapsed time, outcome/error code (never payloads)
      └── ValidationBehavior     → runs FluentValidation; returns Result.Failure on invalid input
  └── Extensions/
      └── AddApplication(Assembly[])  → MediatR (with licence key) + validators

MediHub.Common.Infrastructure
  └── Persistence/   BaseDbContext (IUnitOfWork, audit timestamps, OutboxMessage config), BaseRepository<T,TKey,TCtx>,
                     AddTenantDbContext / AddCatalogDbContext, ITenantConnectionResolver
  └── Encryption/    IsEncrypted() EF extension, tenant data-key provider (local secret in dev, Key Vault in prod)
  └── Outbox/        OutboxMessage, OutboxMessagesInterceptor, OutboxMessageProcessor<TCtx>, Quartz job
  └── Messaging/     AddInfrastructure (MassTransit + RabbitMQ), tenant publish/send/consume filters, MassTransitEventBus
  └── Tenancy/       TenantResolutionMiddleware, ITenantJobRunner, TenantCacheKey
  └── Authorization/ permission policy provider, AddPermissions, CurrentUser
  └── Migrations/    MigrationRegistry, AddMigrationService
```

---

## Persistence: Database per Tenant, Schema per Module

```
catalog database (central)      → tenancy schema: tenants, connection info, key references
                                   (+ group-level data — scope still open)
medihub_<tenant> database        → one schema per module, e.g.
                                     inventory.Products, inventory.OutboxMessages, inventory.__EFMigrationsHistory
                                     orders.Orders, orders.OrderSagaState, orders.OutboxMessages, …
```

- Schema = lowercase module name, set with `modelBuilder.HasDefaultSchema("inventory")`.
- Each module keeps its migration history in its own schema (`MigrationsHistoryTable("__EFMigrationsHistory", "<schema>")`).
- The DbContext's connection is resolved per request/message/job from the tenant context. See conventions §2.
- Migrations are applied by `MediHub.MigrationService`, never by the API. See conventions §3.

---

## CQRS via MediatR

```csharp
public sealed record CancelOrderCommand(Guid OrderId, string ReasonCode) : ICommand<CancelOrderResponse>;
public sealed record GetOrderQuery(Guid OrderId) : IQuery<OrderResponse>;
```

Pipeline behaviours (registered globally via `AddApplication`):
1. `LoggingBehavior`: request type name, elapsed time, success or error code. **No payloads.**
2. `ValidationBehavior`: runs FluentValidation and returns `Result.Failure(...)` if the input is invalid.

Authorization happens at the endpoint (`RequireAuthorization(permission)`). Record-level scope is applied
inside repository queries. See conventions §5.

---

## MassTransit Consumer Pattern

```csharp
public sealed class OrderPlacedInventoryConsumer(
    IProductRepository productRepo,
    InventoryDbContext dbContext,
    ILogger<OrderPlacedInventoryConsumer> logger) : IConsumer<OrderPlacedEvent>
{
    public async Task Consume(ConsumeContext<OrderPlacedEvent> context)
    {
        // Tenant context was set by the consume filter from the medihub-tenant-id header,
        // so dbContext already points at the right tenant database.
        logger.LogInformation("[CHOREOGRAPHY] Inventory received OrderPlacedEvent for Order {OrderId}", context.Message.OrderId);
        // ... business logic ...
        await context.Publish(new StockReservedEvent(...));   // tenant header propagated automatically
    }
}
```

Consumers are registered through each module's `ConfigureConsumers` and bound with `cfg.ConfigureEndpoints(ctx)`
in `AddInfrastructure`. **Retry policy:** 3 attempts at 100 ms → 500 ms → 1 s.

---

## Choreography Flow (illustrative)

```
POST /api/orders
  └─ PlaceOrderCommand (MediatR) → Order created → OrderPlacedDomainEvent → outbox
      └─ OrderPlacedDomainEventHandler → publishes OrderPlacedEvent (IDs only)
          └─ OrderPlacedInventoryConsumer (Inventory) → reserves stock → StockReservedEvent
              └─ StockReservedPaymentConsumer (Payments) → PaymentProcessedEvent
                  └─ PaymentProcessedNotificationConsumer (Notifications)
                       → fetches recipient details via request/response, sends notification
              └─ StockReservedOrderUpdater (Orders) → updates status
          └─ StockReservationFailedEvent (reason CODE) → Orders marks failed
```

No central coordinator. Each module reacts to what it sees on the bus.

---

## Orchestration / Saga Flow (illustrative)

```
POST /api/orders/orchestrated
  └─ StartOrderCommand → Order created → domain event → outbox → OrderSagaStartMessage (IDs only)
      └─ [Saga] Submitted → sends ReserveStockCommand
          ↳ StockReservedEvent        → [Saga] StockReserved → sends ProcessPaymentCommand
              ↳ PaymentProcessedEvent → [Saga] sends SendOrderNotificationCommand → Completed + Finalize
              ↳ PaymentFailedEvent    → [Saga] sends ReleaseStockCommand (compensation)
                                               → sends SendOrderNotificationCommand → Failed + Finalize
          ↳ StockReservationFailedEvent → [Saga] sends SendOrderNotificationCommand → Failed + Finalize
```

Saga state is persisted in the owning module's schema of the **tenant database** with optimistic
concurrency (Postgres `xmin`). It stores IDs and status only.

---

## Technology Stack Rationale

| Concern | Library | Why |
|---|---|---|
| Messaging | MassTransit v9 + RabbitMQ | Abstracts the broker; sagas, retry, request/response, consumer binding |
| Saga persistence | MassTransit.EntityFrameworkCore (Postgres lock provider) | Reuses the module DbContext; optimistic concurrency |
| ORM | EF Core 10 + Npgsql | Schema per module via `HasDefaultSchema()`; database per tenant |
| CQRS | MediatR | Clean separation; pipeline behaviours for cross-cutting concerns |
| Validation | FluentValidation | Wired automatically through the MediatR pipeline |
| Mapping | Mapster | Fast and minimal-API friendly |
| Outbox scheduling | Quartz | Periodic outbox processing |
| Observability | OpenTelemetry via Aspire ServiceDefaults | Aspire dashboard locally, Grafana in production |
| API reference | Scalar (from the OpenAPI document) | Better developer experience; the same OpenAPI document feeds orval for the frontends |

---

## Transactional Outbox Pattern

See SKILL.md for the flow, the error-handling rule and the **open multi-tenant delivery decision**.

| Layer | Responsibility |
|---|---|
| Command handler | Create or change the aggregate, call `SaveChangesAsync`, nothing else |
| Domain entity | `RaiseDomainEvent(new XyzDomainEvent(...))` with **IDs only** on meaningful state changes |
| `IDomainEventHandler<T>` | Re-fetch the aggregate if needed, build the integration message (IDs only), publish via `IEventBus` |

The handler may load the aggregate because the transaction has already committed by the time it runs.

---

## When to Choose a Modular Monolith

**Choose it when:**
- 3–15 developers; modules map to team or domain boundaries
- You want clean separation without microservice operations
- You may extract a module later; integration events are already its contract

**Avoid it when:**
- Modules need radically different scaling profiles
- Modules need different tech stacks or runtimes
- The team is so large that coordination costs more than deployment coupling
