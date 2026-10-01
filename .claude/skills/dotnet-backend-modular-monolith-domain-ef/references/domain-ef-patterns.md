# Domain Implementation, EF Configuration & Migrations: Complete Reference

Stack: .NET 10, EF Core 10, **Npgsql (Postgres)**, database per tenant, schema per module.
Entities below (Order, Product, StockReservation) are **illustrative**, not MediHub modules.
Cross-cutting rules: `../../dotnet-backend-modular-monolith-eventdriven-architecture/references/medihub-platform-conventions.md`.

---

## 1. Domain Entity Patterns

### Base class hierarchy (from `MediHub.Common.Domain.Primitives`)

```
Entity<TKey>                 → Id, DomainEvents, equality by Id
  └── AuditableEntity<TKey>  → + CreatedAt, UpdatedAt (UTC, auto-set by BaseDbContext)
        └── AuditableGuidEntity  → shorthand: AuditableEntity<Guid>
```

`CreatedAt`/`UpdatedAt` are technical timestamps only. Clinical-grade audit (who, including reads) is a
separate platform capability whose design is pending. Don't add per-entity audit columns or tables for it.

### Decision guide

| Scenario | Base class |
|---|---|
| Aggregate root (own lifecycle, owns child entities) | `AuditableGuidEntity` |
| Child entity (owned by an aggregate, no independent lifecycle) | `Entity<Guid>` |
| Lookup / reference data (non-Guid key) | `AuditableEntity<TKey>` |
| Immutable grouping with no identity | C# `record` (value object) |

---

### Aggregate root: full pattern

```csharp
// Domain/Order.cs
public sealed class Order : AuditableGuidEntity
{
    private readonly List<OrderItem> _items = [];

    private Order() { }  // required: EF needs a parameterless constructor

    private Order(Guid id, Guid customerId, Guid departmentId, List<OrderItem> items) : base(id)
    {
        CustomerId = customerId;
        DepartmentId = departmentId;
        _items = items;
        Status = OrderStatus.Pending;
        TotalAmount = items.Sum(i => i.UnitPrice * i.Quantity);

        RaiseDomainEvent(new OrderCreatedDomainEvent(id));   // IDs only — stored in the outbox row
    }

    public Guid CustomerId { get; private set; }             // reference by ID, not by personal details
    public Guid DepartmentId { get; private set; }           // used for access-scope filtering
    public OrderStatus Status { get; private set; }
    public decimal TotalAmount { get; private set; }
    public string? FailureReasonCode { get; private set; }   // a code, not free text
    public uint Version { get; private set; }                // optimistic concurrency (Postgres xmin)
    public IReadOnlyList<OrderItem> Items => _items.AsReadOnly();

    // Factory — returns Result<T>, never throws
    public static Result<Order> Create(Guid id, Guid customerId, Guid departmentId, List<OrderItem> items)
    {
        if (customerId == Guid.Empty)
            return Result.Failure<Order>(OrderErrors.InvalidCustomer);
        if (items.Count == 0)
            return Result.Failure<Order>(OrderErrors.NoItems);

        return new Order(id, customerId, departmentId, items);
    }

    // Behaviour methods — ubiquitous language, not setters
    public void MarkAsStockReserved() => Status = OrderStatus.StockReserved;
    public void MarkAsCompleted() => Status = OrderStatus.Completed;
    public void MarkAsFailed(string reasonCode) { Status = OrderStatus.Failed; FailureReasonCode = reasonCode; }
    public void MarkAsCancelled() => Status = OrderStatus.Cancelled;
}
```

Callers create IDs with `Guid.CreateVersion7()` (time-ordered, index-friendly).

**Rules:**
- Always `sealed class`
- Private `_field` for collections, exposed as `IReadOnlyList<T>`
- `private Entity() { }` for EF Core
- `static Create(...)` returns `Result<TEntity>` with `Error.Validation(...)` failures and **never throws**
- Behaviour methods use ubiquitous language (`MarkAsCancelled`, `ReserveStock`), never `SetStatus`
- Domain events carry **IDs, codes and timestamps only**. They are persisted in outbox rows, so personal data must never be in them.
- Any entity whose records must be filtered by the user's access scope carries the scoping key (e.g. `DepartmentId`)

---

### Child entity: owned by an aggregate

```csharp
// Domain/OrderItem.cs
public sealed class OrderItem : Entity<Guid>
{
    private OrderItem() { }

    public OrderItem(Guid id, Guid orderId, Guid productId, int quantity, decimal unitPrice) : base(id)
    {
        OrderId = orderId;
        ProductId = productId;
        Quantity = quantity;
        UnitPrice = unitPrice;
    }

    public Guid OrderId { get; private set; }
    public Guid ProductId { get; private set; }
    public int Quantity { get; private set; }
    public decimal UnitPrice { get; private set; }
}
```

- Use `Entity<Guid>` (no audit timestamps; the child's lifecycle is tied to the root)
- No factory needed; only the aggregate root creates it

---

### Value object (owned / embedded)

```csharp
// Domain/ReservationItem.cs  (owned by StockReservation)
public sealed record ReservationItem(Guid ProductId, int Quantity);
```

Map with `OwnsOne` / `OwnsMany` (section 2).

---

### Enum

```csharp
// Domain/OrderStatus.cs
public enum OrderStatus
{
    Pending = 0,
    StockReserved = 1,
    PaymentProcessed = 2,
    Completed = 3,
    Failed = 4,
    Cancelled = 5
}
```

- Always assign explicit integer values
- Persist as `string` via `.HasConversion<string>()` so values are readable and stable across migrations

---

### Domain event

```csharp
// Domain/Events/OrderCreatedDomainEvent.cs
public sealed record OrderCreatedDomainEvent(Guid OrderId) : DomainEvent;
// DomainEvent base provides: EventId (Guid), OccurredOn (DateTime, UTC)
```

Raised inside the entity with `RaiseDomainEvent(...)`. The outbox interceptor stores it in the same
transaction, and the outbox processor dispatches it to `IDomainEventHandler<T>`. See the CQRS skill.

---

## 2. EF Entity Configuration: `IEntityTypeConfiguration<T>`

Each entity gets its own configuration class in `Infrastructure/Persistence/Configurations/`. The
module's `DbContext.OnModelCreating` calls `ApplyConfigurationsFromAssembly`.

```csharp
// Infrastructure/Persistence/Configurations/ProductConfiguration.cs
public sealed class ProductConfiguration : IEntityTypeConfiguration<Product>
{
    public void Configure(EntityTypeBuilder<Product> builder)
    {
        builder.ToTable("Products");
        builder.HasKey(p => p.Id);
        builder.Property(p => p.Name).IsRequired().HasMaxLength(200);
        builder.Property(p => p.Sku).IsRequired().HasMaxLength(50);
        builder.Property(p => p.Price).HasPrecision(18, 2);
        builder.HasIndex(p => p.Sku).IsUnique();
        builder.HasIndex(p => p.DepartmentId);              // access-scope filter column
    }
}
```

**Rules:**
- One file per entity, `<EntityName>Configuration.cs`
- `sealed class`, no constructor parameters
- All mapping lives in `Configure(...)`; never use data annotations on entities

### String properties

```csharp
builder.Property(p => p.Name).IsRequired().HasMaxLength(200);   // → varchar(200)
builder.Property(p => p.FailureReasonCode).HasMaxLength(100);   // nullable — no IsRequired()
```

| Field type | Max length |
|---|---|
| Name / Title | 200 |
| Code / SKU / Slug / reason code | 50–100 |
| Email | 200 |
| Id / short reference | 100 |
| Reason / message | 500 |
| Long message / body | 1000 |

### Decimal precision

```csharp
builder.Property(p => p.Price).HasPrecision(18, 2);   // → numeric(18,2); always set explicitly
```

### Enum → string conversion

```csharp
builder.Property(o => o.Status).HasConversion<string>().HasMaxLength(50).IsRequired();
```

### Indexes

```csharp
builder.HasIndex(p => p.Sku).IsUnique();     // unique
builder.HasIndex(i => i.OrderId);            // non-unique, FK / filter columns
```

### Optimistic concurrency (Postgres `xmin`)

```csharp
// Entity: public uint Version { get; private set; }
builder.Property(o => o.Version).IsRowVersion();   // Npgsql maps this to the xmin system column
```

Don't use SQL Server-style `byte[] RowVersion` columns.

### One-to-many relationship

```csharp
builder.HasMany(o => o.Items)
       .WithOne()
       .HasForeignKey(i => i.OrderId)
       .OnDelete(DeleteBehavior.Cascade);
```

### Owned entities: `OwnsMany` / `OwnsOne`

```csharp
builder.OwnsMany(r => r.Items, ib =>
{
    ib.ToTable("StockReservationItems");
    ib.WithOwner().HasForeignKey("ReservationId");
    ib.Property(i => i.ProductId);
    ib.Property(i => i.Quantity);
});

builder.OwnsOne(o => o.DeliveryPoint, ab =>
{
    ab.Property(a => a.Building).IsRequired().HasMaxLength(100);
    ab.Property(a => a.Room).HasMaxLength(50);
});   // stored as columns on the owner's table
```

---

## 3. Personal Data: Application-Level Encryption

Personal-data fields chosen for encryption are encrypted by the application (AES-GCM, tenant data key).
**Which** fields are encrypted is decided per requirement. If the requirement is silent, ask.

```csharp
// Ciphertext column — the value is encrypted on save and decrypted on load
builder.Property(c => c.ContactEmail).IsEncrypted().HasMaxLength(500);   // ciphertext is longer than plaintext

// Ciphertext + blind index (shadow column ContactEmail_bidx, HMAC with the tenant's index key) for exact lookups
builder.Property(c => c.NationalId).IsEncrypted(blindIndex: true);
builder.HasIndex("NationalId_bidx").IsUnique();                          // uniqueness on the blind index, never the ciphertext
```

Querying an encrypted field by exact value:

```csharp
var index = blindIndexer.Compute(nationalId);   // IBlindIndexer from Common.Infrastructure
var match = await DbSet.FirstOrDefaultAsync(c => EF.Property<string>(c, "NationalId_bidx") == index, ct);
```

**Rules:**
- Never `Where`, `OrderBy`, `Contains`/`LIKE` or full-text search on an encrypted column. Only exact matches, through the blind index.
- Size encrypted columns for ciphertext (≈ 2–3× the plaintext length, plus a key-version prefix).
- The domain entity stays plain C#. Encryption is purely an EF configuration concern.
- Decrypted values never go into logs, exceptions, domain events or messages.

---

## 4. DbContext Structure

```csharp
// Infrastructure/Persistence/InventoryDbContext.cs
public sealed class InventoryDbContext(DbContextOptions<InventoryDbContext> options)
    : BaseDbContext(options), IInventoryUnitOfWork
{
    public DbSet<Product> Products => Set<Product>();                       // aggregate roots only
    public DbSet<StockReservation> StockReservations => Set<StockReservation>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);              // must call first (OutboxMessage config)
        modelBuilder.HasDefaultSchema("inventory");      // schema per module
        modelBuilder.ApplyConfigurationsFromAssembly(typeof(InventoryDbContext).Assembly);
    }
}
```

Registration (in `<Module>Module.cs`). The connection string comes from the **tenant**, never from a fixed configuration key:

```csharp
services.AddTenantDbContext<InventoryDbContext>(schema: "inventory");
```

**Rules:**
- `sealed class`, primary constructor passed straight to the base
- Implements `I<Module>UnitOfWork`
- `HasDefaultSchema`: always set, lowercase module name
- `base.OnModelCreating(modelBuilder)`: always called first
- No `DbSet` for child or owned entities
- Never inject or query another module's DbContext

---

## 5. Design-Time Factory

Required so `dotnet ef migrations add` works from the Infrastructure project. It points at a **local
scratch database** used only for creating migrations, not at a tenant database.

```csharp
// Infrastructure/Persistence/InventoryDbContextFactory.cs
public sealed class InventoryDbContextFactory : IDesignTimeDbContextFactory<InventoryDbContext>
{
    public InventoryDbContext CreateDbContext(string[] args)
    {
        var configuration = new ConfigurationBuilder()
            .AddUserSecrets(Assembly.GetExecutingAssembly(), optional: true)
            .AddEnvironmentVariables()
            .Build();

        var connectionString = configuration.GetConnectionString("design-time")
            ?? throw new InvalidOperationException("Connection string 'design-time' not found (set it in user-secrets).");

        var optionsBuilder = new DbContextOptionsBuilder<InventoryDbContext>();
        optionsBuilder.UseNpgsql(connectionString,
            b => b.MigrationsHistoryTable("__EFMigrationsHistory", "inventory"));   // per-schema history

        return new InventoryDbContext(optionsBuilder.Options);
    }
}
```

The `MigrationsHistoryTable("__EFMigrationsHistory", "<schema>")` call is **critical**. Each module keeps
its own history so migrations don't collide.

---

## 6. EF Migrations

### Add a migration (from the repo root)

```bash
dotnet ef migrations add <MigrationName> \
  --project src/Modules/<Module>/MediHub.Modules.<Module>.Infrastructure \
  --startup-project src/Modules/<Module>/MediHub.Modules.<Module>.Infrastructure \
  --context <Module>DbContext
```

Migrations land in `Infrastructure/Persistence/Migrations/`.

### Apply migrations

**Not** by the API, and not with `dotnet ef database update` against tenant databases.
`MediHub.MigrationService` applies every module's migrations to the catalog and to **every tenant
database**. Locally, Aspire runs it before the API starts (`aspire run`). To re-apply after adding a
migration, restart the AppHost or the `migrations` resource from the Aspire dashboard.

The module must be registered with the migration service:

```csharp
// <Module>Module.cs
public static void ConfigureMigrations(MigrationRegistry registry) => registry.Tenant<InventoryDbContext>();
```

### Inspect generated SQL / remove the last unapplied migration

```bash
dotnet ef migrations script --project … --startup-project … --context <Module>DbContext
dotnet ef migrations remove --project … --startup-project … --context <Module>DbContext
```

`remove` only works if the migration has not been applied anywhere. Once a migration has reached any
shared environment, add a new migration instead.

---

## 7. What Belongs Where

| Concern | Layer | File |
|---|---|---|
| Entity, factory, behaviour | Domain | `Domain/<EntityName>.cs` |
| Domain event | Domain | `Domain/Events/<EventName>DomainEvent.cs` |
| Enum | Domain | `Domain/<EntityName>.cs` or `Domain/<EnumName>.cs` |
| Errors | Domain | `Domain/Errors/<Entity>Errors.cs` |
| Repository interface | Domain | `Domain/I<EntityName>Repository.cs` |
| EF configuration (incl. encryption) | Infrastructure | `Infrastructure/Persistence/Configurations/<EntityName>Configuration.cs` |
| Repository implementation | Infrastructure | `Infrastructure/Persistence/<EntityName>Repository.cs` |
| Design-time factory | Infrastructure | `Infrastructure/Persistence/<Module>DbContextFactory.cs` |
| Migrations | Infrastructure | `Infrastructure/Persistence/Migrations/` |
| Migration registration | Infrastructure | `Infrastructure/Extensions/<Module>Module.cs` (`ConfigureMigrations`) |

---

## 8. Common Mistakes & Gotchas

| Mistake | Correct approach |
|---|---|
| `UseSqlServer`, SQL Server packages, `byte[] RowVersion` | Npgsql: `UseNpgsql`, `uint Version` + `IsRowVersion()` (xmin) |
| Fixed connection string in `AddDbContext` | `AddTenantDbContext<T>(schema)`; the tenant decides the database |
| `Database.MigrateAsync()` in the API host | Migrations run only in `MediHub.MigrationService` |
| Forgetting `ConfigureMigrations` for a new DbContext | Tenant databases never get the schema |
| Personal data in a domain event | IDs only; the event is stored in the outbox |
| Filtering/sorting on an encrypted column | Blind index for exact matches; otherwise the field must not be encrypted (decide per requirement) |
| `DateTime.Now` or non-UTC `DateTime` | `DateTime.UtcNow`; Npgsql rejects non-UTC values for `timestamptz` |
| `Guid.NewGuid()` for new entities | `Guid.CreateVersion7()` |
| Missing `private Entity() { }` | EF needs a parameterless constructor |
| `DbSet` for a child entity | Only aggregate roots get a `DbSet` |
| Missing `base.OnModelCreating(modelBuilder)` | Always call base first |
| Data annotations / inline config in `OnModelCreating` | Dedicated `IEntityTypeConfiguration<T>` class |
| Storing an enum as an integer | `.HasConversion<string>()` |
| Missing `HasPrecision` on `decimal` | Always set `(18, 2)` explicitly |
| Migration-history collision across modules | `MigrationsHistoryTable("__EFMigrationsHistory", "<schema>")` |
