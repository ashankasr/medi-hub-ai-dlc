---
name: dotnet-backend-modular-monolith-presentation-endpoints
description: Use this skill when the user asks to "add an endpoint", "add a route", "add an API endpoint", "expose via HTTP", "add a controller", "map a request", "add a GET/POST/PUT/DELETE endpoint", "register endpoints", "protect an endpoint with a permission", or asks how the Presentation layer and Minimal API work in the MediHub backend.
---

# Presentation Layer: Minimal API Endpoints

This skill guides adding HTTP endpoints to a module's `Presentation` project using Minimal APIs, with
**permission-based authorization on every endpoint**.

Load `references/endpoints-patterns.md` for the complete guide covering:

1. **Endpoint file structure**: a static class with an `IEndpointRouteBuilder` extension
2. **Authorization**: baseline `RequireAuthorization()` per group plus a permission per endpoint
3. **Request records**: co-located with the endpoints
4. **Result → IResult mapping**: 200/201/204/400/404/409
5. **Route grouping and OpenAPI metadata**: Scalar and the orval client both depend on it
6. **Registering endpoints** in the API host
7. **Project dependencies**: Application only

Cross-cutting rules (tenant from the token, permissions, field visibility) are in
`.claude/skills/dotnet-backend-modular-monolith-eventdriven-architecture/references/medihub-platform-conventions.md` (§2, §5).

## How to use

1. Load `references/endpoints-patterns.md`.
2. Identify the operation: command (POST/PUT/DELETE) or query (GET).
3. Identify the **permission** it requires. If the module has no suitable permission, add one to `<Module>Permissions` (CQRS skill §11). If the requirement doesn't say who may call it, ask.
4. Add the request record and endpoint in the module's `<Module>Endpoints.cs`.
5. For a new module, wire it into `WebApplicationExtensions.cs`.

Examples (Inventory, Orders) are **illustrative**, not MediHub modules.
