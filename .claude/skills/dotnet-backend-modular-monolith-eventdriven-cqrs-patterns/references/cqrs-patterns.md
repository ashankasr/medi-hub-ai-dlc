# CQRS Patterns: Complete Reference

Module names below (Inventory, Orders) are **illustrative**, not MediHub modules.
Cross-cutting rules: `../../dotnet-backend-modular-monolith-eventdriven-architecture/references/medihub-platform-conventions.md`.

---

## 1. CQRS Type Hierarchy

### Interfaces (from `MediHub.Common.Application.Abstractions`)

```
ICommand                           → write operation, no return value  → IRequest<Result>
ICommand<TResponse>                → write operation, returns data      → IRequest<Result<TResponse>>
IQuery<TResponse>                  → read operation, always returns     → IRequest<Result<TResponse>>

ICommandHandler<TCommand>          → handles ICommand
ICommandHandler<TCommand, TRes>    → handles ICommand<TRes>
IQueryHandler<TQuery, TRes>        → handles IQuery<TRes>
```

**Rule:** commands mutate state, queries only read. Never mix them.

---

## 2. Command: Definition

File: `Application/<Feature>/<Action><Entity>/<Action><Entity>Command.cs`

```csharp
public sealed record DeleteProductCommand(Guid ProductId) : ICommand;

public sealed record CreateProductCommand(
    string Name,
    string Sku,
    Guid DepartmentId,
    int StockQuantity,
    decimal Price) : ICommand<Guid>;
```

- Always `sealed record`
- Positional parameters are the input data
- No logic; a pure data carrier

---

## 3. Command Handler: Definition

File: `Application/<Feature>/<Action><Entity>/<Action><Entity>CommandHandler.cs`

### With Unit of Work

```csharp
public sealed class CreateProductCommandHandler(
    IProductRepository productRepository,
    IInventoryUnitOfWork unitOfWork) : ICommandHandler<CreateProductCommand, Guid>
{
    public async Task<Result<Guid>> Handle(CreateProductCommand command, CancellationToken cancellationToken)
    {
        var productResult = Product.Create(
            Guid.CreateVersion7(), command.Name, command.Sku, command.DepartmentId, command.StockQuantity, command.Price);
        if (productResult.IsFailure)
            return Result.Failure<Guid>(productResult.Error);

        productRepository.Add(productResult.Value);
        await unitOfWork.SaveChangesAsync(cancellationToken);   // domain events → outbox rows, same transaction
        return productResult.Value.Id;                          // implicit TValue → Result<TValue>
    }
}
```

### With a failure path and access scope

```csharp
public sealed class CancelOrderCommandHandler(
    IOrderRepository orderRepository,
    IOrdersUnitOfWork unitOfWork,
    ICurrentUser currentUser) : ICommandHandler<CancelOrderCommand, CancelOrderResponse>
{
    public async Task<Result<CancelOrderResponse>> Handle(CancelOrderCommand command, CancellationToken cancellationToken)
    {
        // Scope applied in the query: an order outside the user's scope is simply "not found"
        var order = await orderRepository.GetByIdAsync(command.OrderId, currentUser.Scope, cancellationToken);
        if (order is null)
            return Result.Failure<CancelOrderResponse>(OrderErrors.NotFound(command.OrderId));

        order.MarkAsCancelled();                                // raises OrderCancelledDomainEvent (IDs only)
        await unitOfWork.SaveChangesAsync(cancellationToken);
        return new CancelOrderResponse(order.Id);
    }
}
```

**A command handler never publishes integration events.** Cross-module side effects go through
domain event → outbox → `IDomainEventHandler<T>` → `IEventBus` (section 15).

**Checklist:**
- [ ] `ICommandHandler`, not `IRequestHandler`
- [ ] `sealed class`
- [ ] Injects only the module's own `I<Module>UnitOfWork`
- [ ] Loads existing aggregates **with the user's access scope**
- [ ] `Result.Failure<T>(error)` for failure; implicit `return value` for success
- [ ] No `IPublishEndpoint` / `IBus` / `IEventBus` in command handlers

---

## 4. Query: Definition

File: `Application/<Feature>/Get<Entity>/<Get...>Query.cs`

```csharp
public sealed record GetProductsQuery(int Page = 1, int PageSize = 50) : IQuery<PagedResult<ProductDto>>;
public sealed record GetOrderQuery(Guid OrderId) : IQuery<OrderResponse>;

// Response DTOs — co-located in the same file
public sealed record ProductDto(Guid Id, string Name, string Sku, int StockQuantity, decimal Price);

public sealed record OrderResponse(
    Guid Id,
    Guid CustomerId,
    string Status,
    decimal TotalAmount,
    List<OrderItemResponse> Items,
    DateTime CreatedAt,
    string? InternalNotes);      // permission-gated: null when the user lacks the permission

public sealed record OrderItemResponse(Guid ProductId, int Quantity, decimal UnitPrice);
```

- Always `sealed record`
- Response DTOs live in the same file as the query
- DTOs are flat; no domain objects leak out
- **Permission-gated fields are nullable** (they become optional in OpenAPI and the orval client)

---

## 5. Query Handler: Definition

File: `Application/<Feature>/Get<Entity>/<Get...>QueryHandler.cs`

### List: filtered inside the query, then paged

```csharp
public sealed class GetProductsQueryHandler(IProductRepository productRepository, ICurrentUser currentUser)
    : IQueryHandler<GetProductsQuery, PagedResult<ProductDto>>
{
    public async Task<Result<PagedResult<ProductDto>>> Handle(GetProductsQuery query, CancellationToken cancellationToken)
    {
        // Scope filter, count and paging all run in SQL — never filter after loading
        var page = await productRepository.ListAsync(currentUser.Scope, query.Page, query.PageSize, cancellationToken);
        return page.Map(p => new ProductDto(p.Id, p.Name, p.Sku, p.StockQuantity, p.Price));
    }
}
```

### Single record with a permission-gated field (Mapster)

```csharp
public sealed class GetOrderQueryHandler(IOrderRepository orderRepository, ICurrentUser currentUser)
    : IQueryHandler<GetOrderQuery, OrderResponse>
{
    public async Task<Result<OrderResponse>> Handle(GetOrderQuery query, CancellationToken cancellationToken)
    {
        var order = await orderRepository.GetByIdAsync(query.OrderId, currentUser.Scope, cancellationToken);
        if (order is null)
            return Result.Failure<OrderResponse>(OrderErrors.NotFound(query.OrderId));   // also when out of scope

        var response = order.Adapt<OrderResponse>();
        return currentUser.HasPermission(OrdersPermissions.InternalNotesRead)
            ? response
            : response with { InternalNotes = null };
    }
}
```

When a gated field is expensive or sensitive (e.g. encrypted), project it conditionally in the repository
query instead, so it is never loaded or decrypted for users who can't see it.

---

## 6. Result / Error Pattern

```csharp
Result.Success()                     // void command success
Result.Failure(error)                // void command failure
Result.Success<T>(value)             // explicit success with value
Result.Failure<T>(error)             // typed failure
return value;                        // implicit conversion TValue → Result<TValue>
```

```csharp
Error.NotFound("Module.EntityNotFound", $"Entity '{id}' not found.")
Error.Validation("Module.InvalidInput", "...")
Error.Conflict("Module.AlreadyExists", "...")
Error.Failure("Module.OperationFailed", "...")
```

Error class per entity (`Domain/Errors/<Entity>Errors.cs`):

```csharp
public static class ProductErrors
{
    public static readonly Error NameRequired = Error.Validation("Inventory.ProductNameRequired", "Name is required.");
    public static Error NotFound(Guid id) => Error.NotFound("Inventory.ProductNotFound", $"Product '{id}' not found.");
    public static Error InsufficientStock(Guid id) => Error.Failure("Inventory.InsufficientStock", $"Insufficient stock for product '{id}'.");
}
```

**Conventions:** codes are `<Module>.<PascalCaseDescription>`. Descriptions are returned to clients and
logged, so they contain **IDs only, never personal data** (no names, e-mails or clinical details).

---

## 7. DDD Entity Types: Decision Guide

```
Entity<TKey>                 → identity + domain events (no timestamps)
  └── AuditableEntity<TKey>  → + CreatedAt, UpdatedAt (UTC, set by BaseDbContext)
        └── AuditableGuidEntity  → AuditableEntity<Guid>
```

| Use | Base class |
|---|---|
| Aggregate root with a `Guid` Id + timestamps | `AuditableGuidEntity` (**default**) |
| Entity with a non-Guid key | `AuditableEntity<TKey>` |
| Child entity | `Entity<Guid>` |

Entity rules (full detail in the domain-ef skill): `sealed class`, private parameterless constructor for
EF, private setters, a `static Create(...)` that returns `Result<T>` and **never throws**, behaviour
methods in ubiquitous language, new IDs from `Guid.CreateVersion7()`.

---

## 8. Domain Events

Raised inside the entity on a meaningful state change. They are persisted in outbox rows, so they carry
**IDs, codes and timestamps only**.

```csharp
// Domain/Events/OrderCancelledDomainEvent.cs
public sealed record OrderCancelledDomainEvent(Guid OrderId, string ReasonCode) : DomainEvent;

// inside Order.MarkAsCancelled(...)
RaiseDomainEvent(new OrderCancelledDomainEvent(Id, reasonCode));
```

Dispatch is automatic: interceptor → outbox → Quartz → `IDomainEventHandler<T>` (section 15).

---

## 9. Repository Pattern

### Interface (`Domain/I<Entity>Repository.cs`)

```csharp
public interface IProductRepository : IRepository<Product, Guid>
{
    Task<Product?> GetByIdAsync(Guid id, AccessScope scope, CancellationToken cancellationToken = default);
    Task<PagedResult<Product>> ListAsync(AccessScope scope, int page, int pageSize, CancellationToken cancellationToken = default);
    Task<List<Product>> GetByIdsAsync(List<Guid> ids, CancellationToken cancellationToken = default);   // internal use (consumers)
}
```

### Implementation (`Infrastructure/Persistence/<Entity>Repository.cs`)

```csharp
public sealed class ProductRepository(InventoryDbContext context)
    : BaseRepository<Product, Guid, InventoryDbContext>(context), IProductRepository
{
    private IQueryable<Product> Scoped(AccessScope scope) =>
        DbSet.Where(p => scope.IsUnrestricted || scope.DepartmentIds.Contains(p.DepartmentId));

    public Task<Product?> GetByIdAsync(Guid id, AccessScope scope, CancellationToken ct = default) =>
        Scoped(scope).FirstOrDefaultAsync(p => p.Id == id, ct);

    public async Task<PagedResult<Product>> ListAsync(AccessScope scope, int page, int pageSize, CancellationToken ct = default)
    {
        var query = Scoped(scope).AsNoTracking();
        var total = await query.CountAsync(ct);                                   // count after the scope filter
        var items = await query.OrderBy(p => p.Id)
                               .Skip((page - 1) * pageSize).Take(pageSize)
                               .ToListAsync(ct);
        return new PagedResult<Product>(items, total, page, pageSize);
    }

    public Task<List<Product>> GetByIdsAsync(List<Guid> ids, CancellationToken ct = default) =>
        DbSet.Where(p => ids.Contains(p.Id)).ToListAsync(ct);
}
```

**Rules:**
- Only the module's own `DbSet`; never another module's DbContext
- Methods serving **users** take an `AccessScope` and apply it to the `IQueryable` **before** `Count`, `Skip`/`Take` and materialisation
- Unscoped methods (including the base `IRepository.GetByIdAsync(id)`) exist only for system work (consumers, sagas, jobs, domain event handlers). Never use them to serve a user request.
- No `SaveChanges` inside repositories; that's the unit of work's job
- `AsNoTracking()` on read-only paths
- No `Where`/`OrderBy` on encrypted columns; use blind indexes (domain-ef skill §3)

The tenant is implicit: the DbContext is already connected to the current tenant's database.

---

## 10. Unit of Work

```csharp
// Application/Abstractions/IInventoryUnitOfWork.cs
public interface IInventoryUnitOfWork : IUnitOfWork { }   // IUnitOfWork: Task<int> SaveChangesAsync(CancellationToken)

// InventoryDbContext : BaseDbContext, IInventoryUnitOfWork
services.AddScoped<IInventoryUnitOfWork>(sp => sp.GetRequiredService<InventoryDbContext>());
```

- Commands that persist state inject `I<Module>UnitOfWork`
- Queries never inject the unit of work
- Each module injects only its own

---

## 11. Permissions

Each module declares its permissions in `Application/Permissions/<Module>Permissions.cs`:

```csharp
public static class InventoryPermissions
{
    public const string ProductsRead   = "inventory.products.read";
    public const string ProductsManage = "inventory.products.manage";

    public static readonly string[] All = [ProductsRead, ProductsManage];
}
```

- Format `<module>.<resource>.<action>`, lowercase; register with `services.AddPermissions(InventoryPermissions.All)` in `<Module>Module`
- Endpoints require them (`.RequireAuthorization(InventoryPermissions.ProductsRead)`); see the endpoints skill
- Handlers use `ICurrentUser.HasPermission(...)` only for **field-level** decisions; endpoint access is enforced at the endpoint
- Hospital administrators bundle permissions into roles at runtime. Never hard-code role names in code.

---

## 12. FluentValidation

Validators are discovered automatically and run by `ValidationBehavior`:

```csharp
public sealed class CreateProductCommandValidator : AbstractValidator<CreateProductCommand>
{
    public CreateProductCommandValidator()
    {
        RuleFor(x => x.Name).NotEmpty().MaximumLength(200);
        RuleFor(x => x.Sku).NotEmpty().MaximumLength(50);
        RuleFor(x => x.DepartmentId).NotEmpty();
        RuleFor(x => x.StockQuantity).GreaterThanOrEqualTo(0);
        RuleFor(x => x.Price).GreaterThan(0);
    }
}
```

No registration needed: `AddApplication` calls `AddValidatorsFromAssemblies`. Validation messages must not
echo personal input values back.

---

## 13. Mapster Mapping Config

```csharp
// Application/<Feature>/<Module>MappingConfig.cs
public static class OrderMappingConfig
{
    public static void Configure()
    {
        TypeAdapterConfig<Order, OrderResponse>
            .NewConfig()
            .Map(dest => dest.Status, src => src.Status.ToString())
            .Map(dest => dest.Items, src => src.Items.Adapt<List<OrderItemResponse>>());

        TypeAdapterConfig<OrderItem, OrderItemResponse>.NewConfig();
    }
}

// <Module>Module.cs — after AddApplication(...)
OrderMappingConfig.Configure();
```

- Manual `new Dto(...)` for flat DTOs with 1–4 fields
- Mapster for nested objects, enum conversions, collections, 5+ fields

---

## 14. Folder Conventions

```
Application/
  Products/
    CreateProduct/
      CreateProductCommand.cs
      CreateProductCommandHandler.cs
      CreateProductCommandValidator.cs
    GetProducts/
      GetProductsQuery.cs
      GetProductsQueryHandler.cs
    ProductCreated/
      ProductCreatedDomainEventHandler.cs
    ProductMappingConfig.cs
  Permissions/
    InventoryPermissions.cs
  Abstractions/
    IInventoryUnitOfWork.cs
```

---

## 15. Domain Events → Outbox → Integration Events

```
entity.RaiseDomainEvent(new XyzDomainEvent(ids…))
      ↓
unitOfWork.SaveChangesAsync()
      └─ OutboxMessagesInterceptor writes OutboxMessage rows (same transaction, module schema, tenant DB)
      ↓
Quartz job → OutboxMessageProcessor<TDbContext> → IDomainEventHandler<T>
      ↓
IEventBus.PublishAsync(integration event — IDs only)   [MassTransit → RabbitMQ, tenant header added by filter]
```

> **Open decision:** delivering outbox rows across **all tenant databases** (and safely with several API
> replicas) is deferred until it is revisited with the project owner. Use the pattern as described; don't
> build a multi-tenant processor on your own.

### Per-module wiring

`services.AddTenantDbContext<InventoryDbContext>("inventory")` already adds the outbox interceptor. Also register:

```csharp
services.AddScoped<IOutboxMessageProcessor, OutboxMessageProcessor<InventoryDbContext>>();
```

The `OutboxMessages` table comes from `BaseDbContext.OnModelCreating`. Add it with the module's first
migration.

### Domain event handler

```csharp
// Application/Orders/OrderCreated/OrderCreatedDomainEventHandler.cs
public sealed class OrderCreatedDomainEventHandler(IOrderRepository orderRepository, IEventBus eventBus)
    : IDomainEventHandler<OrderCreatedDomainEvent>
{
    public async Task Handle(DomainEventNotification<OrderCreatedDomainEvent> notification, CancellationToken cancellationToken)
    {
        var domainEvent = notification.DomainEvent;

        // Unscoped base-repository lookup: system work, not a user request
        var order = await orderRepository.GetByIdAsync(domainEvent.OrderId, cancellationToken);
        if (order is null) return;

        await eventBus.PublishAsync(new OrderCreatedIntegrationEvent(
            order.Id,
            order.CustomerId,             // an ID, not contact details
            order.TotalAmount,
            domainEvent.OccurredOn), cancellationToken);
    }
}
```

**Rules:**
- Publish through `IEventBus` only (never `IPublishEndpoint` or `IBus` in the Application layer)
- Don't inject `I<Module>UnitOfWork`; the transaction has already committed
- Integration events carry **IDs only**; consumers needing details use request/response (consumers skill)
- Handlers are discovered by `AddApplication(assembly)`

### Outbox processor error handling

The catch block sets `Error` only, **never** `ProcessedOnUtc`. Otherwise a transient failure (e.g.
RabbitMQ down) drops the event permanently. Log the message ID only.

---

## 16. Defining DDD Types from Requirements

| Question | Decision |
|---|---|
| Does it have identity and lifecycle? | Aggregate root (`AuditableGuidEntity`) |
| Is it owned by an aggregate, with no independent lifecycle? | Child entity (`Entity<Guid>`) |
| Is it just a grouping of data with no identity? | Value object (`record`) |
| Does something meaningful happen that others should know about? | Domain event (IDs only) |
| Does another module need to react? | Integration event in the `IntegrationEvents` project |
| Does another module need **details**? | Request/response contract owned by this module |
| Is it a state-changing business operation? | Command |
| Is it a read-only business operation? | Query, scoped to what the user may see |
| Who may do it? | A permission in `<Module>Permissions` |
| Does it hold personal data? | Ask whether each field is encrypted and which fields are permission-gated |
| Should it fail gracefully? | `Result.Failure<T>(Error...)` |
| Is the input from outside the system? | FluentValidation |
