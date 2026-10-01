# Presentation Layer: Minimal API Endpoints: Complete Reference

Module names (Inventory, Orders) are **illustrative**, not MediHub modules.
Cross-cutting rules: `../../dotnet-backend-modular-monolith-eventdriven-architecture/references/medihub-platform-conventions.md`.

---

## 1. File Structure

```
src/Modules/<Name>/MediHub.Modules.<Name>.Presentation/
  <Module>Endpoints.cs     ← all routes for the module + request records
  Tags.cs                  ← OpenAPI tag constants
  AssemblyReference.cs
```

---

## 2. Endpoint File Skeleton

```csharp
using MediatR;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Routing;
using MediHub.Modules.Inventory.Application.Permissions;
using MediHub.Modules.Inventory.Application.Products.CreateProduct;
using MediHub.Modules.Inventory.Application.Products.GetProducts;

namespace MediHub.Modules.Inventory.Presentation;

public static class InventoryEndpoints
{
    public static IEndpointRouteBuilder MapInventoryEndpoints(this IEndpointRouteBuilder app)
    {
        var group = app.MapGroup("/api/inventory")
            .WithTags(Tags.Inventory)
            .RequireAuthorization();                         // baseline: authenticated user, tenant resolved from the token

        // GET — list, filtered to what the user may see (inside the query)
        group.MapGet("/products", async (int? page, int? pageSize, ISender sender) =>
        {
            var result = await sender.Send(new GetProductsQuery(page ?? 1, pageSize ?? 50));
            return result.IsSuccess ? Results.Ok(result.Value) : Results.BadRequest(result.Error);
        })
        .RequireAuthorization(InventoryPermissions.ProductsRead)
        .WithSummary("List the products the current user may see");

        // POST — command, returns Created with location
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

        return app;
    }
}

// Request records — co-located at the bottom of the same file
public sealed record CreateProductRequest(string Name, string Sku, Guid DepartmentId, int StockQuantity, decimal Price);
```

---

## 3. Authorization

| Rule | Detail |
|---|---|
| Baseline | Every route group calls `.RequireAuthorization()`. Anonymous endpoints (`.AllowAnonymous()`) are a deliberate exception and need review. |
| Permission per endpoint | `.RequireAuthorization(<Module>Permissions.X)`. The policy name **is** the permission; the Common policy provider checks it against the user's roles in the **active tenant**. |
| No role names | Never `RequireRole(...)` or hard-coded role names. Hospital administrators define roles at runtime. |
| Tenant | Comes from the validated token through middleware. Never accept a tenant ID in the route, query string, body or headers. |
| Record scope | Not checked in the endpoint. Handlers and repositories filter by `ICurrentUser.Scope` inside the query; out-of-scope records come back as **404**. |
| Field visibility | Not handled in the endpoint. The query handler leaves permission-gated fields `null`. |

Authentication is applied by `app.UseAuthentication()` → `app.UseTenantResolution()` → `app.UseAuthorization()`
in the API host (in that order).

---

## 4. Result → IResult Mapping

Always check `result.IsSuccess`. Never throw from endpoints.

```csharp
// Query — found / not found (also "not found" when outside the user's scope)
group.MapGet("/orders/{id:guid}", async (Guid id, ISender sender) =>
{
    var result = await sender.Send(new GetOrderQuery(id));
    return result.IsSuccess ? Results.Ok(result.Value) : Results.NotFound(result.Error);
})
.RequireAuthorization(OrdersPermissions.OrdersRead)
.WithSummary("Get order by ID");

// Command with path parameter
group.MapPost("/orders/{orderId:guid}/cancel", async (Guid orderId, CancelOrderRequest request, ISender sender) =>
{
    var result = await sender.Send(new CancelOrderCommand(orderId, request.ReasonCode));
    return result.IsSuccess
        ? Results.Ok(result.Value)
        : result.Error.Type == ErrorType.NotFound ? Results.NotFound(result.Error) : Results.BadRequest(result.Error);
})
.RequireAuthorization(OrdersPermissions.OrdersCancel)
.WithSummary("Cancel order");
```

| Scenario | HTTP result |
|---|---|
| Query found | `Results.Ok(result.Value)` |
| Not found **or outside the user's scope** | `Results.NotFound(result.Error)` |
| Created a resource | `Results.Created("/path/{id}", new { Id = result.Value })` |
| Succeeded with a response | `Results.Ok(result.Value)` |
| Succeeded, no body | `Results.NoContent()` |
| `Error.Conflict` | `Results.Conflict(result.Error)` |
| Validation or domain failure | `Results.BadRequest(result.Error)` |
| Missing permission | `403`, produced by the authorization middleware (no endpoint code) |

Error bodies are `{ code, description }`. Descriptions never contain personal data.

---

## 5. Route Grouping and OpenAPI Metadata

```csharp
var group = app.MapGroup("/api/orders").WithTags(Tags.Orders).RequireAuthorization();

group.MapPost("/", ...)
    .RequireAuthorization(OrdersPermissions.OrdersCreate)
    .WithSummary("Place order")
    .WithDescription("Places an order; a saga coordinates stock and payment.");
```

```csharp
// Tags.cs
internal static class Tags
{
    internal const string Orders = "Orders";
    internal const string Inventory = "Inventory";
}
```

The OpenAPI document feeds both **Scalar** (API reference UI) and **orval**, which generates the
TanStack Query client in `packages/api-client` for web and mobile. Keep summaries accurate and response
types explicit. Permission-gated response fields are nullable, so they appear as optional in the client.
Regenerate the client after changing endpoints.

---

## 6. Request Records

```csharp
public sealed record CreateProductRequest(string Name, string Sku, Guid DepartmentId, int StockQuantity, decimal Price);

public sealed record PlaceOrderRequest(Guid CustomerId, Guid DepartmentId, List<PlaceOrderItemRequest> Items);
public sealed record PlaceOrderItemRequest(Guid ProductId, int Quantity);

public sealed record CancelOrderRequest(string ReasonCode);
```

**Rules:**
- Always `sealed record`
- Only primitives, `Guid`, `decimal`, and `List<T>` of other records; no domain objects
- Map to the command or query inside the endpoint lambda
- No tenant ID fields, ever

---

## 7. Registering Endpoints in the API Host

```csharp
// src/Api/MediHub.Api/Extensions/WebApplicationExtensions.cs
internal static class WebApplicationExtensions
{
    internal static WebApplication MapEndpoints(this WebApplication app)
    {
        app.MapInventoryEndpoints();
        app.MapOrdersEndpoints();      // ← add new modules here
        return app;
    }
}
```

The API host `.csproj` references each module's Presentation project:

```xml
<ProjectReference Include="..\..\Modules\Orders\MediHub.Modules.Orders.Presentation\MediHub.Modules.Orders.Presentation.csproj" />
```

---

## 8. Presentation Project Dependencies

```xml
<ItemGroup>
  <FrameworkReference Include="Microsoft.AspNetCore.App" />
</ItemGroup>
<ItemGroup>
  <ProjectReference Include="..\MediHub.Modules.<Name>.Application\MediHub.Modules.<Name>.Application.csproj" />
</ItemGroup>
```

- Own module's `Application` ✅ (commands, queries, permissions)
- Own module's `Domain` ❌; use Application DTOs
- Any `Infrastructure` ❌ never

---

## 9. Checklist: Adding an Endpoint

- [ ] Open the module's `<Module>Endpoints.cs`
- [ ] Route group has `.RequireAuthorization()`
- [ ] Endpoint has `.RequireAuthorization(<Module>Permissions.X)`, with a new permission added and registered if needed
- [ ] Request record (if it takes a body) at the bottom of the file, with no tenant fields
- [ ] Request mapped to the command or query; `sender.Send(...)`; check `result.IsSuccess`
- [ ] Correct `IResult` (section 4); out-of-scope records → 404
- [ ] `.WithSummary(...)` for Scalar, OpenAPI and orval
- [ ] New module: `app.Map<Module>Endpoints()` in `WebApplicationExtensions.cs` + `ProjectReference` in the API host
- [ ] orval client regenerated if the web or mobile app uses the endpoint
