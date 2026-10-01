# ADR-0003: Backend patterns: CQRS, outbox, choreography and sagas

- **Status:** Accepted
- **Date:** 2026-10-01
- **Deciders:** Project owner
- **Serves:** Intent §2 (skill-based and harness-based coding agents); architecture §2.2, §3.1

## Context

Most backend code will be written by coding agents guided by skills. That only
works if every module is built the same way: the same layers, the same request
pipeline and the same way of publishing events. A saved change and the event
announcing it must never drift apart, because other modules act on that event.

## Decision

The patterns are defined by the backend skills in
`.claude/skills/dotnet-backend-modular-monolith-*` and summarised here.

- **Module structure:** five projects per module: Domain, Application,
  Infrastructure, IntegrationEvents, Presentation. Dependencies point inward.
  Other modules may reference only the `IntegrationEvents` contract project.
- **Persistence:** EF Core on PostgreSQL, **one schema per module** inside each
  tenant database, migration history per schema.
- **CQRS:** **MediatR** commands and queries returning `Result<T>`, with
  pipeline behaviours for logging and validation (**FluentValidation**).
  Mapping with **Mapster**. HTTP via **Minimal APIs** in each module's
  Presentation project. MediatR's commercial licence is accepted.
- **Outbox:** domain events are saved as `OutboxMessage` rows in the same
  transaction (EF Core interceptor). A **Quartz** job dispatches them to
  domain event handlers, which publish integration events through MassTransit.
- **Workflows:** per feature, either **choreography** (consumers reacting to
  events) or **orchestration** (MassTransit state-machine sagas persisted with
  EF Core). Sagas are used when a workflow needs explicit state, timeouts or
  compensation.
- **Message content:** events, saga commands, outbox rows and saga state carry
  **identifiers, not personal data** (see ADR-0006). A consumer that needs
  details asks the owning module with **MassTransit request/response**.
- **Migrations** are applied by a dedicated `MediHub.MigrationService`; the
  API never migrates.

## Alternatives considered

- **Publishing to the broker directly after `SaveChanges`** — a crash between
  the two leaves data and events out of step.
- **Choreography only** — long clinical and billing workflows become hard to
  follow and to compensate.
- **Orchestration only** — couples simple reactions to a central coordinator.
- **Hand-rolled mediator, no CQRS library** — less dependency cost, but loses
  the shared pipeline behaviours the skills rely on.

## Consequences

**Positive**

- Uniform modules that agents can generate and reviewers can predict.
- Reliable event publication.
- Workflow style chosen per feature, not imposed globally.

**Negative / costs**

- More projects and ceremony per module than a simple layered app.
- Request/response for personal data adds latency and coupling at read time.
- Commercial licences for MediatR and MassTransit.

**Open points**

- **Outbox across tenant databases** (ADR-0004): the processor works per
  database and must cover every tenant without double delivery across API
  replicas. To prototype early and record in its own ADR.
