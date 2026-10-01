---
name: dotnet-backend-modular-monolith-eventdriven-saga
description: Use this skill when the user asks to "add a saga", "add a saga step", "extend a saga", "add a new state", "add compensation", "add a saga transition", "how does the saga work", "add a new saga event", or asks how the MassTransit state machine orchestration pattern works in the MediHub backend.
---

# Saga Orchestration: MassTransit State Machine

This skill guides creating, extending and understanding MassTransit `MassTransitStateMachine<TState>`
sagas for orchestrated multi-module workflows in MediHub.

Load `references/saga-patterns.md` for the complete guide covering:

1. **Saga anatomy**: `MassTransitStateMachine<TState>`, `State`, `Event`, `InstanceState`, correlation
2. **State machine DSL**: `Initially`, `During`, `When`, `Then`, `PublishAsync`, `TransitionTo`, `Finalize`
3. **Saga state**: what to store (**IDs and status only**, no personal data)
4. **Adding a step**: a new state, event, transition and compensation
5. **Compensation**: undoing previous steps on failure
6. **Persistence**: EF Core in the owning module's schema of the **tenant database**, Postgres optimistic concurrency
7. **Correlation and tenancy**: how messages find their instance; how the tenant flows

## How to use

1. **No saga exists in MediHub yet.** `OrderSaga` in the reference is **illustrative**. A new saga lives in the owning module's `Application/Saga/` folder.
2. Load `references/saga-patterns.md`.
3. Identify the task: a new saga, a new happy-path step, a new failure path, or compensation.
4. Add `State` and `Event` properties and correlation, then wire `During(...).When(...).Then(...).PublishAsync(...).TransitionTo(...)`.
5. Add state properties (IDs, status, reason codes only) and a migration for the saga state table.
6. Add contracts to the relevant `IntegrationEvents` projects and consumers in target modules (see the integration-events-consumers skill).

Choose a saga only when several modules must succeed or be compensated together. Independent reactions
use choreography.
