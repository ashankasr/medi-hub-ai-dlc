# Full-Pipeline Feature Implementation: Complete Reference

Work through the phases in order; each phase produces what the next one needs. Code examples use
**illustrative** modules (Inventory, Notifications), not MediHub modules.
Cross-cutting rules: `../../dotnet-backend-modular-monolith-eventdriven-architecture/references/medihub-platform-conventions.md`.

---

## Phase 1: Brainstorm the Requirement

Answer every question before writing code, and confirm the answers with the user. Anything the requirement
doesn't settle is a **question for the user**, never a silent assumption.

### 1.1 The Operation

| Question | Why it matters |
|---|---|
| Which groomed requirement (Story/Feature) does this implement? | Traceability; no invented features |
| What action does the user or system want to take? | Command name, domain method name, HTTP verb |
| Which module owns the affected entity? | Where the feature lives |
| Write (state change) or read? | Command vs query; unit of work or not |
| What data does the caller supply, and what do they get back? | Request record, command/query, response DTO, status code |

### 1.2 Access

| Question | Why it matters |
|---|---|
| Which **permission** allows this? Does it exist in `<Module>Permissions`? | `.RequireAuthorization(permission)`; a new permission for administrators to assign |
| Whose records may the user see or act on? Is there a scoping key (department/ward)? | Access-scope filter inside the repository query |
| Do some users see **more fields** than others on this endpoint? Which fields, gated by which permission? | Nullable gated fields, populated conditionally |
| Rules beyond scope (care relationship, consent, break-the-glass)? | Belongs to the Access module and isn't designed yet. Stop and raise it. |

### 1.3 Personal Data

| Question | Why it matters |
|---|---|
| Does the feature add or expose personal data? Which fields? | Encryption, logging, messaging rules |
| Is each personal-data field **encrypted**? | `IsEncrypted()`, sizing, no filtering or sorting on it |
| Does anything need an exact-match lookup on an encrypted field? | Blind index |
| Does it appear in a notification? | Notifications exclude personal data by default; exceptions are decided per notification type |

### 1.4 The Domain Impact

| Question | Why it matters |
|---|---|
| Does it change state? Create, update or delete an aggregate? | Unit of work, repository calls |
| Which invariants and business rules apply? | Entity methods returning `Result<T>` |
| What are the failure scenarios and error codes? | `<Entity>Errors` |
| Does it need a new entity? | Start with the domain-ef skill |

### 1.5 The Event Story

| Question | Answer |
|---|---|
| Does another module need to **know** this happened? | Domain event → outbox → integration event (IDs only) |
| Does another module need **details** owned by this module (or vice versa)? | Request/response contract |
| Fire-and-forget? | Choreography consumer in the target module |
| Several modules must succeed together, with compensation? | Saga |
| Does it depend on **outbox delivery across tenants**? | That decision is deferred; flag it |

### 1.6 The HTTP Contract

```
Verb:        POST / GET / PUT / DELETE / PATCH
Route:       /api/<module>/<resource>[/{id}]
Permission:  <module>.<resource>.<action>
Request:     { field: type, ... } | path param | query string   (never a tenant ID)
Response:    200 { ... } | 201 { id } | 204   (gated fields nullable)
Errors:      400 { code, description } | 403 (permission) | 404 (missing or out of scope) | 409
```

### 1.7 Validation Rules

Required fields, lengths, ranges, business rules. These map 1:1 to FluentValidation rules.

---

## Phase 2: Pipeline Design: Decision Matrix

| Layer needed? | Condition | Artefacts |
|---|---|---|
| **New entity / value object** | Entity doesn't exist yet | Entity, EF configuration, migration |
| **Encrypted field / blind index** | Personal data confirmed as encrypted | `IsEncrypted()` in the configuration, sized column |
| **Repository method** | A new query is needed | Interface + implementation, **scoped** if it serves users |
| **Command + handler** | Write | `XxxCommand`, `XxxCommandHandler` |
| **Query + handler** | Read | `XxxQuery`, `XxxResponse`, `XxxQueryHandler` |
| **Validator** | Command with user input | `XxxCommandValidator` |
| **Permission** | Not covered by an existing permission | Constant in `<Module>Permissions` + included in `All` |
| **Domain event** | Other handlers or modules react | `XxxDomainEvent` (IDs only), raised in the entity |
| **IDomainEventHandler** | Domain event → integration message | `XxxDomainEventHandler` in **Application** |
| **Integration event contract** | Another module (or a saga) must be told | Record in the owning `IntegrationEvents` project |
| **Request/response contract + responder** | Another module needs this module's details | Request/response records + responder consumer |
| **Consumer in target module** | Another module reacts | `XxxConsumer` in the target's `Infrastructure/Consumers/` |
| **Saga step** | Multi-module coordination with compensation | State, events, transitions, contracts |
| **Migration** | Schema changed | `dotnet ef migrations add …` (applied by the migration service) |
| **Endpoint** | Callable over HTTP | `MapXxx` + `.RequireAuthorization(permission)` |
| **API client regeneration** | Web or mobile uses it | orval regeneration in `packages/api-client` |

### Where integration events are published

```
Command handler (save state)
  └─ Entity raises DomainEvent (IDs only)
       └─ EF interceptor writes OutboxMessage row (same transaction, tenant DB)
            └─ OutboxMessageProcessor (Quartz)
                 └─ IDomainEventHandler<T> → IEventBus.PublishAsync(...) → RabbitMQ (tenant header added)
                      └─ Consumer in target module reacts
```

**Rule:** never publish from a command handler.

---

## Phase 3: Implementation Order

```
1. Domain
   a. Entity behaviour method (invariants, raises domain event)
   b. Domain event record (IDs only)
   c. Errors in Domain/Errors/<Entity>Errors.cs
   d. Repository interface method (with AccessScope if user-facing)

2. Application
   a. Permission constant (if new)
   b. Command/query record + response DTO (gated fields nullable)
   c. Handler (scope applied via repository; gated fields via ICurrentUser)
   d. Validator
   e. Domain event handler (if publishing)

3. Infrastructure: Persistence
   a. EF configuration (encryption, indexes on scope keys)
   b. Repository implementation (scope filter before paging)
   c. Migration

4. IntegrationEvents (if applicable)
   a. Event / saga command / request-response contracts in the owning module

5. Infrastructure: Messaging (if applicable)
   a. Consumer(s) in the target module (idempotent, IDs-only logging)
   b. Responder consumer / request client registration
   c. ConfigureConsumers registration

6. Presentation
   a. Request record
   b. MapPost/MapGet/... with RequireAuthorization(permission)
   c. WebApplicationExtensions wiring (new module only)
```

Domain is pure C#. Application depends on Domain interfaces. Infrastructure implements them. Contracts are
defined once the handler shape is known. Presentation comes last because it maps HTTP onto commands and
queries that must already exist.

---

## Phase 4: Layer-by-Layer Implementation

### 4.1 Domain

```csharp
// Domain/Product.cs
public static Result<Product> Create(Guid id, string name, string sku, Guid departmentId, int stockQty, decimal price)
{
    if (string.IsNullOrWhiteSpace(name))
        return Result.Failure<Product>(ProductErrors.NameRequired);
    if (price <= 0)
        return Result.Failure<Product>(ProductErrors.InvalidPrice);

    var product = new Product(id, name, sku, departmentId, stockQty, price);
    product.RaiseDomainEvent(new ProductCreatedDomainEvent(id));   // IDs only
    return product;
}
```

```csharp
// Domain/Events/ProductCreatedDomainEvent.cs
public sealed record ProductCreatedDomainEvent(Guid ProductId) : DomainEvent;
```

```csharp
// Domain/Errors/ProductErrors.cs
public static class ProductErrors
{
    public static readonly Error NameRequired = Error.Validation("Inventory.ProductNameRequired", "Name is required.");
    public static readonly Error InvalidPrice = Error.Validation("Inventory.InvalidPrice", "Price must be greater than zero.");
    public static Error NotFound(Guid id) => Error.NotFound("Inventory.ProductNotFound", $"Product '{id}' was not found.");
}
```

```csharp
// Domain/IProductRepository.cs
Task<Product?> GetBySkuAsync(string sku, AccessScope scope, CancellationToken cancellationToken = default);
```

> Details: `dotnet-backend-modular-monolith-domain-ef` skill.

---

### 4.2 Application

```csharp
// Application/Permissions/InventoryPermissions.cs  (add if new)
public const string ProductsManage = "inventory.products.manage";
```

```csharp
public sealed record CreateProductCommand(string Name, string Sku, Guid DepartmentId, int StockQuantity, decimal Price)
    : ICommand<Guid>;

public sealed record GetProductByIdQuery(Guid ProductId) : IQuery<ProductResponse>;
public sealed record ProductResponse(Guid Id, string Name, string Sku, int StockQuantity, decimal Price, decimal? CostPrice);
//                                                                                       gated field ↑ (nullable)
```

```csharp
public sealed class CreateProductCommandHandler(IProductRepository productRepository, IInventoryUnitOfWork unitOfWork)
    : ICommandHandler<CreateProductCommand, Guid>
{
    public async Task<Result<Guid>> Handle(CreateProductCommand command, CancellationToken cancellationToken)
    {
        var result = Product.Create(Guid.CreateVersion7(), command.Name, command.Sku, command.DepartmentId,
            command.StockQuantity, command.Price);
        if (result.IsFailure)
            return Result.Failure<Guid>(result.Error);

        productRepository.Add(result.Value);
        await unitOfWork.SaveChangesAsync(cancellationToken);
        return result.Value.Id;
    }
}
```

```csharp
public sealed class GetProductByIdQueryHandler(IProductRepository productRepository, ICurrentUser currentUser)
    : IQueryHandler<GetProductByIdQuery, ProductResponse>
{
    public async Task<Result<ProductResponse>> Handle(GetProductByIdQuery query, CancellationToken cancellationToken)
    {
        var product = await productRepository.GetByIdAsync(query.ProductId, currentUser.Scope, cancellationToken);
        if (product is null)
            return Result.Failure<ProductResponse>(ProductErrors.NotFound(query.ProductId));   // also when out of scope

        var response = product.Adapt<ProductResponse>();
        return currentUser.HasPermission(InventoryPermissions.CostPriceRead) ? response : response with { CostPrice = null };
    }
}
```

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

```csharp
// Application/Products/ProductCreated/ProductCreatedDomainEventHandler.cs
public sealed class ProductCreatedDomainEventHandler(IEventBus eventBus) : IDomainEventHandler<ProductCreatedDomainEvent>
{
    public Task Handle(DomainEventNotification<ProductCreatedDomainEvent> notification, CancellationToken cancellationToken) =>
        eventBus.PublishAsync(
            new ProductCreatedIntegrationEvent(notification.DomainEvent.ProductId, notification.DomainEvent.OccurredOn),
            cancellationToken);
}
```

Always publish through `IEventBus`, never `IBus` or `IPublishEndpoint`, in the Application layer.

> Details: `dotnet-backend-modular-monolith-eventdriven-cqrs-patterns` skill.

---

### 4.3 Infrastructure: Persistence

```csharp
// Infrastructure/Persistence/Configurations/ProductConfiguration.cs
public sealed class ProductConfiguration : IEntityTypeConfiguration<Product>
{
    public void Configure(EntityTypeBuilder<Product> builder)
    {
        builder.ToTable("Products");
        builder.HasKey(p => p.Id);
        builder.Property(p => p.Name).HasMaxLength(200).IsRequired();
        builder.Property(p => p.Sku).HasMaxLength(50).IsRequired();
        builder.HasIndex(p => p.Sku).IsUnique();
        builder.HasIndex(p => p.DepartmentId);
        builder.Property(p => p.Price).HasPrecision(18, 2);
    }
}
```

```csharp
// Repository — scope applied before materialising
public Task<Product?> GetBySkuAsync(string sku, AccessScope scope, CancellationToken cancellationToken = default) =>
    Scoped(scope).FirstOrDefaultAsync(p => p.Sku == sku, cancellationToken);
```

```bash
dotnet ef migrations add <MigrationName> \
  --project src/Modules/<Name>/MediHub.Modules.<Name>.Infrastructure \
  --startup-project src/Modules/<Name>/MediHub.Modules.<Name>.Infrastructure \
  --context <Name>DbContext
```

The migration service applies it to every tenant database. The API never migrates.

> Details: `dotnet-backend-modular-monolith-domain-ef` skill.

---

### 4.4 Integration Events (if applicable)

```csharp
// src/Modules/Inventory/MediHub.Modules.Inventory.IntegrationEvents/
public sealed record ProductCreatedIntegrationEvent(Guid ProductId, DateTime OccurredAt);   // IDs only

// Request/response owned by Inventory
public sealed record GetProductDetails(Guid ProductId);
public sealed record ProductDetails(Guid ProductId, string Name, string Sku);
public sealed record ProductNotFound(Guid ProductId);
```

> Details: `dotnet-backend-modular-monolith-eventdriven-integration-events-consumers` skill.

---

### 4.5 Infrastructure: Messaging (if applicable)

Consumers are the handlers: they use the module's own repositories and DbContext directly and do **not**
delegate to MediatR (`ISender`).

```csharp
// Notifications module (illustrative): Infrastructure/Consumers/ProductCreatedConsumer.cs
public sealed class ProductCreatedConsumer(
    IRequestClient<GetProductDetails> productDetails,
    NotificationsDbContext dbContext,
    ILogger<ProductCreatedConsumer> logger) : IConsumer<ProductCreatedIntegrationEvent>
{
    public async Task Consume(ConsumeContext<ProductCreatedIntegrationEvent> context)
    {
        logger.LogInformation("[CHOREOGRAPHY] ProductCreated {ProductId}", context.Message.ProductId);   // IDs only

        if (await dbContext.NotificationLogs.AnyAsync(n => n.SourceId == context.Message.ProductId, context.CancellationToken))
            return;   // idempotent

        var response = await productDetails.GetResponse<ProductDetails, ProductNotFound>(
            new GetProductDetails(context.Message.ProductId), context.CancellationToken);
        // ... build and send the notification; never log or store response.Message
    }
}
```

```csharp
public static void ConfigureConsumers(IRegistrationConfigurator configurator)
{
    configurator.AddConsumer<ProductCreatedConsumer>();
    configurator.AddRequestClient<GetProductDetails>();
}
```

> Details: `dotnet-backend-modular-monolith-eventdriven-integration-events-consumers` and
> `dotnet-backend-modular-monolith-eventdriven-saga` skills.

---

### 4.6 Presentation

```csharp
group.MapPost("/products", async (CreateProductRequest request, ISender sender) =>
{
    var result = await sender.Send(new CreateProductCommand(
        request.Name, request.Sku, request.DepartmentId, request.StockQuantity, request.Price));

    return result.IsSuccess
        ? Results.Created($"/api/inventory/products/{result.Value}", new { Id = result.Value })
        : Results.BadRequest(result.Error);
})
.RequireAuthorization(InventoryPermissions.ProductsManage)
.WithSummary("Create a product");

public sealed record CreateProductRequest(string Name, string Sku, Guid DepartmentId, int StockQuantity, decimal Price);
```

| Scenario | HTTP result |
|---|---|
| Created | `201 Created` with `Location` and `{ id }` |
| Updated/deleted | `200 Ok` or `204 NoContent` |
| Query succeeded | `200 Ok` |
| `Error.NotFound` (incl. out of scope) | `404 NotFound` |
| `Error.Conflict` | `409 Conflict` |
| `Error.Validation` / FluentValidation | `400 BadRequest` |
| Missing permission | `403` (middleware) |

> Details: `dotnet-backend-modular-monolith-presentation-endpoints` skill.

---

## Phase 5: Verification Checklist

### Build and structure
- [ ] `dotnet build MediHub.slnx` (or `npx nx affected -t build`): 0 errors, 0 warnings
- [ ] Files in the correct layer; no cross-module references except `IntegrationEvents`

### Access
- [ ] Endpoint has `.RequireAuthorization(<permission>)`; any new permission is in `<Module>Permissions.All`
- [ ] User-facing queries apply `ICurrentUser.Scope` **inside** the SQL query, before count and paging
- [ ] Out-of-scope records return 404
- [ ] Gated fields are nullable and only populated with the permission

### Personal data
- [ ] Every personal-data field's encryption decision came from the requirement or the user, not a guess
- [ ] No filtering or sorting on encrypted columns (blind index for exact matches)
- [ ] No personal data in domain events, integration events, saga state, logs or error descriptions

### Domain
- [ ] Factories and behaviour methods return `Result<T>`, never throw
- [ ] Error codes are in `Domain/Errors/<Entity>Errors.cs`
- [ ] New IDs from `Guid.CreateVersion7()`; timestamps in UTC

### Application
- [ ] Records are `sealed record`; correct `ICommand`/`IQuery` interfaces
- [ ] Validator for every command with user input
- [ ] Integration messages are published only from `IDomainEventHandler` via `IEventBus`

### Infrastructure: Persistence
- [ ] Dedicated `IEntityTypeConfiguration<T>` class; `DbSet<T>` for aggregate roots
- [ ] Migration created and reviewed (no unintended drops)
- [ ] Module registered with the migration service (`ConfigureMigrations`)

### Infrastructure: Messaging
- [ ] Consumers are idempotent and registered in `ConfigureConsumers`
- [ ] Contracts are in the owning module's `IntegrationEvents` project, IDs only
- [ ] Request clients are registered; responses are never logged or stored

### Presentation
- [ ] `.WithSummary()` added; `MapXxxEndpoints()` wired for new modules
- [ ] orval client regenerated if the frontends use the endpoint

### Runtime smoke test (Aspire)
- [ ] `aspire run` (or `npx nx run apphost:serve`): all resources healthy in the Aspire dashboard
- [ ] The `migrations` resource completed; the new schema or columns exist in the demo tenant databases
- [ ] Happy path, as a demo user **with** the permission: expected status and body
- [ ] As a demo user **without** the permission: 403
- [ ] As a demo user scoped to another department/ward: list excludes the record; GET returns 404
- [ ] Switching the active hospital shows only that hospital's data
- [ ] Bad input: 400 with `{ code, description }`
- [ ] Integration event: the consuming module received it (Aspire traces/logs; RabbitMQ UI via dashboard link)

---

## Quick Reference: Which Specialist Skill to Load Next

| Task | Skill |
|---|---|
| Entity, EF config, encryption, migration | `dotnet-backend-modular-monolith-domain-ef` |
| Command/query/handler/validator/permission | `dotnet-backend-modular-monolith-eventdriven-cqrs-patterns` |
| Integration event, request/response or consumer | `dotnet-backend-modular-monolith-eventdriven-integration-events-consumers` |
| Saga | `dotnet-backend-modular-monolith-eventdriven-saga` |
| HTTP endpoint | `dotnet-backend-modular-monolith-presentation-endpoints` |
| New module | `dotnet-backend-modular-monolith-eventdriven-create-module` |
| Architecture, tenancy and platform rules | `dotnet-backend-modular-monolith-eventdriven-architecture` |
