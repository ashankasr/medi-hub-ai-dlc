# ADR-0007: FHIR facade, with Subscriptions for authorized partners

- **Status:** Accepted
- **Date:** 2026-10-01
- **Deciders:** Project owner
- **Serves:** Intent §2 (healthcare interoperability, government integration); driver "HL7 FHIR via a facade"; architecture §3.4

## Context

The platform must exchange data with **authorized external parties**:
government systems and other hospitals (for example, when a patient is
repatriated). HL7 FHIR is the expected exchange standard in the EU (EHDS,
national profiles). Partners need both to pull data and to be told when
something relevant changes.

The internal domain model is shaped by hospital workflows, encryption
(ADR-0006) and authorization (ADR-0009), not by FHIR resources.

## Decision

- FHIR is the **exchange format, not the internal model**.
- A dedicated **Interoperability module** maps domain ↔ FHIR on request using
  the **Firely .NET SDK**. It stores no second copy of the data.
- **Pull:** FHIR REST API under `/fhir/...`. Partners authenticate as Keycloak
  confidential clients (ADR-0005); every request is authorized (tenant,
  purpose, consent) and audited.
- **Push (webhooks):** for authorized parties only, using FHIR topic-based
  **Subscriptions** (R5 Backport IG on R4), `rest-hook` channel, **ID-only
  payloads**, triggered by domain events from RabbitMQ. The partner then pulls
  the resource with its own authorization. *(The mechanism is still
  Proposed; webhooks for authorized parties are Decided.)*
- Profiles, operations and search parameters are added as requirements need
  them. The `CapabilityStatement` publishes exactly what is supported.

## Alternatives considered

- **A FHIR server (e.g. HAPI FHIR, Firely Server, Azure Health Data Services)**
  — the initial leaning. Rejected once it was clear that a FHIR server is a
  separate deployable product holding **its own copy** of the data: it would
  need synchronising, and encryption, consent, authorization and audit would
  have to be enforced in two places.
- **FHIR as the internal domain model** — ties every module to FHIR's resource
  shapes and versions.
- **Full-payload webhooks** — would push personal data to endpoints without a
  fresh authorization check.

## Consequences

**Positive**

- One source of truth; authorization, consent, encryption and audit enforced
  once.
- No extra deployable per hospital group.
- ID-only notifications keep personal data out of webhook traffic.

**Negative / costs**

- We implement the FHIR REST surface ourselves: search parameters, paging,
  operations and conformance.
- Mapping code grows with every resource and profile supported.
- Searching encrypted fields through FHIR is limited (ADR-0006).

**Open points**

- First target country and its national profiles → discovery.
- EMPI design (IHE PIXm/PDQm, `$match`) → requirement grooming.
