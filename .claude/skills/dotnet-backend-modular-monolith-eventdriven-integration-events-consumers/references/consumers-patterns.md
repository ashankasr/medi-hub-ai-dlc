# Integration Events, Request/Response & Consumers: Complete Reference

Module names (Orders, Inventory, Payments, Notifications) are **illustrative**, not MediHub modules.
Cross-cutting rules: `../../dotnet-backend-modular-monolith-eventdriven-architecture/references/medihub-platform-conventions.md`.

---

## 1. Contracts

### Where they live

Each module owns one `IntegrationEvents` project:

```
src/Modules/<Name>/MediHub.Modules.<Name>.IntegrationEvents/
  <EventName>.cs          ← events published by this module
  <CommandName>.cs        ← saga commands sent TO this module
  Get<Thing>Details.cs    ← request/response contracts this module ANSWERS
  AssemblyReference.cs
```

The `IntegrationEvents` project has **no project references**. It is a pure contract library.

### Shape

```csharp
// Event — something happened (past tense, immutable)
public sealed record OrderCancelledEvent(
    Guid OrderId,
    string ReasonCode,          // a code, not free text
    DateTime CancelledAt);

// Saga command — instruction from the saga to a module
public sealed record ReserveStockCommand(
    Guid CorrelationId,         // required for saga correlation
    Guid OrderId,
    List<ReserveStockItem> Items);
public sealed record ReserveStockItem(Guid ProductId, int Quantity);

// Result events — published back to the saga
public sealed record StockReservedEvent(Guid CorrelationId, Guid OrderId, Guid ReservationId, DateTime OccurredAt);
public sealed record StockReservationFailedEvent(Guid CorrelationId, Guid OrderId, string ReasonCode, DateTime OccurredAt);

// Request/response — owned by the module that holds the data
public sealed record GetProductDetails(Guid ProductId);
public sealed record ProductDetails(Guid ProductId, string Name, string Sku);
public sealed record ProductNotFound(Guid ProductId);
```

**Rules:**
- Always `sealed record`, immutable
- `CorrelationId` on every event or command that takes part in a saga
- A timestamp (`OccurredAt` / `CancelledAt`, UTC) on events
- Only primitives, `Guid`, enums/codes and nested records; no domain objects or EF entities
- **Events and saga commands carry IDs, codes, amounts and timestamps only.** No names, e-mail addresses, phone numbers, addresses, national IDs, dates of birth, diagnoses or clinical free text. Failure reasons are **codes**.
- Personal data may appear **only** in request/response **responses**, limited to what the caller needs (section 7)
- The tenant is **not** a field on the contract. It travels in the `medihub-tenant-id` header, added and read by the Common filters.

---

## 2. Cross-Module Project References

A consumer in module A that reacts to module B's event, or calls B by request/response, references B's
`IntegrationEvents` project:

```xml
<!-- MediHub.Modules.Inventory.Infrastructure.csproj — needs Orders' contracts -->
<ProjectReference Include="..\..\Orders\MediHub.Modules.Orders.IntegrationEvents\MediHub.Modules.Orders.IntegrationEvents.csproj" />
```

**Allowed:**
- `Infrastructure` → another module's `IntegrationEvents` ✅
- `Application` → another module's `IntegrationEvents` ✅ (saga commands only)
- Anything → another module's `Domain`, `Application`, `Infrastructure` or `Presentation` ❌ never

---

## 3. Consumer Anatomy

```
Infrastructure/
  Consumers/
    <MessageName>Consumer.cs     ← one consumer per message type
```

**Tenant context.** Before `Consume` runs, the Common consume filter reads the `medihub-tenant-id` header
and sets `ITenantContext`. So the injected module DbContext is already connected to that tenant's database.
A message without the header is rejected. Never pick a tenant inside a consumer.

**Dependency rules:**
- Inject the module's **own** repositories and DbContext only (DbContext, not `IUnitOfWork`; consumers live in Infrastructure)
- Inject `ILogger<T>` and log with the `[ORCHESTRATION]` / `[CHOREOGRAPHY]` / `[REQUEST]` prefix, **IDs only**
- Do **not** inject `ISender` (MediatR); the consumer is the handler
- Pass `context.CancellationToken` to every async call
- Use unscoped repository methods (system work, not a user request)

---

## 4. Orchestration Consumer (Saga Command → Result Event)

```csharp
public sealed class ReserveStockCommandConsumer(
    IProductRepository productRepository,
    IStockReservationRepository reservationRepository,
    InventoryDbContext dbContext,
    ILogger<ReserveStockCommandConsumer> logger) : IConsumer<ReserveStockCommand>
{
    public async Task Consume(ConsumeContext<ReserveStockCommand> context)
    {
        var msg = context.Message;
        logger.LogInformation("[ORCHESTRATION] Inventory received ReserveStockCommand for Order {OrderId}", msg.OrderId);

        // Idempotency: already reserved for this order? reply again and stop
        var existing = await reservationRepository.GetByOrderIdAsync(msg.OrderId, context.CancellationToken);
        if (existing is not null)
        {
            await context.Publish(new StockReservedEvent(msg.CorrelationId, msg.OrderId, existing.Id, DateTime.UtcNow));
            return;
        }

        var products = await productRepository.GetByIdsAsync(
            msg.Items.Select(i => i.ProductId).ToList(), context.CancellationToken);

        foreach (var item in msg.Items)
        {
            var product = products.FirstOrDefault(p => p.Id == item.ProductId);
            if (product is null || !product.HasSufficientStock(item.Quantity))
            {
                var reasonCode = product is null ? "Inventory.ProductNotFound" : "Inventory.InsufficientStock";
                await context.Publish(new StockReservationFailedEvent(msg.CorrelationId, msg.OrderId, reasonCode, DateTime.UtcNow));
                return;   // early return before any state change
            }
        }

        var reservation = StockReservation.Create(Guid.CreateVersion7(), msg.OrderId,
            msg.Items.Select(i => new ReservationItem(i.ProductId, i.Quantity)).ToList());

        foreach (var item in msg.Items)
            products.First(p => p.Id == item.ProductId).ReserveStock(item.Quantity);

        reservationRepository.Add(reservation);
        await dbContext.SaveChangesAsync(context.CancellationToken);

        await context.Publish(new StockReservedEvent(msg.CorrelationId, msg.OrderId, reservation.Id, DateTime.UtcNow));
    }
}
```

**Pattern:** idempotency guard → validate preconditions → on failure publish the failure event (reason
**code**) and return → on success mutate, save, publish the success event. Always echo `CorrelationId`.

---

## 5. Choreography Consumer (Autonomous Reaction, No Reply)

```csharp
public sealed class OrderCancelledPaymentConsumer(
    IPaymentRepository paymentRepository,
    PaymentsDbContext dbContext,
    ILogger<OrderCancelledPaymentConsumer> logger) : IConsumer<OrderCancelledEvent>
{
    public async Task Consume(ConsumeContext<OrderCancelledEvent> context)
    {
        var msg = context.Message;
        logger.LogInformation("[CHOREOGRAPHY] Payments received OrderCancelledEvent for Order {OrderId}", msg.OrderId);

        var payment = await paymentRepository.GetByOrderIdAsync(msg.OrderId, context.CancellationToken);
        if (payment is null || payment.IsRefunded) return;   // idempotent guard

        payment.Refund();
        await dbContext.SaveChangesAsync(context.CancellationToken);
    }
}
```

Delivery is **at least once**: outbox retries and broker redelivery mean the same message can arrive
twice. Every consumer needs an idempotency guard.

---

## 6. Compensation Consumer (Undo a Previous Step)

```csharp
public sealed class ReleaseStockCommandConsumer(
    IProductRepository productRepository,
    IStockReservationRepository reservationRepository,
    InventoryDbContext dbContext,
    ILogger<ReleaseStockCommandConsumer> logger) : IConsumer<ReleaseStockCommand>
{
    public async Task Consume(ConsumeContext<ReleaseStockCommand> context)
    {
        var msg = context.Message;
        logger.LogInformation("[ORCHESTRATION] Releasing reservation {ReservationId}", msg.ReservationId);

        var reservation = await reservationRepository.GetByIdAsync(msg.ReservationId, context.CancellationToken);
        if (reservation is null || reservation.IsReleased)
        {
            await context.Publish(new StockReleasedEvent(msg.CorrelationId, msg.OrderId, msg.ReservationId, DateTime.UtcNow));
            return;   // already undone — idempotent
        }

        var products = await productRepository.GetByIdsAsync(
            reservation.Items.Select(i => i.ProductId).ToList(), context.CancellationToken);
        foreach (var item in reservation.Items)
            products.FirstOrDefault(p => p.Id == item.ProductId)?.ReleaseStock(item.Quantity);

        reservation.Release();
        await dbContext.SaveChangesAsync(context.CancellationToken);

        await context.Publish(new StockReleasedEvent(msg.CorrelationId, msg.OrderId, msg.ReservationId, DateTime.UtcNow));
    }
}
```

Compensation consumers are always idempotent, always publish a completion event so the saga can continue,
and receive the resource ID on the command.

---

## 7. Request/Response: Fetching Details from the Owning Module

Use this when a consumer or handler needs data that events deliberately don't carry (e.g. a display
name or contact details for a notification).

### Responder: in the module that owns the data

```csharp
// Infrastructure/Consumers/GetProductDetailsConsumer.cs
public sealed class GetProductDetailsConsumer(
    InventoryDbContext dbContext,
    ILogger<GetProductDetailsConsumer> logger) : IConsumer<GetProductDetails>
{
    public async Task Consume(ConsumeContext<GetProductDetails> context)
    {
        logger.LogInformation("[REQUEST] Product details requested for {ProductId}", context.Message.ProductId);

        var product = await dbContext.Products.AsNoTracking()
            .FirstOrDefaultAsync(p => p.Id == context.Message.ProductId, context.CancellationToken);

        if (product is null)
            await context.RespondAsync(new ProductNotFound(context.Message.ProductId));
        else
            await context.RespondAsync(new ProductDetails(product.Id, product.Name, product.Sku));   // decrypted only in memory
    }
}
```

### Requester: in the module that needs the data

```csharp
public sealed class OrderCompletedNotificationConsumer(
    IRequestClient<GetProductDetails> productDetails,
    INotificationSender sender,
    ILogger<OrderCompletedNotificationConsumer> logger) : IConsumer<OrderCompletedEvent>
{
    public async Task Consume(ConsumeContext<OrderCompletedEvent> context)
    {
        var response = await productDetails.GetResponse<ProductDetails, ProductNotFound>(
            new GetProductDetails(context.Message.ProductId), context.CancellationToken);

        if (response.Is(out Response<ProductDetails>? details))
            await sender.SendAsync(/* uses details.Message — never logged, never stored */);
        else
            logger.LogWarning("[CHOREOGRAPHY] Product {ProductId} not found", context.Message.ProductId);
    }
}
```

**Rules:**
- The responder applies the same tenant: the tenant header propagates on the request, and the response comes from that tenant's database
- Responses carry **only** the fields the caller needs
- Never **log** response payloads, **store** them in saga state or outbox rows, or **re-publish** them in events
- Register the request client with `configurator.AddRequestClient<GetProductDetails>()` in the requester's `ConfigureConsumers`
- Whether responses carrying personal data must also be encrypted in transit through the broker is an **open item** in the architecture document

---

## 8. Consumer Registration

```csharp
// <Module>Module.cs
public static void ConfigureConsumers(IRegistrationConfigurator configurator)
{
    // Orchestration
    configurator.AddConsumer<ReserveStockCommandConsumer>();
    configurator.AddConsumer<ReleaseStockCommandConsumer>();

    // Choreography
    configurator.AddConsumer<OrderCancelledInventoryConsumer>();

    // Request/response
    configurator.AddConsumer<GetProductDetailsConsumer>();            // responder
    configurator.AddRequestClient<GetCustomerContact>();              // requester (if this module asks others)
}
```

```csharp
// src/Api/MediHub.Api/Program.cs
builder.Services.AddInfrastructure(
    [
        InventoryModule.ConfigureConsumers,   // ← one entry per module
    ],
    builder.Configuration);
```

`AddInfrastructure` binds every consumer to its queue with `cfg.ConfigureEndpoints(context)` and registers
the tenant filters.

---

## 9. Checklist: Adding a Consumer

- [ ] Contract added to the **owning** module's `IntegrationEvents` project
- [ ] Contract contains IDs, codes, amounts and timestamps only (responses: minimum needed fields)
- [ ] `ProjectReference` to that `IntegrationEvents` project added to the consuming module's Infrastructure `.csproj`
- [ ] Consumer created in `Infrastructure/Consumers/<MessageName>Consumer.cs`
- [ ] Injects only the module's own repositories, DbContext and `ILogger<T>`
- [ ] Idempotency guard (check whether the work is already done; return early)
- [ ] Preconditions validated before any state change
- [ ] `dbContext.SaveChangesAsync(context.CancellationToken)` after mutations
- [ ] Reply/result event published if orchestration; nothing if choreography
- [ ] Logs contain IDs only
- [ ] Registered in `<Module>Module.ConfigureConsumers()`

---

## 10. Decision Guide: Consumer vs Domain Event Handler vs Request/Response

| Scenario | Use |
|---|---|
| Another module publishes an event | `IConsumer<T>` in `Infrastructure/Consumers/` |
| This module's own state change must trigger an integration message | Domain event → outbox → `IDomainEventHandler<T>` (CQRS skill) |
| A saga sends a command to this module | `IConsumer<T>`; publish a success or failure event back |
| Cross-module compensation | `IConsumer<T>` for the compensation command |
| A module needs details owned by another module | Request/response (`IRequestClient<T>` + responder consumer) |
| Several reactions to the same event | Multiple consumers or handlers; both patterns fan out |
