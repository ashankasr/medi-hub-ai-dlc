# ADR-0009: In-app granular permissions with hospital-configured roles

- **Status:** Accepted
- **Date:** 2026-10-01
- **Deciders:** Project owner
- **Serves:** Driver "authorization beyond roles"; architecture §2.5, §3.1 (Access module)

## Context

Hospitals organise their staff differently, so fixed roles shipped with the
product will not fit. A hospital administrator must be able to define what a
"Ward Nurse" or "Pharmacist" may do, assign it to staff, and narrow it to a
ward or department, with the change taking effect **immediately**, without a
release or a re-login.

Clinical access also depends on context that only the domain knows: the
care relationship, consent, break-the-glass. Lists must show only what a user
may see, and the same endpoint may show more fields to some users than others.

## Decision

- **Granular permissions** declared in code by each module form a permission
  catalog.
- A **hospital administrator** bundles permissions into **roles** at runtime
  and assigns them to staff **in their own hospital only**, optionally scoped to
  a **ward or department**. No second approval.
- Roles and assignments are stored **per tenant** in the **Access module**.
- Checks run **server-side** and are cached; permissions are **not** carried in
  the token. Contextual rules (care relationship, consent, break-the-glass)
  are code in the Access module.
- **List filtering** is applied inside the database query, so paging and
  counts stay correct; never by trimming results in memory.
- **Field-level visibility:** extra fields are gated by permissions and
  omitted for users without them.
- **No external policy engine.**

## Alternatives considered

- **Roles or permissions in the Keycloak token** — stale until the token is
  refreshed (breaks "immediately"), bloats tokens, and is awkward to scope per
  tenant and ward.
- **External policy engine (e.g. OPA, OpenFGA, Cerbos)** — another component
  to run per hospital group, and contextual clinical rules need domain data
  that would have to be synchronised into it.
- **Fixed, product-defined roles** — does not fit how different hospitals
  organise their staff.

## Consequences

**Positive**

- Hospitals configure access themselves; changes are effective at once.
- Rules live next to the domain data they depend on.
- Correct paging and counts with filtered lists.

**Negative / costs**

- We build and maintain the authorization model, admin UI and caching
  ourselves.
- Cache invalidation on role and assignment changes must be reliable.
- Every query that lists records needs a filter expression; this needs a
  shared mechanism and tests, not per-handler discipline.

**Open points**

- Which fields or data categories (e.g. mental health, HIV status) are gated →
  requirement grooming.
- Consent model and break-the-glass workflow → requirement grooming.
