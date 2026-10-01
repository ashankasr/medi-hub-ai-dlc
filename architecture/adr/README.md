# Architecture Decision Records

Each ADR records one architectural decision: the situation that forced it, what
was decided, what else was on the table, and what we now have to live with. The
[high-level architecture](../high-level-architecture.md) says *what* the system
looks like; the ADRs say *why*.

## Rules

- **One decision per ADR.** File name: `NNNN-short-title.md`, numbered in order.
- **Accepted ADRs are not rewritten.** If a decision changes, write a new ADR
  that supersedes the old one and set the old one's status to
  `Superseded by ADR-NNNN`. Typo and link fixes are fine.
- **Status values:** `Proposed` → `Accepted` → (`Deprecated` | `Superseded by ADR-NNNN`).
  A decision marked **Proposed** in the architecture document becomes
  **Decided** there once its ADR is `Accepted`.
- **Trace back to intent.** Each ADR names the intent sections or architectural
  drivers it serves. When an ADR changes the intent, the intent commit uses
  `Trigger: ADR-NNNN` (see [`intent/README.md`](../../intent/README.md)).
- Start from [`template.md`](template.md).

## Index

| ADR | Title | Status |
| --- | --- | --- |
| [0001](0001-monorepo-nx-npm-workspaces.md) | Monorepo with Nx and npm workspaces | Accepted |
| [0002](0002-modular-monolith-aspire-masstransit-rabbitmq.md) | Modular monolith with Aspire, MassTransit and RabbitMQ | Accepted |
| [0003](0003-backend-internal-patterns.md) | Backend patterns: CQRS, outbox, choreography and sagas | Accepted |
| [0004](0004-database-per-tenant.md) | Database per tenant with a central catalog | Accepted |
| [0005](0005-keycloak-ad-federation-tenant-switching.md) | Keycloak with AD federation and tenant switching | Accepted |
| [0006](0006-application-level-encryption.md) | Application-level encryption of personal data at rest | Accepted |
| [0007](0007-fhir-facade.md) | FHIR facade, with Subscriptions for authorized partners | Accepted |
| [0008](0008-notification-providers.md) | Notification providers: Brevo for email, Firebase for push | Accepted |
| [0009](0009-in-app-granular-authorization.md) | In-app granular permissions with hospital-configured roles | Accepted |
| [0010](0010-frontends-shared-generated-api-client.md) | Next.js and React Native with a shared generated API client | Accepted |
