# Post-Generation Wiring Steps

After generating all module files, show the user these steps. Offer to make the edits and run the commands.

---

## 1. Add the projects to the solution

```bash
dotnet sln MediHub.slnx add \
  src/Modules/{ModuleName}/MediHub.Modules.{ModuleName}.Domain/MediHub.Modules.{ModuleName}.Domain.csproj \
  src/Modules/{ModuleName}/MediHub.Modules.{ModuleName}.Application/MediHub.Modules.{ModuleName}.Application.csproj \
  src/Modules/{ModuleName}/MediHub.Modules.{ModuleName}.Infrastructure/MediHub.Modules.{ModuleName}.Infrastructure.csproj \
  src/Modules/{ModuleName}/MediHub.Modules.{ModuleName}.IntegrationEvents/MediHub.Modules.{ModuleName}.IntegrationEvents.csproj \
  src/Modules/{ModuleName}/MediHub.Modules.{ModuleName}.Presentation/MediHub.Modules.{ModuleName}.Presentation.csproj \
  --solution-folder Modules/{ModuleName}
```

Nx discovers the new projects through its .NET plugin. Check with `npx nx show projects`.

---

## 2. Reference the module from the API host

`src/Api/MediHub.Api/MediHub.Api.csproj`:

```xml
<ProjectReference Include="..\..\Modules\{ModuleName}\MediHub.Modules.{ModuleName}.Infrastructure\MediHub.Modules.{ModuleName}.Infrastructure.csproj" />
<ProjectReference Include="..\..\Modules\{ModuleName}\MediHub.Modules.{ModuleName}.Presentation\MediHub.Modules.{ModuleName}.Presentation.csproj" />
```

## 3. Update the API host's `Program.cs`

```csharp
using MediHub.Modules.{ModuleName}.Infrastructure.Extensions;

builder.Services.Add{ModuleName}Module(builder.Configuration);   // alongside the other Add*Module calls

builder.Services.AddInfrastructure(
    [
        // ... existing modules ...
        {ModuleName}Module.ConfigureConsumers,   // ← add
    ],
    builder.Configuration);
```

The API host **does not** run migrations. Never add `MigrateAsync` calls here.

## 4. Update `WebApplicationExtensions.cs`

`src/Api/MediHub.Api/Extensions/WebApplicationExtensions.cs`:

```csharp
using MediHub.Modules.{ModuleName}.Presentation;

// inside MapEndpoints():
app.Map{ModuleName}Endpoints();
```

---

## 5. Register the module with the migration service

`src/Tools/MediHub.MigrationService/MediHub.MigrationService.csproj`:

```xml
<ProjectReference Include="..\..\Modules\{ModuleName}\MediHub.Modules.{ModuleName}.Infrastructure\MediHub.Modules.{ModuleName}.Infrastructure.csproj" />
```

`src/Tools/MediHub.MigrationService/Program.cs`:

```csharp
using MediHub.Modules.{ModuleName}.Infrastructure.Extensions;

builder.Services.AddMigrationService(
    [
        // ... existing modules ...
        {ModuleName}Module.ConfigureMigrations,   // ← add
    ],
    builder.Configuration);
```

Without this step the module's schema is never created in the tenant databases.

---

## 6. Create the initial EF migration

Make sure `ConnectionStrings:design-time` is set in the Infrastructure project's user-secrets (a local
scratch Postgres database, e.g. on the Aspire Postgres container):

```bash
dotnet user-secrets set "ConnectionStrings:design-time" "<local postgres connection string>" \
  --project src/Modules/{ModuleName}/MediHub.Modules.{ModuleName}.Infrastructure

dotnet ef migrations add Initial_{ModuleName} \
  --project src/Modules/{ModuleName}/MediHub.Modules.{ModuleName}.Infrastructure \
  --startup-project src/Modules/{ModuleName}/MediHub.Modules.{ModuleName}.Infrastructure \
  --context {ModuleName}DbContext
```

The initial migration includes the module's `OutboxMessages` table (from `BaseDbContext`).

---

## 7. Build and run

```bash
dotnet build MediHub.slnx            # or: npx nx affected -t build
aspire run                           # or: npx nx run apphost:serve
```

In the Aspire dashboard, check that:
- the `migrations` resource finished successfully, so the new schema exists in every demo tenant database;
- the API started, and its Scalar UI shows the new endpoints;
- RabbitMQ (via the dashboard link to its management UI) shows queues for the new consumers.

---

## Notes

- If the module's endpoints should appear in the web or mobile app, regenerate the orval client (`packages/api-client`) after the API's OpenAPI document changes.
- Tell the user which **permissions** were declared, because hospital administrators will bundle them into roles.
- No existing module is a reference yet. The templates in `module-templates.md` are the canonical pattern until the first real module exists.
