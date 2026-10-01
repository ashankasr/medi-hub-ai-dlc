---
name: dotnet-backend-modular-monolith-eventdriven-cqrs-patterns
description: Use this skill when the user asks to "create a command", "create a query", "create a handler", "add a use case", "implement a feature", "add validation", "add a domain event", "add repository methods", "map with Mapster", "filter by what the user may see", "add a permission", or asks how CQRS patterns work in the MediHub backend.
---

# CQRS Patterns: Commands, Queries, Handlers, DDD

This skill guides implementation of a feature slice in the MediHub .NET 10 modular monolith.

Load `references/cqrs-patterns.md` for the complete guide covering:

1. **CQRS type hierarchy**: `ICommand`, `ICommand<T>`, `IQuery<T>` and their handlers
2. **Result/Error pattern**: `Result<T>`, `Error`, factories; no personal data in error descriptions
3. **DDD entity types**: `Entity<TKey>` vs `AuditableGuidEntity`, domain events (IDs only)
4. **Repository + Unit of Work**: module-specific UoW, **access-scope filtering inside queries**
5. **Permissions**: declaring module permissions; permission-gated response fields
6. **FluentValidation**: auto-wired through `ValidationBehavior`
7. **Mapster mapping**
8. **Domain events → outbox → integration events** (never publish from a command handler)
9. **Folder conventions**

Cross-cutting rules (tenancy, authorization, encryption, logging) are in
`.claude/skills/dotnet-backend-modular-monolith-eventdriven-architecture/references/medihub-platform-conventions.md`.

## How to use

When asked to implement a feature:
1. Read the requirement carefully. Note who may do it (permission), whose records they may see (scope), and which fields are gated or encrypted. **Ask** if the requirement doesn't say.
2. Load `references/cqrs-patterns.md`.
3. Decide: command (write) or query (read)?
4. Identify the DDD types needed.
5. Generate files following the patterns exactly.

No backend code exists yet. The Inventory and Orders code in the reference is **illustrative**, not
MediHub modules.
