---
name: dotnet-backend-modular-monolith-eventdriven-create-module
description: This skill should be used when the user asks to "create a module", "add a new module", "scaffold a module", "generate a module", "add a bounded context", or wants to add a new feature module to the MediHub modular monolith. Generates all 5 projects (Domain, Application, Infrastructure, IntegrationEvents, Presentation) following the MediHub module pattern (Postgres, database per tenant, permissions, migration service registration).
---

# Create Module

Generate a complete new module for the MediHub .NET 10 modular monolith.

**Usage:** `/create-module <ModuleName> [EntityName]`
- `ModuleName`: PascalCase module name
- `EntityName`: optional PascalCase entity name; if omitted, derive it from `ModuleName`

Arguments: $ARGUMENTS

## Before generating

- **Modules come from groomed requirements.** If the module isn't traceable to a requirement or Epic, ask before creating it. Don't invent hospital domain modules.
- Decide with the user whether the module is **tenant-scoped** (the default: its data lives in each hospital's database) or **catalog-level** (central group data, whose scope is still open). Templates assume tenant-scoped.
- Check that `src/Common` exists. If the solution hasn't been bootstrapped yet, say so and stop. Bootstrapping Common, the API host, the migration service and the AppHost is a separate task.

## Workflow

### Step 1: Parse arguments

Extract `ModuleName` (first word) and `EntityName` (second word, or derived). Derive `moduleName_lower`
(lowercase) for the schema name, permission prefix and URL path.

### Step 2: Generate all files

Load `references/module-templates.md` and generate every file across the 5 projects:

| Project | Key files |
|---|---|
| **Domain** | `.csproj`, `{EntityName}.cs`, `Errors/{EntityName}Errors.cs`, `I{EntityName}Repository.cs` |
| **Application** | `.csproj`, `Abstractions/I{ModuleName}UnitOfWork.cs`, `Permissions/{ModuleName}Permissions.cs`, `Create{EntityName}/` (command + handler + validator), `Get{ModuleName}/` (query + handler), `AssemblyReference.cs` |
| **IntegrationEvents** | `.csproj`, `{EntityName}CreatedEvent.cs` (IDs only), `AssemblyReference.cs` |
| **Infrastructure** | `.csproj`, `Persistence/{ModuleName}DbContext.cs`, `Persistence/{ModuleName}DbContextFactory.cs`, `Persistence/Configurations/{EntityName}Configuration.cs`, `Persistence/{EntityName}Repository.cs`, `Consumers/{EntityName}CreatedConsumer.cs`, `Extensions/{ModuleName}Module.cs`, `AssemblyReference.cs` |
| **Presentation** | `.csproj`, `{ModuleName}Endpoints.cs`, `AssemblyReference.cs` |

### Step 3: Post-generation wiring

Load `references/post-generation-steps.md` and show the user the exact commands and snippets to wire the
module into the solution, the API host and the **migration service**.

## Key conventions

- Project names `MediHub.Modules.{ModuleName}.{Layer}` under `src/Modules/{ModuleName}/`
- Schema name = `moduleName_lower` (`modelBuilder.HasDefaultSchema(...)`), with migration history in that schema
- DbContext registered with `AddTenantDbContext<{ModuleName}DbContext>("{moduleName_lower}")`, **never** a fixed connection string
- DbContext implements `I{ModuleName}UnitOfWork`
- Permissions `{moduleName_lower}.<resource>.<action>`, registered with `AddPermissions(...)`, required on every endpoint
- List queries take the user's `AccessScope` and filter inside SQL
- Integration events carry IDs only; consumers log IDs only
- `ConfigureMigrations` registers the DbContext with `MediHub.MigrationService`
- Cross-cutting rules: `.claude/skills/dotnet-backend-modular-monolith-eventdriven-architecture/references/medihub-platform-conventions.md`

## Additional Resources

- **`references/module-templates.md`**: complete C# templates for all 5 layers
- **`references/post-generation-steps.md`**: `dotnet sln add`, API host and migration-service wiring, the first EF migration
