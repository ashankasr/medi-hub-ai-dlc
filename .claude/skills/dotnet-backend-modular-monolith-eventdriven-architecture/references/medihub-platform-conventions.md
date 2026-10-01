# MediHub Platform Conventions

The single source of truth for the cross-cutting rules every backend skill must follow.
These rules come from [`architecture/high-level-architecture.md`](../../../../architecture/high-level-architecture.md).
If the two ever disagree, the architecture document wins. Point out the conflict instead of guessing.

> **Bootstrap status.** No backend code exists yet. The type and method names below
> (`ITenantContext`, `AddTenantDbContext`, `IsEncrypted()` …) are the **target API**
> for the `MediHub.Common.*` projects. Build them as described when bootstrapping
> `Common`, and keep this file in sync if a name changes.

---

## 1. Names, paths, versions

| Item | Convention |
|---|---|
| Solution | `MediHub.slnx` at the repo root (with `Directory.Build.props`, `Directory.Packages.props`, `global.json`) |
| Module projects | `src/Modules/<Name>/MediHub.Modules.<Name>.{Domain,Application,Infrastructure,IntegrationEvents,Presentation}` |
| Shared projects | `src/Common/MediHub.Common.{Domain,Application,Infrastructure}` |
| API host | `src/Api/MediHub.Api` |
| Migration service | `src/Tools/MediHub.MigrationService` |
| Aspire | `src/Aspire/MediHub.AppHost`, `src/Aspire/MediHub.ServiceDefaults` |
| Runtime | .NET 10, EF Core 10 with **Npgsql** (`Npgsql.EntityFrameworkCore.PostgreSQL`); **no SQL Server** |
| Libraries | MediatR (commercial, licence key from configuration `MediatR:LicenseKey`), MassTransit v9 (commercial, licence from secrets), FluentValidation, Mapster, Quartz, Scalar (API reference UI) |
| Package versions | Only in `Directory.Packages.props` (Central Package Management) |
| Local run | **Aspire**, not docker-compose: `aspire run` or `npx nx run apphost:serve` |
| Identifiers | `Guid.CreateVersion7()` for new entity IDs (time-ordered, index-friendly in Postgres) |
| Timestamps | UTC only (`DateTime.UtcNow`). Npgsql maps `DateTime` to `timestamptz` and rejects non-UTC values. |

Connection-string names come from Aspire resource names: `catalog` (tenant catalog
database), `rabbitmq`, `redis`. If the AppHost renames a resource, update this table.

---

## 2. Multi-tenancy: database per tenant

- Tenant = hospital. Each tenant has its **own database**. Inside it, every module owns a **schema** named after the module in lowercase.
- A central **catalog** database holds the tenant registry (and any group-level data, whose scope is still open).
- **Tenant context** (`ITenantContext` in `Common.Application/Abstractions/Tenancy`) is set at every entry point, and only there:

| Entry point | Source of the tenant | Set by |
|---|---|---|
| HTTP request | The **validated token's active-organization claim** (Keycloak Organizations), mapped to a tenant via the catalog. **Never** a client-supplied header or route value. | `TenantResolutionMiddleware` (Common.Infrastructure) |
| MassTransit message | Header `medihub-tenant-id`, added automatically on publish/send | Tenant publish/send/consume filters registered in `AddInfrastructure` |
| Background job (Quartz) | Explicit loop over tenants from the catalog, one DI scope per tenant | `ITenantJobRunner.ForEachTenantAsync(...)` |

A message or request with no resolvable tenant **fails**. It never falls back to a default tenant.

### Tenant-scoped DbContext registration

Module DbContexts never read a fixed connection string. Register them with the Common helper:

```csharp
services.AddTenantDbContext<InventoryDbContext>(schema: "inventory");
```

which is equivalent to:

```csharp
services.AddDbContext<InventoryDbContext>((sp, opts) =>
{
    var tenant = sp.GetRequiredService<ITenantContext>();
    var connectionString = sp.GetRequiredService<ITenantConnectionResolver>()
                             .GetConnectionString(tenant.TenantId);   // looked up in the catalog

    opts.UseNpgsql(connectionString,
            npgsql => npgsql.MigrationsHistoryTable("__EFMigrationsHistory", "inventory"))
        .AddInterceptors(sp.GetRequiredService<OutboxMessagesInterceptor>());
});
```

Catalog-level DbContexts (e.g. the Tenancy module) use `services.AddCatalogDbContext<TContext>(schema)`,
which reads `ConnectionStrings:catalog`.

### Caching (HybridCache / Redis)

Every cache key starts with the tenant: `t:{tenantId}:<module>:<key>`. Use `TenantCacheKey.For(...)`.
Never cache decrypted personal data unless the requirement explicitly allows it.

---

## 3. Migrations: the migration service, never the API

- The API host **never** calls `Database.MigrateAsync()`.
- `MediHub.MigrationService` (a worker project) applies migrations to the **catalog** once, then to **every tenant database** listed in the catalog, for every module DbContext.
- Aspire runs it before the API (`api.WaitForCompletion(migrations)`). In production it runs as a Container Apps Job. Production details belong in the production architecture document.
- Each module tells the migration service about its DbContext:

```csharp
// Infrastructure/Extensions/<Module>Module.cs
public static void ConfigureMigrations(MigrationRegistry registry) =>
    registry.Tenant<InventoryDbContext>();      // or registry.Catalog<TContext>() for catalog-level modules
```

and the migration service's `Program.cs` lists `<Module>Module.ConfigureMigrations` for every module.
- **Creating** a migration uses a design-time factory pointed at a local scratch database
  (`ConnectionStrings:design-time` in user-secrets). See the domain-ef skill.
- Provisioning a new tenant database at runtime will reuse the migration service's code path.
  That design belongs to the Tenancy module and is not decided yet.

---

## 4. Messaging

- MassTransit over RabbitMQ, configured once in `AddInfrastructure` (Common.Infrastructure) from `ConnectionStrings:rabbitmq`. That includes retry, the tenant filters and the licence.
- Modules talk to each other **only** through integration events, saga commands and request/response contracts, all defined in the owning module's `IntegrationEvents` project.

### Messages carry identifiers, not personal data

Applies to **integration events, saga commands, domain events (they are stored in outbox rows) and saga state**.

| Allowed | Not allowed |
|---|---|
| IDs (`Guid`), correlation IDs, status/enum values, reason **codes**, UTC timestamps, quantities and amounts | Names, e-mail addresses, phone numbers, postal addresses, national IDs, dates of birth, diagnoses, clinical free text, or free-text reasons that could contain any of these |

A consumer that needs more detail asks the owning module with **MassTransit request/response**:

```csharp
// Owning module: IntegrationEvents
public sealed record GetProductDetails(Guid ProductId);
public sealed record ProductDetails(Guid ProductId, string Name, string Sku);
public sealed record ProductNotFound(Guid ProductId);

// Owning module: Infrastructure/Consumers — answers the request
public sealed class GetProductDetailsConsumer(InventoryDbContext db) : IConsumer<GetProductDetails>
{
    public async Task Consume(ConsumeContext<GetProductDetails> context)
    {
        var p = await db.Products.AsNoTracking()
            .FirstOrDefaultAsync(x => x.Id == context.Message.ProductId, context.CancellationToken);
        if (p is null) { await context.RespondAsync(new ProductNotFound(context.Message.ProductId)); return; }
        await context.RespondAsync(new ProductDetails(p.Id, p.Name, p.Sku));
    }
}

// Requesting module: inject IRequestClient<GetProductDetails>
var response = await client.GetResponse<ProductDetails, ProductNotFound>(new GetProductDetails(id), ct);
```

Request/response payloads: keep them to the fields the caller needs, and **never log them or store them
in saga state or outbox rows**. Whether such payloads must also be encrypted while they pass through the
broker is an open item in the architecture document.

### Outbox

The outbox (domain events → `OutboxMessage` rows → Quartz → domain event handlers → MassTransit) is
described in the architecture skill. **Delivering outbox messages across many tenant databases** (looping
tenants, preventing double delivery when several API replicas run) is an **open design decision** to be
revisited with the project owner. Do not invent a variant. If a task depends on it, stop and raise it.

---

## 5. Authorization: granular permissions, built in the app

Keycloak authenticates users and states which hospitals they belong to. **Permissions are not in the
token.** They are resolved on the server from the roles a hospital administrator assigned at runtime,
cached in HybridCache, and invalidated when roles change.

### Permissions are declared in code, per module

```csharp
// Application/Permissions/InventoryPermissions.cs
public static class InventoryPermissions
{
    public const string ProductsRead   = "inventory.products.read";
    public const string ProductsManage = "inventory.products.manage";

    public static readonly string[] All = [ProductsRead, ProductsManage];
}
```

- Format: `<module>.<resource>.<action>`, lowercase.
- Register them in `Add<Module>Module`: `services.AddPermissions(InventoryPermissions.All);`. The Access module builds the catalog from these registrations; hospital administrators bundle them into roles.

### Every endpoint states its permission

```csharp
group.MapGet("/products", ...).RequireAuthorization(InventoryPermissions.ProductsRead);
```

A policy provider in Common.Infrastructure treats each policy name as a permission and checks it against
the user's roles **in the active tenant**. Route groups call `.RequireAuthorization()` as a baseline.
Anonymous endpoints are a deliberate, reviewed exception.

### Lists show only what the user may see: filter inside the query

`ICurrentUser` (Common.Application/Abstractions/Identity) exposes `UserId`, `TenantId`,
`HasPermission(string)` and `Scope` (the departments/wards the user's assignments are narrowed to, or
unrestricted).

```csharp
// Repository — apply the scope to the IQueryable BEFORE paging, counting or materialising
public Task<List<Product>> ListAsync(AccessScope scope, int skip, int take, CancellationToken ct) =>
    DbSet.AsNoTracking()
         .Where(p => scope.IsUnrestricted || scope.DepartmentIds.Contains(p.DepartmentId))
         .OrderBy(p => p.Id)
         .Skip(skip).Take(take)
         .ToListAsync(ct);
```

- **Never** load everything and filter in memory (it breaks paging and counts, and loads data the user may not see).
- A single record outside the user's scope is reported as **not found** (404), not 403, so its existence isn't revealed.
- Rules beyond department/ward (care relationship, consent, break-the-glass) belong to the Access module. Their shape is not designed yet, so don't invent them in a module.

### Some users see more fields on the same endpoint

- Permission-gated response fields are **nullable** in the DTO (and therefore optional in OpenAPI and in the orval-generated client).
- The query handler populates them only when `currentUser.HasPermission(...)` allows it, preferably inside the projection, so the data is never loaded or decrypted for users who can't see it.
- **Which** fields are gated is decided per requirement. If a requirement doesn't say, ask; don't decide silently.

---

## 6. Application-level encryption of personal data

- Personal data fields chosen for encryption are encrypted **by the application** before they reach Postgres: AES-GCM with the **tenant's data key**, which is wrapped by a master key (local developer secret in development, Azure Key Vault in production).
- Mark them in the EF configuration:

```csharp
builder.Property(p => p.NationalId).IsEncrypted();                    // ciphertext column
builder.Property(p => p.NationalId).IsEncrypted(blindIndex: true);    // + shadow column NationalId_bidx (HMAC) for exact-match lookups
```

- Encrypted columns **cannot** be used in `Where`, `OrderBy`, `LIKE`/`pg_trgm` or unique indexes. Use the blind-index column for exact matches, and put unique indexes on the blind index, not the ciphertext.
- **Which fields** are encrypted is decided per requirement during grooming. If a requirement introduces a personal-data field without saying, **ask**.

---

## 7. Logging, errors and telemetry

- **No personal or clinical data** in logs, exception messages, traces, metric tags or `Error` descriptions. Log identifiers only.
- `LoggingBehavior` logs the request **type name**, elapsed time and outcome (success, or the error **code**). It never logs request or response payloads. Never destructure (`{@Request}`) commands, queries, DTOs or messages.
- `Error` descriptions are returned to clients and end up in logs, so they must not contain personal data.

---

## 8. Audit

`AuditableEntity` records `CreatedAt`/`UpdatedAt` only. **Clinical-grade audit** (who read or changed
what, including reads) is a platform capability whose design is **pending a separate discussion**. Don't
build ad-hoc audit tables or per-module audit logic in the meantime.
