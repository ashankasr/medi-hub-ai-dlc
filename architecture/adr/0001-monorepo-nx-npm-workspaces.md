# ADR-0001: Monorepo with Nx and npm workspaces

- **Status:** Accepted
- **Date:** 2026-10-01
- **Deciders:** Project owner
- **Serves:** Intent §1 (AI-DLC engineering system), §2 (agentic development, traceability); architecture §2.1

## Context

The platform has a .NET backend, a Next.js web app and a React Native mobile
app. Web and mobile share a client generated from the backend's OpenAPI spec
and a set of design tokens, so a backend contract change ripples into both
frontends.

The project is also an AI-DLC practice environment. Coding agents work best
when one change, such as a new endpoint plus the client hooks that call it, can
be made, reviewed and verified in one place, with one set of skills and
quality gates.

## Decision

- One **monorepo** for backend, web, mobile, shared packages, infrastructure
  config, intent, discovery and architecture documents.
- **Nx** orchestrates tasks for both .NET and Node projects: `affected`
  builds and tests, caching, and module-boundary rules on the TypeScript side.
- **npm workspaces** for JavaScript packages.
- .NET integrates through the official **`@nx/dotnet`** plugin, with the
  community `@nx-dotnet/core` as fallback.
- .NET build hygiene: `.slnx` solution, `Directory.Build.props`, Central
  Package Management (`Directory.Packages.props`), SDK pinned in `global.json`.

## Alternatives considered

- **Polyrepo (backend, web, mobile separate)** — API contract changes would
  span several repositories and pull requests, and agents would lose the
  cross-stack context.
- **Turborepo** — JavaScript-only task graph; it would not orchestrate the
  .NET projects.
- **pnpm workspaces** — considered; npm workspaces chosen.

## Consequences

**Positive**

- Atomic changes across API, generated client and UIs.
- CI runs only what a change affects (`nx affected`).
- One place for skills, issue templates, quality gates and the intent trail.

**Negative / costs**

- Nx support for .NET is younger than for JavaScript; the fallback plugin may
  be needed.
- npm workspaces offer weaker isolation of hoisted dependencies than pnpm;
  phantom dependencies must be caught by linting.
- Repository size and CI setup grow with every app.

**Open points**

- Exact Nx plugin choice is confirmed when the repository is bootstrapped.
