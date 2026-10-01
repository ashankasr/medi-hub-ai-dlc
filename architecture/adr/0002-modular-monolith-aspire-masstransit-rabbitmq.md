# ADR-0002: Modular monolith with Aspire, MassTransit and RabbitMQ

- **Status:** Accepted
- **Date:** 2026-10-01
- **Deciders:** Project owner
- **Serves:** Driver "one backend deployment per hospital group"; architecture §2.2, §3.1

## Context

A hospital management system has many bounded contexts (patients,
admissions, clinical care, pharmacy, billing and more) that must evolve
independently. The product is **not SaaS**: each hospital group runs its own
backend deployment. Every additional deployable therefore multiplies the
operational burden for every customer.

Modules must still be decoupled enough that a boundary mistake does not turn
into a big ball of mud, and long-running cross-module workflows (for example
admission → bed allocation → billing) need durable, asynchronous messaging.

## Decision

- The backend is a **modular monolith**: one host (`MediHub.Api`) composes all
  modules. Each module owns its data and exposes no internals.
- Modules communicate **only through integration events and saga commands**
  over a message broker. No direct calls, no shared DbContexts.
- **MassTransit** is the messaging library. Its commercial licence is accepted.
- **RabbitMQ** is the broker in every environment, including production.
- **.NET Aspire** provides local orchestration (AppHost) and shared service
  defaults (OpenTelemetry, health checks, resilience).
- Production hosting of RabbitMQ is an **Azure Container App**; persistence and
  clustering are designed in the production architecture document.

## Alternatives considered

- **Microservices** — independent deployability is not worth the cost when
  every hospital group operates its own installation; the monolith keeps one
  deployable while preserving the boundaries needed to extract a module later.
- **Layered monolith with in-process calls between modules** — cheap at first,
  but boundaries erode and there is no durable path for cross-module workflows.
- **Azure Service Bus in production** — considered. RabbitMQ chosen so that
  development and production run the same broker and MassTransit transport.
- **CloudAMQP (managed RabbitMQ)** for production — considered; a Container App
  chosen instead.

## Consequences

**Positive**

- One deployable per hospital group; simple to operate and upgrade.
- Hard module boundaries enforced by messaging, ready for later extraction.
- Identical broker semantics locally and in production.

**Negative / costs**

- The broker is critical infrastructure even though modules share a process.
- Azure has no managed RabbitMQ, so we own its availability, persistence and
  upgrades in production.
- Eventual consistency between modules must be designed for in every feature.
- MassTransit licence cost.

**Open points**

- RabbitMQ persistence, clustering and backup on Container Apps → production
  architecture document.
- Architecture tests enforcing module boundaries (proposed, §3.1).
