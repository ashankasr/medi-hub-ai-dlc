# ADR-0010: Next.js and React Native with a shared generated API client

- **Status:** Accepted
- **Date:** 2026-10-01
- **Deciders:** Project owner
- **Serves:** Intent §2 (UI/UX design and implementation); architecture §2.3, §2.4

## Context

Staff use the system on desktops in wards and offices, and on phones and
iPads at the bedside. Both frontends call the same backend, and a hand-written
client in each would drift from the API. Tokens for health data must not be
exposed to browser JavaScript.

## Decision

- **Web:** **Next.js** (App Router), **shadcn/ui** and **Tailwind CSS**,
  **TanStack Query** for server state, **TanStack Store** only where
  client-only state is needed.
- **Web authentication:** Next.js acts as a **backend-for-frontend** with
  **Auth.js** and Keycloak, so tokens never reach the browser (ADR-0005).
- **Mobile and iPad:** **React Native** with **Expo** (development builds),
  **NativeWind** and **react-native-reusables**, OIDC Authorization Code with
  PKCE. **No offline mode.**
- **Shared API client:** generated with **orval** from the backend's OpenAPI
  document into `packages/api-client`, producing TanStack Query hooks on top
  of `fetch`; used by web and mobile. The same document feeds the **Scalar**
  API reference.
- **Shared design tokens** in `packages/ui-tokens`, used by Tailwind on web and
  NativeWind on mobile.

## Alternatives considered

- **Hand-written API clients** — drift from the backend contract and
  duplicated effort across two apps.
- **Single-page app with tokens in the browser** — exposes tokens to XSS.
- **Offline-first mobile app** — not required, and it would put health data
  on devices and add sync conflicts.
- **Separate native apps (Swift/Kotlin) or Flutter** — no code or token sharing
  with the React web app.

## Consequences

**Positive**

- One contract, regenerated on change, type-checked in both apps.
- Shared UI vocabulary across web and mobile.
- No tokens in the browser.

**Negative / costs**

- The OpenAPI document must be accurate; backend endpoint metadata becomes part
  of the contract.
- The BFF means Next.js proxies API traffic and needs to run as a server.
- Mobile depends on network connectivity at all times.

**Open points**

- Mobile token storage and persistence of the query cache (proposed: secure
  storage, cache never persisted) → confirm at bootstrap.
