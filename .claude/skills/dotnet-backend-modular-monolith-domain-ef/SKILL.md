---
name: dotnet-backend-modular-monolith-domain-ef
description: Use this skill when the user asks to "add an entity", "model the domain", "configure EF", "add a migration", "add a DbSet", "map a table", "configure a relationship", "add an index", "add an enum property", "add a value object", "add an owned entity", "encrypt a field", "run migrations", or asks how domain entities and EF Core (Postgres) configuration work in the MediHub backend.
---

# Domain Implementation, EF Configuration & Migrations (Postgres, database per tenant)

This skill guides implementation of domain entities, EF Core entity configuration, the design-time
factory and EF migrations for the MediHub backend: EF Core 10 with **Npgsql/Postgres**, **database per
tenant**, schema per module.

Load `references/domain-ef-patterns.md` for the complete reference covering:

1. **Domain entity patterns**: aggregate roots, child entities, value objects, enums, behaviour methods, domain events (IDs only)
2. **EF entity configuration**: `IEntityTypeConfiguration<T>` classes; keys, lengths, precision, enum-as-string, indexes, relationships, owned entities, concurrency (`xmin`)
3. **Personal data**: application-level encryption with `IsEncrypted()`, and blind indexes
4. **DbContext structure**: `BaseDbContext`, `IUnitOfWork`, schema, tenant-scoped registration
5. **Design-time factory**: needed for `dotnet ef`
6. **EF migrations**: add, inspect and remove; applying them is done by `MediHub.MigrationService`

Cross-cutting rules (tenancy, encryption, messaging, logging) are in
`.claude/skills/dotnet-backend-modular-monolith-eventdriven-architecture/references/medihub-platform-conventions.md`.

## How to use

When asked to add or change domain or persistence:
1. Read the requirement. If it introduces **personal data** and doesn't say whether a field is encrypted, **ask** (conventions §6).
2. Load `references/domain-ef-patterns.md`.
3. Implement the domain entity first (pure C#, no EF references).
4. Add a `<Entity>Configuration : IEntityTypeConfiguration<T>` class in `Infrastructure/Persistence/Configurations/`.
5. Add the `DbSet<T>` (aggregate roots only) to the module DbContext.
6. Create the migration from the module's Infrastructure project.
7. Make sure the module's DbContext is registered with the migration service (`ConfigureMigrations`).

No backend code exists yet. The Inventory/Orders code in the reference is **illustrative**. Follow its
shape, not its business content.
