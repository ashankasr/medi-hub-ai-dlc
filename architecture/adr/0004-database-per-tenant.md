# ADR-0004: Database per tenant with a central catalog

- **Status:** Accepted
- **Date:** 2026-10-01
- **Deciders:** Project owner
- **Serves:** Drivers "one deployment per hospital group, multi-tenant", "database per tenant", EU/GDPR; architecture §3.2

## Context

One backend deployment serves a hospital group; each **hospital is a
tenant**. Health records are special-category data under GDPR. A leak between
hospitals is a serious incident, and hospitals may join or leave a group,
which means exporting, restoring or erasing one hospital's data on its own.

A group-level administrator governs the tenants and some central data, so a
place for data that belongs to the group rather than to one hospital is also
needed.

## Decision

- **One PostgreSQL database per tenant** (`medihub_<tenant>`), containing one
  schema per module plus the outbox and inbox tables.
- A **central tenant catalog** database holds tenants, connection
  information, encryption key references and group-level data.
- The tenant is resolved per request (ADR-0005) and travels with every hop:
  HTTP requests, MassTransit headers, background jobs, cache keys and
  database connections.
- The migration service migrates the catalog and **every** tenant database.

## Alternatives considered

- **Shared database, tenant column with row-level security** — cheapest to run,
  but one missing filter or policy exposes another hospital's patients, and
  per-hospital backup, restore or erasure is hard.
- **Schema per tenant** — collides with the schema-per-module layout
  (ADR-0003) and gives weaker isolation for backup and restore than separate
  databases.

## Consequences

**Positive**

- Strong isolation: a query cannot reach another hospital's data by accident.
- Per-hospital backup, restore, export and offboarding.
- A per-tenant data encryption key maps naturally onto a per-tenant database
  (ADR-0006).

**Negative / costs**

- Migrations, outbox processing and background jobs must loop over all tenant
  databases.
- Connection pools multiply with the number of hospitals.
- Cross-hospital features (group reporting, EMPI) cannot simply join; they
  need the catalog, group-level data or messaging.
- Onboarding a hospital means provisioning a database.

**Open points**

- Multi-tenant outbox delivery without double delivery (ADR-0003).
- Scope of group-level central data (EMPI, terminology, staff directory,
  master data) → requirement grooming.
- Connection pooling strategy in production → production architecture document.
