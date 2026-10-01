# ADR-0005: Keycloak with AD federation and tenant switching

- **Status:** Accepted
- **Date:** 2026-10-01
- **Deciders:** Project owner
- **Serves:** Drivers "tenant switching", "multi-tenant"; architecture §2.5, §3.3, §3.4

## Context

Hospital staff already have accounts in their hospital's **Active
Directory**; they should not get a second password. Some staff (consultants,
on-call doctors) work in several hospitals of the same group and need to move
between them without signing in again, while only ever acting in one hospital
at a time.

External partners (government systems, other hospitals) also need
machine-to-machine access.

## Decision

- **Keycloak** is the identity provider. Staff authenticate against their
  hospital's **Active Directory**, federated through Keycloak.
- **Single realm with Keycloak Organizations**, one organization per hospital.
  The token lists the hospitals a user belongs to; the user picks the active
  one and receives a token scoped to that organization.
- The API resolves the tenant **only from the validated token claim**, never
  from a client-supplied header.
- Web uses a **backend-for-frontend** (Auth.js in Next.js), so tokens never
  reach the browser. Mobile uses **Authorization Code with PKCE**.
- External partners are **Keycloak confidential clients** using client
  credentials with `private_key_jwt`, scoped per tenant and purpose.
- Authorization (what a user may do) is **not** carried in the token; see
  ADR-0009.

## Alternatives considered

- **Realm per hospital** — strong separation, but staff in several hospitals
  would need separate sessions and identities per realm, which defeats
  tenant switching.
- **Each hospital's AD / Entra ID directly, no broker** — every client would
  have to deal with several identity providers; Keycloak gives one OIDC
  surface.
- **Tenant from a request header** — trivially spoofable.

## Consequences

**Positive**

- Single sign-on with existing hospital accounts.
- One OIDC issuer for web, mobile and partners.
- Tenant context cannot be forged by the client.

**Negative / costs**

- Keycloak is one more component to run, upgrade and secure.
- Switching hospital requires a new token; clients must clear or partition
  caches by tenant.
- Every audit event must record both user and active tenant.

**Open points**

- Local AD stand-in (OpenLDAP vs Keycloak local users) → decided at bootstrap.
- Mobile token storage and cache handling (proposed, §2.4).
