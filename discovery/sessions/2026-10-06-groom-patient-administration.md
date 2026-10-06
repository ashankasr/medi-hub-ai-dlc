# Grooming: Patient Administration (Epic #4), first slice S1

- **Date:** 2026-10-06
- **Participants:** Ashanka Randeniya, Claude
- **Intent section served:** §5 First Slice (`settled`, commit f6a7222); §4 Platform Scope (`emerging`) is
  the Epic's parent and is not groomed below Epic level
- **Epic:** #4 Patient Administration
- **Builds on:** [2026-10-02 platform scope and first slice](2026-10-02-platform-scope-and-first-slice.md)
  (D12 candidate map C1–C7, D13 first slice, D14 test identities, D17 slice order, D21 stub in production)
- **Resolves questions:** none

## Scope

Turn slice S1 (D13) into a Capability, Features and User Stories under Epic #4, and make the decisions
that architecture defers to grooming: which fields are encrypted (ADR-0006), which permissions exist
(ADR-0009), and what is audited. Only S1 is groomed, because §5 is the only `settled` section beneath
the Epic. C3 (patients without a Swedish ID), C6 (identity data quality) and C7 (cross-hospital
recognition) stay on the candidate map and get no issues yet.

## Decisions

**Grooming shape**

- **G1.** One Capability, *Patient Registration & Identity*, under Epic #4. Its Features are the
  C-areas from D12. Only C1, C2, C4 and C5 are created now, and each one's acceptance criteria cover
  S1 only. C3, C6 and C7 stay listed in the Capability and are created when a settled slice needs them.
- **G2.** Things S1 needs from outside patient administration (a hospital with outpatient clinics, a
  receptionist user and role) are **seed data for S1**: Keycloak realm import and tenant/catalog seed,
  with no admin UI. They become tasks under the stories that need them.
- **G3.** Issues go down to User Stories. The four tasks per story (implementation, security, test,
  documentation) are created when a story is picked up.
- **G4.** Grooming decisions are recorded here and cited from the issues.

**C1 Identification and lookup**

- **G5.** A personnummer can be **entered in several formats** (`YYYYMMDDNNNN`, `YYYYMMDD-NNNN`,
  `YYMMDD-NNNN`, `YYMMDD+NNNN`), but is **always stored and always displayed in one format:
  `YYYYMMDD-NNNN`**. The user: "if the personal number can be entered in multiple format but it is
  always saved in single format. also display in single format".
- **G6.** A **samordningsnummer** (coordination number) is recognised and stops check-in with a
  message to use the manual routine. Full support stays in C1 for a later slice.
- **G7.** A patient already registered at the hospital is shown from stored data and **not refreshed**
  from the population register in S1 (refresh belongs to C6). The protected-identity check still asks
  the register on **every** check-in.
- **G8.** A valid personnummer that is found neither at the hospital nor in the population register
  stops check-in with "Not found in the population register — follow the manual routine". Nothing is
  stored. Manual entry comes with C2 in a later slice.

**C2 Record creation**

- **G9.** A patient created from register data stores **personnummer, given names, surname and
  registered address, all encrypted** (AES-GCM, ADR-0006), with a **blind index on the personnummer**
  for exact lookup. Date of birth and sex are derived from the personnummer and not stored in clear.

**C4 Protected identity and privacy**

- **G10.** When the register reports protected personal data for a **new** patient, nothing personal
  is stored and no register details are displayed. The user: "may be personal information can be scarp
  out but cancelation information needs to tracked management perspective".
- **G11.** When the patient is **already registered** and is now protected, the record is **kept but
  hidden**. It is flagged as protected, and its name and address are never shown again. A lookup shows
  only the manual-routine message. Nothing is deleted, because records must be retained (A2, Q-004).
- **G12.** **Stopped check-ins are recorded for management** (quote under G10). Each stop record holds **care unit, time,
  reason and receptionist user id, and no patient data**. The reasons tracked are: protected
  identity (G10, G11), coordination number (G6), not found in register (G8). Invalid personnummer
  input is not tracked. Reporting on these records belongs to Epic #15 Management Reporting.
- **G13.** Access logging in S1 covers **patient record views**: the lookup result and the register
  data shown for confirmation. Waiting-list views are not logged per patient. This narrows the
  2026-10-02 candidate point "every read of a patient registration is access-logged".

**C5 Arrival and check-in**

- **G14.** The receptionist **picks the clinic** from the hospital's outpatient clinics, and the choice
  is remembered per user. A patient already waiting at that clinic **cannot be checked in there again**.
- **G15.** The clinic's waiting list shows **name, personnummer (`YYYYMMDD-NNNN`), arrival time and
  waiting time**, ordered by arrival, for today's arrivals only.
- **G16.** The receptionist can **remove** a patient from the waiting list and **must pick a reason**:
  *called in* or *left without being seen*. The reason is stored on the check-in. Removals are not
  stop records (G12).

**Authorization**

- **G17.** S1 uses **one coarse permission, `reception.checkin`**, covering everything in the slice.
  It is split later when another role needs only part of it. A seeded *Receptionist* role holds it (G2).

## Assumptions accepted

None new. A2 (PDL interpretation) still stands and underlies G11 and G13.

## Open questions

None new. Related open items: Q-004 (PDL interpretation) affects G11 and G13. Q-012 (real patients
while the stub is in production) affects G8 and the protected-identity guard.

## Candidate requirements

**Capability: Patient Registration & Identity** (Epic #4; G1). Every patient who arrives is
identified correctly, registered once, and checked in to the right care unit, in line with PDL.
Features C1–C7 as in D12. Created now: C1, C2, C4 and C5, scoped to S1.

### Feature C1 — Patient identification & lookup

- **US-1 Enter and validate a personnummer.** As a receptionist, I want the personnummer I type to be
  checked and normalised before anything is looked up, so that typos never reach the register or
  create the wrong patient.
  - The four input formats in G5 are accepted and normalised to `YYYYMMDD-NNNN`. For `YYMMDD`, `-`
    means under 100 years old and `+` means 100 or older. *(Century rule: Claude's domain knowledge.)*
  - Invalid format or checksum is rejected with a message **before any lookup**, as verified with
    invalid test numbers.
  - A samordningsnummer is recognised, check-in stops with the manual-routine message, and a stop is
    recorded (G6, G12).
  - Everywhere in S1, a personnummer is displayed only as `YYYYMMDD-NNNN`.
- **US-2 Find a patient already registered at the hospital.** As a receptionist, I want a returning
  patient to be found by personnummer, so that they are registered only once.
  - Exact match through the blind index, within the current hospital only (tenant from token).
  - A found patient is shown (name, personnummer) and not re-created. A repeat check-in of the same
    test personnummer leaves one patient.
  - Stored data is shown without a register refresh (G7).
  - The view is access-logged (G13).
- **US-3 Look up an unknown personnummer in the population register.** As a receptionist, I want a
  patient who is new to the hospital to be fetched from the population register, so that I don't type
  their details.
  - The register is asked only when the patient is not found at the hospital.
  - The register is the stub, seeded with Skatteverket test personnummer (D14). Some of them are
    marked protected, as synthetic data for testing the guard.
  - The register data is shown for confirmation, and that view is access-logged (G13).
  - Not found in the register: check-in stops with the manual-routine message, nothing is stored, and
    a stop is recorded (G8, G12).

### Feature C2 — Patient record creation & maintenance

- **US-4 Create a patient from register data.** As a receptionist, I want to confirm the register data
  and create the patient, so that the hospital has a correct record from the start.
  - No patient is created without the receptionist's confirmation. Cancelling stores nothing.
  - The stored fields and their encryption follow G9, and the personnummer is stored as `YYYYMMDD-NNNN`.
  - Verified end to end with Skatteverket test data.

### Feature C4 — Protected identity & privacy

- **US-5 Stop check-in for a patient with protected personal data.** ⚠ **Safety-relevant: needs a human
  approval gate.** As a receptionist, I want check-in to stop when a patient's identity is protected, so
  that their name and whereabouts are not exposed by the system.
  - The register check runs on every check-in, for new and existing patients (G7).
  - New patient: nothing personal is stored, no register details are displayed, and the manual-routine
    message is shown (G10).
  - Existing patient: the record is flagged as protected, and its name and address are never shown again
    in lookups or on the waiting list (G11).
  - A stop is recorded without patient data (G12).
  - Verified with test identities marked protected in the stub.
- **US-6 Access-log patient record views.** As the care provider, I want every view of a patient record
  logged, so that access can be reviewed as PDL requires (A2).
  - Lookup results and register-confirmation views are logged with who, when, which patient (by id)
    and which care unit, through the platform audit (G13).
  - Waiting-list views are not logged per patient.
  - Application logs and traces contain no decrypted personal data.
  - Verified by inspecting the audit trail.

### Feature C5 — Arrival & check-in

- **US-7 Check in a walk-in patient to an outpatient clinic.** As a receptionist, I want to check in
  the identified patient to a clinic, so that the clinic knows they have arrived.
  - The receptionist picks a clinic from the hospital's seeded outpatient clinics, and the choice is
    remembered per user (G14).
  - The check-in records the patient, the clinic and the arrival time.
  - A patient already waiting at that clinic cannot be checked in there again (G14).
  - Requires `reception.checkin` (G17).
- **US-8 See and manage the clinic's waiting list.** As a receptionist, I want to see who is waiting at
  my clinic and remove patients who have been called in or left, so that the list stays accurate.
  - The list shows today's arrivals for the selected clinic: name, personnummer, arrival time and
    waiting time, ordered by arrival (G15).
  - Removing a patient requires a reason, *called in* or *left without being seen*, stored on the
    check-in (G16).
  - A removed patient disappears from the list.
  - Requires `reception.checkin` (G17).

**Seed data for S1 (G2):** one hospital tenant with at least two outpatient clinics; a receptionist user
in Keycloak; a *Receptionist* role with `reception.checkin`; the stub register filled with Skatteverket
test identities, some marked protected.

## Suggestions not adopted

- Fine-grained permissions (`patients.lookup`, `patients.register`, `checkin.create`,
  `waitinglist.view`, `waitinglist.remove`) — the user chose one coarse permission (G17).
- Logging each patient shown on the waiting list as a read — the user chose record views only (G13).
- Storing date of birth and sex in clear for sorting and statistics — the user chose to store everything
  encrypted (G9).
- Deleting an existing protected patient's name and address — the user chose keep but hide (G11).
- Tracking invalid personnummer input as a stop — not selected (G12).
- One-click removal from the waiting list without a reason — the user chose to require a reason (G16).

## Intent impact

| Section | Change | Status transition | Applied? |
| --- | --- | --- | --- |
| — | None. Grooming refines S1 inside §5 without changing it. | — | — |
