# Hospital Management System — Project Intent

> **Living document.** This intent is deliberately high level and is refined as
> discovery proceeds. Each section carries a status marker indicating how far it
> has settled. See [README.md](README.md) for how this document evolves.

## 1. Purpose

_Status: settled_

This project is an enterprise-level **Hospital Management System (HMS)** built primarily as a hands-on environment for practicing and evaluating **AI-Driven Development Lifecycle (AI-DLC)** practices.

The objective is not only to build a feature-rich hospital platform, but also to explore how AI-assisted and agentic engineering can support the complete software development lifecycle in a controlled, secure, traceable, and repeatable way.

The project should be treated as two parallel initiatives:

1. **Hospital Platform** — the healthcare system being designed and implemented.
2. **AI-DLC Engineering System** — the processes, agent harnesses, skills, policies, tooling, security controls, and quality gates used to build the platform.

---

## 2. Primary Objectives

_Status: emerging_

The project should provide a realistic environment to practice:

- Requirement elicitation using AI.
- Requirement clarification and gap identification.
- Requirement documentation and traceability.
- Converting requirements into structured GitHub issues.
- Architecture and design using AI-assisted workflows.
- Agentic software development.
- Skill-based and harness-based coding agents.
- Secure software development.
- DevSecOps and SecOps.
- Automated testing and verification.
- UI/UX design and implementation.
- Healthcare interoperability.
- Government healthcare integration.
- Documentation generation and maintenance.
- Architecture Decision Records (ADRs).
- Threat modeling.
- Observability and operational readiness.
- AI-generated code evaluation.
- Human approval and governance around AI-generated changes.

The system should eventually represent the complexity expected from a real enterprise healthcare platform rather than a simple CRUD application.

---

## 3. Context

_Status: emerging_

The product is a **hospital group management system** for a private healthcare provider in Sweden: one legal entity (one care provider under Swedish law) operating several hospitals. Each hospital is a tenant with its own database; hospital-group functions that need aggregated information are still to be discovered. Sweden is the first and, for now, only country supported; an EU-wide product is the long-term direction.

Patient data is governed by GDPR and the Swedish Patient Data Act (PDL). The platform models the group, its hospitals and their care units. Each hospital keeps its own patient records; with the patient's consent, a hospital can request a patient's information from another hospital of the group through a group-level patient index. Patient information is shared with national services such as the National Patient Overview (NPÖ) and the National Medication List. The platform deliberately does not support every organisational form — for example several care providers in one deployment.

---

## 4. Platform Scope

_Status: emerging_

In scope over time: patient administration, outpatient scheduling, EMR, clinical documentation, orders and results, medication and pharmacy, emergency department, theatre, billing, claims, patient portal, management reporting.

Laboratory and radiology are planned for a later phase.

---

## 5. First Slice

_Status: settled_

The first slice is something a user can feel rather than an architecture proof: **a receptionist checks in a walk-in patient with a personnummer at an outpatient clinic, and the patient appears on the clinic's waiting list.** Patient details come from a stubbed population register using official test identities. Patients with protected personal data are stopped and handled manually. Funding and fees are not part of the slice. The slice runs on test identities only; serving real patients in production is outside it.

Later slices follow the agreed order: hard cases at the same desk, ED arrival, ambulance pre-registration, booked check-in, self check-in.