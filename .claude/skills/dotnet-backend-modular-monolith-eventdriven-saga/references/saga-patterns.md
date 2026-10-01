# Saga Orchestration: Complete Reference

`OrderSaga` and the Orders, Inventory, Payments and Notifications modules are **illustrative**. No saga
exists in MediHub yet. Cross-cutting rules: `../../dotnet-backend-modular-monolith-eventdriven-architecture/references/medihub-platform-conventions.md`.

---

## 1. What a Saga Is

A **saga** is a long-running process that coordinates steps across modules. Each step is a message exchange:

```
Saga sends command → module consumer processes it → module publishes result event → saga transitions
```

If a step fails, the saga runs compensating actions in reverse to restore consistency. MediHub uses
**MassTransit's `MassTransitStateMachine<TState>`**, where every state, event and transition is explicit
C# code. A saga lives in the owning module: `Application/Saga/<Name>Saga.cs` and `<Name>SagaState.cs`.

---

## 2. Anatomy of the Saga Class

```csharp
public sealed class OrderSaga : MassTransitStateMachine<OrderSagaState>
{
    private readonly ILogger<OrderSaga> _logger;

    // ── States: points where the saga waits for a reply (Initial/Final are implicit)
    public State Submitted     { get; private set; } = null!;
    public State StockReserved { get; private set; } = null!;
    public State Completed     { get; private set; } = null!;
    public State Failed        { get; private set; } = null!;

    // ── Events: message types the saga can receive
    public Event<OrderSagaStartMessage>       Started               { get; private set; } = null!;
    public Event<StockReservedEvent>          StockWasReserved      { get; private set; } = null!;
    public Event<StockReservationFailedEvent> StockReservationFailed{ get; private set; } = null!;
    public Event<PaymentProcessedEvent>       PaymentWasProcessed   { get; private set; } = null!;
    public Event<PaymentFailedEvent>          PaymentFailed         { get; private set; } = null!;

    public OrderSaga(ILogger<OrderSaga> logger)
    {
        _logger = logger;

        InstanceState(x => x.CurrentState);

        Event(() => Started,                x => x.CorrelateById(ctx => ctx.Message.CorrelationId));
        Event(() => StockWasReserved,       x => x.CorrelateById(ctx => ctx.Message.CorrelationId));
        Event(() => StockReservationFailed, x => x.CorrelateById(ctx => ctx.Message.CorrelationId));
        Event(() => PaymentWasProcessed,    x => x.CorrelateById(ctx => ctx.Message.CorrelationId));
        Event(() => PaymentFailed,          x => x.CorrelateById(ctx => ctx.Message.CorrelationId));

        Initially( ... );
        During(Submitted, ... );
        During(StockReserved, ... );

        SetCompletedWhenFinalized();   // removes the saga row once finalized
    }
}
```

---

## 3. State Machine DSL: Full Reference

### `Initially`: handles the first event

```csharp
Initially(
    When(Started)
        .Then(ctx =>
        {
            ctx.Saga.OrderId     = ctx.Message.OrderId;
            ctx.Saga.CustomerId  = ctx.Message.CustomerId;   // an ID — contact details are fetched when needed
            ctx.Saga.TotalAmount = ctx.Message.TotalAmount;
            ctx.Saga.StartedAt   = DateTime.UtcNow;
            _logger.LogInformation("[SAGA] Order {OrderId} saga started.", ctx.Saga.OrderId);
        })
        .PublishAsync(ctx => ctx.Init<ReserveStockCommand>(new ReserveStockCommand(
            ctx.Saga.CorrelationId,
            ctx.Saga.OrderId,
            ctx.Message.Items)))
        .TransitionTo(Submitted));
```

### `During`: handles events in a specific state

```csharp
During(Submitted,

    When(StockWasReserved)
        .Then(ctx =>
        {
            ctx.Saga.ReservationId = ctx.Message.ReservationId;
            _logger.LogInformation("[SAGA] Stock reserved for Order {OrderId}.", ctx.Saga.OrderId);
        })
        .PublishAsync(ctx => ctx.Init<ProcessPaymentCommand>(new ProcessPaymentCommand(
            ctx.Saga.CorrelationId,
            ctx.Saga.OrderId,
            ctx.Saga.CustomerId,
            ctx.Saga.TotalAmount)))
        .TransitionTo(StockReserved),

    When(StockReservationFailed)
        .Then(ctx =>
        {
            ctx.Saga.FailureReasonCode = ctx.Message.ReasonCode;
            _logger.LogWarning("[SAGA] Stock reservation FAILED for Order {OrderId}: {ReasonCode}",
                ctx.Saga.OrderId, ctx.Message.ReasonCode);
        })
        .PublishAsync(ctx => ctx.Init<SendOrderNotificationCommand>(new SendOrderNotificationCommand(
            ctx.Saga.CorrelationId, ctx.Saga.OrderId, ctx.Saga.CustomerId,
            NotificationTemplate.OrderFailed, ctx.Saga.FailureReasonCode)))
            // the Notifications module fetches recipient details itself (request/response)
        .TransitionTo(Failed)
        .Finalize());
```

### Compensation inside `During`

```csharp
During(StockReserved,
    When(PaymentFailed)
        .Then(ctx =>
        {
            ctx.Saga.FailureReasonCode = ctx.Message.ReasonCode;
            _logger.LogWarning("[SAGA] Payment FAILED for Order {OrderId}. Releasing stock.", ctx.Saga.OrderId);
        })
        // 1. Compensating action
        .PublishAsync(ctx => ctx.Init<ReleaseStockCommand>(new ReleaseStockCommand(
            ctx.Saga.CorrelationId, ctx.Saga.OrderId, ctx.Saga.ReservationId!.Value)))
        // 2. Notify
        .PublishAsync(ctx => ctx.Init<SendOrderNotificationCommand>(new SendOrderNotificationCommand(
            ctx.Saga.CorrelationId, ctx.Saga.OrderId, ctx.Saga.CustomerId,
            NotificationTemplate.OrderFailed, ctx.Saga.FailureReasonCode)))
        .TransitionTo(Failed)
        .Finalize());
```

### DSL summary

| Method | Purpose |
|---|---|
| `When(Event)` | Matches an event in the current state block |
| `.Then(ctx => ...)` | Synchronous side effect: update saga state, log (IDs only) |
| `.PublishAsync(ctx => ctx.Init<T>(new T(...)))` | Publish a command or event (tenant header propagated automatically) |
| `.TransitionTo(State)` | Move to a new state; persists `CurrentState` |
| `.Finalize()` | Mark the saga complete; `SetCompletedWhenFinalized()` deletes the row |
| `InstanceState(x => x.CurrentState)` | Which property stores the state name |
| `Event(() => E, x => x.CorrelateById(...))` | How incoming messages find their instance |

---

## 4. Saga State

```csharp
public sealed class OrderSagaState : SagaStateMachineInstance
{
    public Guid      CorrelationId     { get; set; }                   // PK
    public string    CurrentState      { get; set; } = string.Empty;
    public uint      Version           { get; set; }                   // optimistic concurrency (Postgres xmin)

    public Guid      OrderId           { get; set; }
    public Guid      CustomerId        { get; set; }                   // ID only
    public decimal   TotalAmount       { get; set; }
    public Guid?     ReservationId     { get; set; }
    public Guid?     PaymentId         { get; set; }
    public string?   FailureReasonCode { get; set; }                   // a code, not free text
    public DateTime  StartedAt         { get; set; }                   // UTC
    public DateTime? CompletedAt       { get; set; }
}
```

**Rules:**
- `CorrelationId` is the primary key
- One nullable property per resource ID produced by a step
- Store the **minimum** needed to send later commands: IDs, amounts, status, reason codes
- **No personal data** (no names, e-mail addresses, contact details or clinical data). Saga state is data at rest; the modules that need details fetch them by request/response.

---

## 5. Adding a New Step (Worked Example)

**Scenario:** add a shipping step after payment.

1. **State and events**

```csharp
public State PaymentProcessed { get; private set; } = null!;
public Event<ShipmentCreatedEvent> ShipmentCreated { get; private set; } = null!;
public Event<ShipmentFailedEvent>  ShipmentFailed  { get; private set; } = null!;
```

2. **Correlation**

```csharp
Event(() => ShipmentCreated, x => x.CorrelateById(ctx => ctx.Message.CorrelationId));
Event(() => ShipmentFailed,  x => x.CorrelateById(ctx => ctx.Message.CorrelationId));
```

3. **Point the previous step at the new state**

```csharp
During(StockReserved,
    When(PaymentWasProcessed)
        .Then(ctx => ctx.Saga.PaymentId = ctx.Message.PaymentId)
        .PublishAsync(ctx => ctx.Init<CreateShipmentCommand>(new CreateShipmentCommand(
            ctx.Saga.CorrelationId, ctx.Saga.OrderId, ctx.Saga.CustomerId)))
        .TransitionTo(PaymentProcessed),
```

4. **New `During` block with success and failure (compensation in reverse order)**

```csharp
During(PaymentProcessed,
    When(ShipmentCreated)
        .Then(ctx => { ctx.Saga.ShipmentId = ctx.Message.ShipmentId; ctx.Saga.CompletedAt = DateTime.UtcNow; })
        .PublishAsync(ctx => ctx.Init<SendOrderNotificationCommand>(new SendOrderNotificationCommand(
            ctx.Saga.CorrelationId, ctx.Saga.OrderId, ctx.Saga.CustomerId, NotificationTemplate.OrderShipped, null)))
        .TransitionTo(Completed)
        .Finalize(),

    When(ShipmentFailed)
        .Then(ctx => ctx.Saga.FailureReasonCode = ctx.Message.ReasonCode)
        .PublishAsync(ctx => ctx.Init<RefundPaymentCommand>(new RefundPaymentCommand(
            ctx.Saga.CorrelationId, ctx.Saga.OrderId, ctx.Saga.PaymentId!.Value)))
        .PublishAsync(ctx => ctx.Init<ReleaseStockCommand>(new ReleaseStockCommand(
            ctx.Saga.CorrelationId, ctx.Saga.OrderId, ctx.Saga.ReservationId!.Value)))
        .PublishAsync(ctx => ctx.Init<SendOrderNotificationCommand>(new SendOrderNotificationCommand(
            ctx.Saga.CorrelationId, ctx.Saga.OrderId, ctx.Saga.CustomerId,
            NotificationTemplate.OrderFailed, ctx.Saga.FailureReasonCode)))
        .TransitionTo(Failed)
        .Finalize());
```

5. **State property:** `public Guid? ShipmentId { get; set; }`

6. **Contracts** (in `MediHub.Modules.Shipping.IntegrationEvents`, IDs and codes only):

```csharp
public sealed record CreateShipmentCommand(Guid CorrelationId, Guid OrderId, Guid CustomerId);
public sealed record ShipmentCreatedEvent(Guid CorrelationId, Guid OrderId, Guid ShipmentId, DateTime OccurredAt);
public sealed record ShipmentFailedEvent(Guid CorrelationId, Guid OrderId, string ReasonCode, DateTime OccurredAt);
```

7. **Consumer** in the target module (integration-events-consumers skill)

8. **Migration** for the saga state change

```bash
dotnet ef migrations add AddShipmentIdToOrderSagaState \
  --project src/Modules/Orders/MediHub.Modules.Orders.Infrastructure \
  --startup-project src/Modules/Orders/MediHub.Modules.Orders.Infrastructure \
  --context OrdersDbContext
```

The migration service applies it to every tenant database.

---

## 6. Saga Persistence: EF Core in the Tenant Database

The saga state lives in the owning module's schema **inside each tenant's database** (e.g.
`orders.OrderSagaState`). The module DbContext is tenant-scoped, and the consume filter sets the tenant
from the message header before the saga loads its instance. So each hospital's sagas live in its own database.

### Registration (in the owning module's `ConfigureConsumers`)

```csharp
public static void ConfigureConsumers(IRegistrationConfigurator configurator)
{
    configurator.AddSagaStateMachine<OrderSaga, OrderSagaState>()
        .EntityFrameworkRepository(r =>
        {
            r.ConcurrencyMode = ConcurrencyMode.Optimistic;   // uses the xmin-mapped Version property
            r.ExistingDbContext<OrdersDbContext>();
            r.UsePostgres();                                  // Postgres SQL dialect / lock statements
        });
}
```

### Mapping (in a `<Name>SagaStateConfiguration` class)

```csharp
public sealed class OrderSagaStateConfiguration : IEntityTypeConfiguration<OrderSagaState>
{
    public void Configure(EntityTypeBuilder<OrderSagaState> b)
    {
        b.ToTable("OrderSagaState");
        b.HasKey(s => s.CorrelationId);
        b.Property(s => s.CurrentState).IsRequired().HasMaxLength(64);
        b.Property(s => s.Version).IsRowVersion();          // Postgres xmin
        b.Property(s => s.FailureReasonCode).HasMaxLength(100);
        b.Property(s => s.TotalAmount).HasPrecision(18, 2);
    }
}
```

> **Related open decision:** the outbox's delivery across tenant databases is deferred (architecture
> skill). Sagas started from domain events depend on it, so raise it if a saga task is blocked by it.

---

## 7. Correlation and Tenancy

Every message the saga handles carries a `CorrelationId`:

```csharp
// The domain event handler that starts the saga (IDs only):
await eventBus.PublishAsync(new OrderSagaStartMessage(Guid.CreateVersion7(), order.Id, order.CustomerId, order.TotalAmount, items), ct);

// Saga instance primary key:
public Guid CorrelationId { get; set; }

// Correlation per event:
Event(() => StockWasReserved, x => x.CorrelateById(ctx => ctx.Message.CorrelationId));

// Consumers echo the CorrelationId on their result events:
await context.Publish(new StockReservedEvent(msg.CorrelationId, msg.OrderId, reservationId, DateTime.UtcNow));
```

The **tenant** is never a contract field. The `medihub-tenant-id` header is added on publish and restored
on consume by the Common filters, so every step of a saga stays in the same hospital's database.

---

## 8. Checklist: Adding or Changing a Saga

- [ ] Saga lives in the owning module's `Application/Saga/`
- [ ] `State` properties for new waiting states
- [ ] `Event<T>` properties for success and failure events, with `CorrelateById` registrations
- [ ] Previous transition now goes to the new state instead of `Completed`/`Finalize`
- [ ] `During(NewState, When(Success)..., When(Failure)...)` block
- [ ] Compensation `PublishAsync` calls on the failure path, in reverse order of the steps
- [ ] New state properties are IDs, amounts, status or reason codes only
- [ ] Contracts added to the relevant `IntegrationEvents` projects (IDs only)
- [ ] Consumers added in target modules, idempotent
- [ ] Migration added for saga state changes (applied by the migration service)
