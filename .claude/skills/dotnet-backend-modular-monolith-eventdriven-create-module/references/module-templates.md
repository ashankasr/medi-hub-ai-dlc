# Module File Templates

Complete C# templates for all 5 projects. Replace placeholders:
- `{ModuleName}`: PascalCase module name
- `{EntityName}`: PascalCase entity name
- `{moduleName_lower}`: lowercase, for schema, permission prefix and URLs
- `{entityName_lower}`: lowercase entity name, for the permission resource segment

Package versions live in `Directory.Packages.props`, so `.csproj` files carry no `Version` attributes.
`TargetFramework`, nullable and implicit usings come from `Directory.Build.props`.

---

## 1. Domain Project

### `MediHub.Modules.{ModuleName}.Domain.csproj`
```xml
<Project Sdk="Microsoft.NET.Sdk">
  <ItemGroup>
    <ProjectReference Include="..\..\..\Common\MediHub.Common.Domain\MediHub.Common.Domain.csproj" />
    <ProjectReference Include="..\..\..\Common\MediHub.Common.Application\MediHub.Common.Application.csproj" />
  </ItemGroup>
</Project>
```

### `{EntityName}.cs`
```csharp
using MediHub.Common.Domain.Primitives;
using MediHub.Common.Domain.Results;
using MediHub.Modules.{ModuleName}.Domain.Errors;
using MediHub.Modules.{ModuleName}.Domain.Events;

namespace MediHub.Modules.{ModuleName}.Domain;

public sealed class {EntityName} : AuditableGuidEntity
{
    private {EntityName}() { }   // EF Core

    private {EntityName}(Guid id, string name, Guid departmentId) : base(id)
    {
        Name = name;
        DepartmentId = departmentId;
        RaiseDomainEvent(new {EntityName}CreatedDomainEvent(id));   // IDs only
    }

    public string Name { get; private set; } = string.Empty;
    public Guid DepartmentId { get; private set; }   // access-scope key — remove only if the requirement says records aren't scoped
    // TODO: add domain-specific properties (ask whether personal-data fields are encrypted)

    public static Result<{EntityName}> Create(Guid id, string name, Guid departmentId)
    {
        if (string.IsNullOrWhiteSpace(name))
            return Result.Failure<{EntityName}>({EntityName}Errors.NameRequired);

        return new {EntityName}(id, name, departmentId);
    }
}
```

### `Events/{EntityName}CreatedDomainEvent.cs`
```csharp
using MediHub.Common.Domain.Primitives;

namespace MediHub.Modules.{ModuleName}.Domain.Events;

public sealed record {EntityName}CreatedDomainEvent(Guid {EntityName}Id) : DomainEvent;
```

### `Errors/{EntityName}Errors.cs`
```csharp
using MediHub.Common.Domain.Results;

namespace MediHub.Modules.{ModuleName}.Domain.Errors;

public static class {EntityName}Errors
{
    public static readonly Error NameRequired =
        Error.Validation("{ModuleName}.{EntityName}NameRequired", "Name is required.");

    public static Error NotFound(Guid id) =>
        Error.NotFound("{ModuleName}.{EntityName}NotFound", $"{EntityName} '{id}' was not found.");
}
```

### `I{EntityName}Repository.cs`
```csharp
using MediHub.Common.Application.Abstractions;
using MediHub.Common.Application.Abstractions.Identity;

namespace MediHub.Modules.{ModuleName}.Domain;

public interface I{EntityName}Repository : IRepository<{EntityName}, Guid>
{
    Task<{EntityName}?> GetByIdAsync(Guid id, AccessScope scope, CancellationToken cancellationToken = default);
    Task<PagedResult<{EntityName}>> ListAsync(AccessScope scope, int page, int pageSize, CancellationToken cancellationToken = default);
}
```

---

## 2. Application Project

### `MediHub.Modules.{ModuleName}.Application.csproj`
```xml
<Project Sdk="Microsoft.NET.Sdk">
  <ItemGroup>
    <ProjectReference Include="..\MediHub.Modules.{ModuleName}.Domain\MediHub.Modules.{ModuleName}.Domain.csproj" />
    <ProjectReference Include="..\MediHub.Modules.{ModuleName}.IntegrationEvents\MediHub.Modules.{ModuleName}.IntegrationEvents.csproj" />
    <ProjectReference Include="..\..\..\Common\MediHub.Common.Application\MediHub.Common.Application.csproj" />
  </ItemGroup>
  <ItemGroup>
    <PackageReference Include="Mapster" />
  </ItemGroup>
</Project>
```

### `Abstractions/I{ModuleName}UnitOfWork.cs`
```csharp
using MediHub.Common.Application.Abstractions;

namespace MediHub.Modules.{ModuleName}.Application.Abstractions;

public interface I{ModuleName}UnitOfWork : IUnitOfWork;
```

### `Permissions/{ModuleName}Permissions.cs`
```csharp
namespace MediHub.Modules.{ModuleName}.Application.Permissions;

public static class {ModuleName}Permissions
{
    public const string {EntityName}sRead   = "{moduleName_lower}.{entityName_lower}s.read";
    public const string {EntityName}sManage = "{moduleName_lower}.{entityName_lower}s.manage";

    public static readonly string[] All = [{EntityName}sRead, {EntityName}sManage];
}
```

### `Create{EntityName}/Create{EntityName}Command.cs`
```csharp
using MediHub.Common.Application.Abstractions;

namespace MediHub.Modules.{ModuleName}.Application.Create{EntityName};

public sealed record Create{EntityName}Command(string Name, Guid DepartmentId) : ICommand<Create{EntityName}Response>;
public sealed record Create{EntityName}Response(Guid Id);
```

### `Create{EntityName}/Create{EntityName}CommandHandler.cs`
```csharp
using MediHub.Common.Application.Abstractions;
using MediHub.Common.Domain.Results;
using MediHub.Modules.{ModuleName}.Application.Abstractions;
using MediHub.Modules.{ModuleName}.Domain;

namespace MediHub.Modules.{ModuleName}.Application.Create{EntityName};

public sealed class Create{EntityName}CommandHandler(
    I{EntityName}Repository repository,
    I{ModuleName}UnitOfWork unitOfWork) : ICommandHandler<Create{EntityName}Command, Create{EntityName}Response>
{
    public async Task<Result<Create{EntityName}Response>> Handle(
        Create{EntityName}Command command,
        CancellationToken cancellationToken)
    {
        var result = {EntityName}.Create(Guid.CreateVersion7(), command.Name, command.DepartmentId);
        if (result.IsFailure)
            return Result.Failure<Create{EntityName}Response>(result.Error);

        repository.Add(result.Value);
        await unitOfWork.SaveChangesAsync(cancellationToken);   // domain event → outbox, same transaction
        return new Create{EntityName}Response(result.Value.Id);
    }
}
```

### `Create{EntityName}/Create{EntityName}CommandValidator.cs`
```csharp
using FluentValidation;

namespace MediHub.Modules.{ModuleName}.Application.Create{EntityName};

public sealed class Create{EntityName}CommandValidator : AbstractValidator<Create{EntityName}Command>
{
    public Create{EntityName}CommandValidator()
    {
        RuleFor(x => x.Name).NotEmpty().MaximumLength(200);
        RuleFor(x => x.DepartmentId).NotEmpty();
    }
}
```

### `Get{ModuleName}/Get{ModuleName}Query.cs`
```csharp
using MediHub.Common.Application.Abstractions;

namespace MediHub.Modules.{ModuleName}.Application.Get{ModuleName};

public sealed record Get{ModuleName}Query(int Page = 1, int PageSize = 50) : IQuery<PagedResult<{EntityName}Response>>;
public sealed record {EntityName}Response(Guid Id, string Name, DateTime CreatedAt);
```

### `Get{ModuleName}/Get{ModuleName}QueryHandler.cs`
```csharp
using MediHub.Common.Application.Abstractions;
using MediHub.Common.Application.Abstractions.Identity;
using MediHub.Common.Domain.Results;
using MediHub.Modules.{ModuleName}.Domain;

namespace MediHub.Modules.{ModuleName}.Application.Get{ModuleName};

public sealed class Get{ModuleName}QueryHandler(
    I{EntityName}Repository repository,
    ICurrentUser currentUser) : IQueryHandler<Get{ModuleName}Query, PagedResult<{EntityName}Response>>
{
    public async Task<Result<PagedResult<{EntityName}Response>>> Handle(
        Get{ModuleName}Query query,
        CancellationToken cancellationToken)
    {
        // Filtered to what the user may see — inside the SQL query, before paging
        var page = await repository.ListAsync(currentUser.Scope, query.Page, query.PageSize, cancellationToken);
        return page.Map(x => new {EntityName}Response(x.Id, x.Name, x.CreatedAt));
    }
}
```

### `{EntityName}Created/{EntityName}CreatedDomainEventHandler.cs`
```csharp
using MediHub.Common.Application.Abstractions;
using MediHub.Modules.{ModuleName}.Domain.Events;
using MediHub.Modules.{ModuleName}.IntegrationEvents;

namespace MediHub.Modules.{ModuleName}.Application.{EntityName}Created;

public sealed class {EntityName}CreatedDomainEventHandler(IEventBus eventBus)
    : IDomainEventHandler<{EntityName}CreatedDomainEvent>
{
    public Task Handle(DomainEventNotification<{EntityName}CreatedDomainEvent> notification, CancellationToken cancellationToken) =>
        eventBus.PublishAsync(
            new {EntityName}CreatedEvent(notification.DomainEvent.{EntityName}Id, notification.DomainEvent.OccurredOn),
            cancellationToken);
}
```

### `AssemblyReference.cs`
```csharp
namespace MediHub.Modules.{ModuleName}.Application;
public sealed class AssemblyReference;
```

---

## 3. IntegrationEvents Project

### `MediHub.Modules.{ModuleName}.IntegrationEvents.csproj`
```xml
<Project Sdk="Microsoft.NET.Sdk">
  <!-- Pure contract library: no project or package references -->
</Project>
```

### `{EntityName}CreatedEvent.cs`
```csharp
namespace MediHub.Modules.{ModuleName}.IntegrationEvents;

// IDs, codes and timestamps only — never personal data
public sealed record {EntityName}CreatedEvent(Guid {EntityName}Id, DateTime OccurredAt);
```

### `AssemblyReference.cs`
```csharp
namespace MediHub.Modules.{ModuleName}.IntegrationEvents;
public sealed class AssemblyReference;
```

---

## 4. Infrastructure Project

### `MediHub.Modules.{ModuleName}.Infrastructure.csproj`
```xml
<Project Sdk="Microsoft.NET.Sdk">
  <ItemGroup>
    <ProjectReference Include="..\MediHub.Modules.{ModuleName}.Application\MediHub.Modules.{ModuleName}.Application.csproj" />
    <ProjectReference Include="..\..\..\Common\MediHub.Common.Infrastructure\MediHub.Common.Infrastructure.csproj" />
    <!-- Cross-module IntegrationEvents references go here when needed, e.g.
         <ProjectReference Include="..\..\Other\MediHub.Modules.Other.IntegrationEvents\MediHub.Modules.Other.IntegrationEvents.csproj" /> -->
  </ItemGroup>
  <ItemGroup>
    <PackageReference Include="Npgsql.EntityFrameworkCore.PostgreSQL" />
    <PackageReference Include="Microsoft.EntityFrameworkCore.Design">
      <PrivateAssets>all</PrivateAssets>
      <IncludeAssets>runtime; build; native; contentfiles; analyzers; buildtransitive</IncludeAssets>
    </PackageReference>
    <PackageReference Include="Microsoft.Extensions.Configuration.UserSecrets" />
  </ItemGroup>
</Project>
```

### `Persistence/{ModuleName}DbContext.cs`
```csharp
using Microsoft.EntityFrameworkCore;
using MediHub.Common.Infrastructure.Persistence;
using MediHub.Modules.{ModuleName}.Application.Abstractions;
using MediHub.Modules.{ModuleName}.Domain;

namespace MediHub.Modules.{ModuleName}.Infrastructure.Persistence;

public sealed class {ModuleName}DbContext(DbContextOptions<{ModuleName}DbContext> options)
    : BaseDbContext(options), I{ModuleName}UnitOfWork
{
    public DbSet<{EntityName}> {EntityName}s => Set<{EntityName}>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);
        modelBuilder.HasDefaultSchema("{moduleName_lower}");
        modelBuilder.ApplyConfigurationsFromAssembly(typeof({ModuleName}DbContext).Assembly);
    }
}
```

### `Persistence/{ModuleName}DbContextFactory.cs`
```csharp
using System.Reflection;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Design;
using Microsoft.Extensions.Configuration;

namespace MediHub.Modules.{ModuleName}.Infrastructure.Persistence;

// Design-time only (dotnet ef migrations add) — points at a local scratch database, not a tenant database
public sealed class {ModuleName}DbContextFactory : IDesignTimeDbContextFactory<{ModuleName}DbContext>
{
    public {ModuleName}DbContext CreateDbContext(string[] args)
    {
        var configuration = new ConfigurationBuilder()
            .AddUserSecrets(Assembly.GetExecutingAssembly(), optional: true)
            .AddEnvironmentVariables()
            .Build();

        var connectionString = configuration.GetConnectionString("design-time")
            ?? throw new InvalidOperationException("Connection string 'design-time' not found (set it in user-secrets).");

        var options = new DbContextOptionsBuilder<{ModuleName}DbContext>()
            .UseNpgsql(connectionString, b => b.MigrationsHistoryTable("__EFMigrationsHistory", "{moduleName_lower}"))
            .Options;

        return new {ModuleName}DbContext(options);
    }
}
```

### `Persistence/Configurations/{EntityName}Configuration.cs`
```csharp
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using MediHub.Modules.{ModuleName}.Domain;

namespace MediHub.Modules.{ModuleName}.Infrastructure.Persistence.Configurations;

public sealed class {EntityName}Configuration : IEntityTypeConfiguration<{EntityName}>
{
    public void Configure(EntityTypeBuilder<{EntityName}> builder)
    {
        builder.ToTable("{EntityName}s");
        builder.HasKey(x => x.Id);
        builder.Property(x => x.Name).IsRequired().HasMaxLength(200);
        builder.HasIndex(x => x.DepartmentId);   // access-scope filter
        // TODO: remaining properties; personal-data fields → .IsEncrypted() if the requirement says so
    }
}
```

### `Persistence/{EntityName}Repository.cs`
```csharp
using Microsoft.EntityFrameworkCore;
using MediHub.Common.Application.Abstractions;
using MediHub.Common.Application.Abstractions.Identity;
using MediHub.Common.Infrastructure.Persistence;
using MediHub.Modules.{ModuleName}.Domain;

namespace MediHub.Modules.{ModuleName}.Infrastructure.Persistence;

public sealed class {EntityName}Repository({ModuleName}DbContext dbContext)
    : BaseRepository<{EntityName}, Guid, {ModuleName}DbContext>(dbContext), I{EntityName}Repository
{
    private IQueryable<{EntityName}> Scoped(AccessScope scope) =>
        DbSet.Where(x => scope.IsUnrestricted || scope.DepartmentIds.Contains(x.DepartmentId));

    public Task<{EntityName}?> GetByIdAsync(Guid id, AccessScope scope, CancellationToken cancellationToken = default) =>
        Scoped(scope).FirstOrDefaultAsync(x => x.Id == id, cancellationToken);

    public async Task<PagedResult<{EntityName}>> ListAsync(AccessScope scope, int page, int pageSize, CancellationToken cancellationToken = default)
    {
        var query = Scoped(scope).AsNoTracking();
        var total = await query.CountAsync(cancellationToken);
        var items = await query.OrderBy(x => x.Id)
            .Skip((page - 1) * pageSize).Take(pageSize)
            .ToListAsync(cancellationToken);
        return new PagedResult<{EntityName}>(items, total, page, pageSize);
    }
}
```

### `Consumers/{EntityName}CreatedConsumer.cs`
```csharp
using MassTransit;
using Microsoft.Extensions.Logging;
using MediHub.Modules.{ModuleName}.IntegrationEvents;

namespace MediHub.Modules.{ModuleName}.Infrastructure.Consumers;

// Example consumer — replace with real cross-module logic or delete
public sealed class {EntityName}CreatedConsumer(
    ILogger<{EntityName}CreatedConsumer> logger) : IConsumer<{EntityName}CreatedEvent>
{
    public Task Consume(ConsumeContext<{EntityName}CreatedEvent> context)
    {
        logger.LogInformation("[CHOREOGRAPHY] {EntityName} created: {Id}", context.Message.{EntityName}Id);   // IDs only
        return Task.CompletedTask;
    }
}
```

### `Extensions/{ModuleName}Module.cs`
```csharp
using MassTransit;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using MediHub.Common.Application.Extensions;
using MediHub.Common.Infrastructure.Authorization;
using MediHub.Common.Infrastructure.Migrations;
using MediHub.Common.Infrastructure.Outbox;
using MediHub.Common.Infrastructure.Persistence;
using MediHub.Modules.{ModuleName}.Application.Abstractions;
using MediHub.Modules.{ModuleName}.Application.Permissions;
using MediHub.Modules.{ModuleName}.Domain;
using MediHub.Modules.{ModuleName}.Infrastructure.Consumers;
using MediHub.Modules.{ModuleName}.Infrastructure.Persistence;

namespace MediHub.Modules.{ModuleName}.Infrastructure.Extensions;

public static class {ModuleName}Module
{
    public static IServiceCollection Add{ModuleName}Module(
        this IServiceCollection services,
        IConfiguration configuration)
    {
        services.AddTenantDbContext<{ModuleName}DbContext>(schema: "{moduleName_lower}");   // tenant connection + outbox interceptor

        services.AddScoped<I{ModuleName}UnitOfWork>(sp => sp.GetRequiredService<{ModuleName}DbContext>());
        services.AddScoped<I{EntityName}Repository, {EntityName}Repository>();
        services.AddScoped<IOutboxMessageProcessor, OutboxMessageProcessor<{ModuleName}DbContext>>();

        services.AddApplication(typeof(Application.AssemblyReference).Assembly);
        services.AddPermissions({ModuleName}Permissions.All);

        return services;
    }

    public static void ConfigureConsumers(IRegistrationConfigurator configurator)
    {
        configurator.AddConsumer<{EntityName}CreatedConsumer>();
    }

    public static void ConfigureMigrations(MigrationRegistry registry) =>
        registry.Tenant<{ModuleName}DbContext>();
}
```

### `AssemblyReference.cs`
```csharp
namespace MediHub.Modules.{ModuleName}.Infrastructure;
public sealed class AssemblyReference;
```

---

## 5. Presentation Project

### `MediHub.Modules.{ModuleName}.Presentation.csproj`
```xml
<Project Sdk="Microsoft.NET.Sdk">
  <ItemGroup>
    <FrameworkReference Include="Microsoft.AspNetCore.App" />
  </ItemGroup>
  <ItemGroup>
    <!-- Application only — never Infrastructure or Domain -->
    <ProjectReference Include="..\MediHub.Modules.{ModuleName}.Application\MediHub.Modules.{ModuleName}.Application.csproj" />
  </ItemGroup>
</Project>
```

### `{ModuleName}Endpoints.cs`
```csharp
using MediatR;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Routing;
using MediHub.Modules.{ModuleName}.Application.Create{EntityName};
using MediHub.Modules.{ModuleName}.Application.Get{ModuleName};
using MediHub.Modules.{ModuleName}.Application.Permissions;

namespace MediHub.Modules.{ModuleName}.Presentation;

public static class {ModuleName}Endpoints
{
    public static IEndpointRouteBuilder Map{ModuleName}Endpoints(this IEndpointRouteBuilder app)
    {
        var group = app.MapGroup("/api/{moduleName_lower}")
            .WithTags("{ModuleName}")
            .RequireAuthorization();                                    // baseline: authenticated, tenant resolved

        group.MapPost("/", async (Create{EntityName}Request request, ISender sender) =>
        {
            var result = await sender.Send(new Create{EntityName}Command(request.Name, request.DepartmentId));
            return result.IsSuccess
                ? Results.Created($"/api/{moduleName_lower}/{result.Value.Id}", result.Value)
                : Results.BadRequest(result.Error);
        })
        .RequireAuthorization({ModuleName}Permissions.{EntityName}sManage)
        .WithSummary("Create a {EntityName}");

        group.MapGet("/", async (int? page, int? pageSize, ISender sender) =>
        {
            var result = await sender.Send(new Get{ModuleName}Query(page ?? 1, pageSize ?? 50));
            return result.IsSuccess ? Results.Ok(result.Value) : Results.BadRequest(result.Error);
        })
        .RequireAuthorization({ModuleName}Permissions.{EntityName}sRead)
        .WithSummary("List the {EntityName}s the current user may see");

        return app;
    }
}

public sealed record Create{EntityName}Request(string Name, Guid DepartmentId);
```

### `AssemblyReference.cs`
```csharp
namespace MediHub.Modules.{ModuleName}.Presentation;
public sealed class AssemblyReference;
```
