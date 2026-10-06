# MediHub — Hospital Management System (AI-DLC practice repo)

This repo has two parallel goals (intent §1): build an enterprise **Hospital Platform**, and practise
the **AI-DLC Engineering System** used to build it (elicitation, traceability, ADRs, skills, agentic
coding, governance). The process is part of the deliverable, so follow the conventions below exactly.

**Current state:** documentation only. No code is bootstrapped yet. The repository layout in
`architecture/high-level-architecture.md` §4 is a proposal.

## Where things live

| Path | What it is |
| --- | --- |
| `intent/intent.md` | Traceability root. Sections carry `exploratory` / `emerging` / `settled`. |
| `intent/README.md` | Status meanings and the `intent:` commit convention. Read before touching intent. |
| `discovery/sessions/` | One record per discovery session (`YYYY-MM-DD-<slug>.md`), decisions `D#`. |
| `discovery/questions.md` | Open questions register (`Q-###`, ids never reused). |
| `discovery/glossary.md` | Domain terms, including Swedish ones (personnummer, vårdenhet, PDL…). |
| `architecture/high-level-architecture.md` | Stack and dev environment. Items marked **Decided** or **Proposed**. |
| `architecture/adr/` | ADR-0001…0010 plus index and template. Accepted ADRs are never rewritten; supersede them. |
| `.claude/skills/` | `discovery`, `sync-epics` (keeps Epics in step with the repo) and eight `dotnet-backend-modular-monolith-*` skills. Use them. |
| `.github/ISSUE_TEMPLATE/` | Epic → Capability → Feature → User Story → Task (implementation/security/test/docs). |

## Working rules

- **The user decides; Claude asks.** Never record a requirement or decision the user did not state or
  confirm. Domain knowledge is offered as a suggestion, clearly labelled.
- **Intent stays high level.** Gaps in `intent/intent.md` become discovery questions, not new documents.
  Propose intent edits; apply only the ones the user approves.
- **Proposed ≠ Decided.** Don't build on a Proposed architecture item as if it were settled; a change to
  a Decided item needs a new ADR that supersedes the old one.
- Issues may only be derived from intent sections at the right status: `emerging` → Epics only,
  `settled` → everything below.

## Context in one paragraph

Hospital group system for one private care provider in **Sweden** (first and only country for now;
EU is the long-run direction). One deployment per hospital group; **tenant = hospital**, **database
per tenant** plus a central catalog. GDPR and Swedish PDL apply. Each hospital keeps its own patient records; with the patient's consent, a hospital can
request a patient's information from another hospital of the group through a group-level patient index (no central
copy), and patient information is shared with national services (NPÖ, National Medication List). First slice (intent §5): a receptionist
checks in a walk-in patient with a personnummer at an outpatient clinic, against a stubbed population
register filled with Skatteverket test identities; protected identities stop check-in.

## Stack (all Decided — see ADRs for why)

- Monorepo: **Nx + npm workspaces** (not pnpm). .NET `.slnx`, Central Package Management, `global.json`.
- Backend: **.NET 10 modular monolith**, Aspire, MassTransit over RabbitMQ, EF Core + Postgres (one
  schema per module per tenant DB), MediatR CQRS returning `Result<T>`, FluentValidation, Mapster,
  Minimal APIs, outbox with Quartz, dedicated `MediHub.MigrationService` (the API never migrates).
- Modules have 5 projects (Domain, Application, Infrastructure, IntegrationEvents, Presentation) and talk
  **only via integration events / saga commands**; other modules may reference only `IntegrationEvents`.
- Web: Next.js (App Router) + shadcn/ui + Tailwind + TanStack Query, orval-generated client, Auth.js BFF.
  Mobile/iPad: React Native (Expo) + NativeWind, no offline mode.
- Identity: Keycloak (Organizations = hospitals, AD federation); tenant comes **from the token only**.
  Authorization: in-app granular permissions, hospital-configured roles, list filtering **inside the
  DB query**.
- FHIR: **facade** in an Interoperability module (Firely SDK), no FHIR server; Subscriptions for partners.

## Non-negotiables when writing code

- Personal data is **encrypted at the application level** (AES-GCM, per-tenant data key, EF Core value
  converters, blind indexes for exact lookups). Which fields — decided per requirement during grooming.
- Integration events, saga state and outbox rows carry **IDs, not personal data**; fetch details with
  MassTransit request/response.
- Logs, traces, exceptions and notifications never contain decrypted personal or clinical data.
- Tenant context must flow through HTTP, message headers, background jobs, cache keys and DB connections.
- Development and test use **synthetic data only** (test personnummer, Synthea). Never real patient data.

## Git and GitHub conventions

- Commit subjects are prefixed by area: `intent:`, `discovery:`, `architecture:` (and module/area names
  once code exists).
- `intent:` commits follow `intent/README.md`: one refinement per commit, with `Trigger:`, `Sections:`
  (with status transitions) and `Rationale:` lines.
- **No `Co-Authored-By: Claude` trailer** on commits in this repo.
- PRs are **squash-merged**. Put the real commit message (including the `intent:` subject and
  Trigger/Sections/Rationale lines) in the squash message, and cite the **squash SHA on `main`** in
  issues, not the branch SHA.
- Issue hierarchy: Epics #4–#15 map 1:1 to the intent §4 scope areas. Don't create new Epics for
  discovered work; add Capabilities under the matching Epic and link as sub-issues.
- Every new issue goes on the GitHub Project board:
  `gh project item-add 2 --owner ashankasr --url <issue-url>`.

## Known open items

Tracked in `architecture/high-level-architecture.md` §6 and `discovery/questions.md`: production
environment document, multi-tenant outbox delivery, clinical audit design, group-level central data,
lab/radiology scope conflict (Q-010), PDL interpretation (Q-004), cross-hospital consent model (Q-013), sharing
with NPÖ and the National Medication List (Q-014).
