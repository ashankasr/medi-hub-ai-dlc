---
name: dotnet-backend-modular-monolith-eventdriven-integration-events-consumers
description: Use this skill when the user asks to "add a consumer", "add an integration event", "subscribe to an event", "handle a message", "add a MassTransit consumer", "wire up a consumer", "request data from another module", "add request/response", "how do modules communicate", or asks how integration events and consumers work in the MediHub backend.
---

# Integration Events, Request/Response & Consumers

This skill guides adding integration event contracts, request/response contracts and the consumers that
handle them. It covers orchestration (saga commands), choreography (autonomous reactions) and
cross-module data requests.

Load `references/consumers-patterns.md` for the complete guide covering:

1. **Contracts**: where they live and what they may contain (**IDs only**, no personal data)
2. **Cross-module project references**
3. **Consumer anatomy**: dependencies, tenant context, logging (IDs only)
4. **Orchestration consumers**: responding to saga commands
5. **Choreography consumers**: reacting to events
6. **Compensation consumers**: undoing earlier work
7. **Request/response**: fetching details from the owning module
8. **Registration**: `ConfigureConsumers`
9. **Decision guide**: consumer vs domain event handler

Cross-cutting rules are in
`.claude/skills/dotnet-backend-modular-monolith-eventdriven-architecture/references/medihub-platform-conventions.md` (§4 Messaging).

## How to use

1. Identify the pattern: orchestration (saga command → reply), choreography (event → reaction) or request/response (needs details).
2. Load `references/consumers-patterns.md`.
3. Add the contract to the **owning** module's `IntegrationEvents` project, with IDs, codes and timestamps only.
4. Add the consumer to the reacting module's `Infrastructure/Consumers/` folder.
5. Register it in the module's `ConfigureConsumers`.

Examples (Orders, Inventory, Payments) are **illustrative**, not MediHub modules.
