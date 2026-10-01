---
name: dotnet-backend-modular-monolith-eventdriven-implement-feature
description: Use this skill when the user asks to "implement a feature end-to-end", "build a full pipeline", "add a new endpoint with everything wired up", "implement X from API to domain", "scaffold the full stack for X", or when a request clearly requires touching multiple layers (Presentation → Application → Domain → Infrastructure → Integration Events) of the MediHub backend. This skill orchestrates the other specialist skills in the correct order.
---

# Full-Pipeline Feature Implementation

This skill guides end-to-end delivery of a feature in the MediHub .NET 10 modular monolith, from
brainstorm through every layer to a working, permission-protected, tenant-aware HTTP endpoint.

Load `references/feature-pipeline.md` for the complete guide covering:

1. **Phase 1, Brainstorm**: questions to answer before writing code, including **who may do it, whose records they may see, which fields are gated or encrypted**
2. **Phase 2, Pipeline design**: a decision matrix for layers and patterns (domain event, integration event, request/response, saga, permission, migration)
3. **Phase 3, Implementation order**
4. **Phase 4, Layer-by-layer implementation**, with pointers to the specialist skills
5. **Phase 5, Verification checklist**

Cross-cutting rules: `.claude/skills/dotnet-backend-modular-monolith-eventdriven-architecture/references/medihub-platform-conventions.md`.

## How to use

1. Read the feature requirement. It should trace to a groomed requirement (Epic → Feature → Story). If it doesn't, ask.
2. Load `references/feature-pipeline.md`.
3. Work through Phase 1 and write the answers down **before generating any code**. Share the analysis with the user and confirm it. Anything the requirement leaves open (permission, scope, gated or encrypted fields) is a question for the user, not a guess.
4. Use the Phase 2 matrix to decide which layers are needed.
5. Implement in the Phase 3 order, using the specialist skills.
6. Confirm every Phase 5 item.

**Critical rule:** never skip the brainstorm. Code written before the design is clear produces layers that don't connect.

**Blocked work:** if the feature needs outbox delivery across tenants (deferred) or clinical audit (pending
a separate discussion), say so and stop at that boundary rather than inventing a design.
