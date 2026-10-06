# Grooming: Patient Administration (Epic #4), first slice S1

- **Date:** 2026-10-06
- **Participants:** Ashanka Randeniya, Claude
- **Intent section served:** §5 First Slice (`settled`, commit f6a7222); §4 Platform Scope (`emerging`) is
  the Epic's parent and is not groomed below Epic level
- **Epic:** #4 Patient Administration
- **Builds on:** [2026-10-02 platform scope and first slice](2026-10-02-platform-scope-and-first-slice.md)
  (D12 candidate map C1–C7, D13 first slice, D14 test identities, D17 slice order, D21 stub in production)
- **Resolves questions:** Q-011 partly (G20). Raises Q-013, Q-014, Q-015

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

**Review of C1 (same day)**

- **G18.** The register's **protection check runs before any patient details are shown**. This applies
  both to a returning patient's stored data (US-2) and to register data shown for confirmation (US-3).
  Without it, a protected patient's old address would be on screen before the guard fires (G11).

**Patients across the group's hospitals**

Raised while reviewing US-2, when a patient registered at one hospital walks into another. Claude
described standard practice (its domain knowledge, to verify under Q-004): within one care provider,
hospitals usually see a patient's history, under care relationship, logging and blocking; across care
providers, Sweden shares through national services such as NPÖ with the patient's consent. The user:
"I think each hospital needs to have their own record. However, if the inner same hospital group one
hospital can request information from another hospital but in that case there needs to be somewhere
central place that they can refer to information but the patient should have given certain consent to
access information from another hospital […] but also this information needs to be shared with other
like third party services such as national patient overview, national medical medication list". The
user then approved Claude's restatement ("I am approng your statements there"), including opt-in
consent, an index-only central place and the intent §3 change.

- **G19.** **Each hospital keeps its own patient record.** In S1, a patient who visits two hospitals
  of the group is registered separately at each one. Linking them is C7.
- **G20.** Within the group, a hospital **can request a patient's information from another hospital**.
  A **group-level patient index** (the "central place") records which hospitals know the patient. The
  details stay in each hospital's database and are requested from the hospital that holds them. The
  index does not hold a central copy. This partly answers Q-011.
- **G21.** Access to another hospital's information needs the **patient's consent, given in advance
  (opt-in)**. This is stricter than Claude's description of the PDL default inside one care provider,
  which is visible-unless-blocked (A2). Details are open in Q-013.
- **G22.** Patient information is **shared with national services**: the National Patient Overview
  (NPÖ) and the National Medication List. This **supersedes D8's exclusion** of record sharing with
  other care providers (sammanhållen journalföring, NPÖ). Details are open in Q-014.

**Review of C2 (same day)**

- **G23.** Creating a patient and checking them in are **two separate steps**: "Create patient" (US-4),
  then check-in (US-7).
- **G24.** The given name the patient goes by (*tilltalsnamn*) is **stored, encrypted like the other
  names**, and the **waiting list shows it with the surname**. If the register marks none, the first
  given name is used. *(Fallback: Claude's domain knowledge.)* This extends G9 and G15.
- **G25.** If two receptionists create the same patient at the same moment, the second gets **"already
  registered"**. The personnummer's blind index is unique within a hospital.
- **G26.** A patient who is created but never checked in (an **orphaned registration**) is **kept in
  S1**. Cleanup comes later in C6, as an automatic rule rather than a manual search, once Q-015 settles
  whether such a registration may be deleted. The user first asked for "another US to find [isolated]
  patient to remove from db". Claude raised PDL retention and the audit trail pointing at the patient
  id, and the user accepted the suggestion: "I will your suggestions."

## Assumptions accepted

None new. A2 (PDL interpretation) still stands and underlies G11 and G13.

## Open questions

- **Q-011** Group-level functions and data — *partly answered by G20*: a group-level patient index
  holds which hospitals know a patient, with no central copy of details. Other group-level functions
  (aggregated reporting, terminology, staff directory) are still open.
- **Q-013** How does a patient give, scope and withdraw consent for cross-hospital access (G21)? This
  covers where consent is given (desk, app, BankID), whether it applies to all hospitals or each one,
  how long it lasts, and what happens in an emergency when the patient can't consent
  (break-the-glass). It also covers how consent relates to PDL blocking. — matters because it shapes C7,
  EMR and the Access module's consent enforcement (ADR-0009).
- **Q-014** Which information is shared with NPÖ and the National Medication List, from which phase,
  and how (G22)? *Claude's domain knowledge, to verify with Inera:* both are Inera services that need
  a customer agreement and a SITHS function certificate, and they use Inera's service contracts rather
  than plain FHIR. — matters for the Interoperability module, ADR-0007 (FHIR facade) and the roadmap.

- **Q-015** Is a registration without any care contact (an orphaned registration, G26) part of the
  patient record under PDL, and how long must it be kept? — decides whether C6's cleanup rule deletes,
  anonymises or keeps it, and how the audit trail stays readable.

Related open items: Q-004 (PDL interpretation) affects G11, G13, G21 and Q-015. Q-012 (real patients while
the stub is in production) affects G8 and the protected-identity guard.

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
  - Exact match through the blind index, within the current hospital only (tenant from token). A
    patient known only at another hospital of the group is treated as new here (G19).
  - The protection check runs before any stored details are shown (G18). If the patient is protected,
    US-5 applies.
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
  - The protection check comes first (G18). If the patient is protected, US-5 applies and no register
    data is shown.
  - Otherwise the register data is shown for confirmation, and that view is access-logged (G13).
  - Not found in the register: check-in stops with the manual-routine message, nothing is stored, and
    a stop is recorded (G8, G12).

### Feature C2 — Patient record creation & maintenance

- **US-4 Create a patient from register data.** As a receptionist, I want to confirm the register data
  and create the patient, so that the hospital has a correct record from the start.
  - No patient is created without the receptionist's confirmation ("Create patient"). Cancelling
    stores nothing. Check-in is a separate step (US-7, G23).
  - Stored, all encrypted: personnummer (as `YYYYMMDD-NNNN`, with a blind index), given names, the given
    name the patient goes by, surname and registered address (G9, G24). Date of birth and sex are
    derived from the personnummer.
  - If the register marks no given name in use, the first given name is used (G24).
  - If the same patient is created at the same moment from two desks, the second gets "already
    registered" and no duplicate is created (G25).
  - A patient created but not checked in stays registered (G26).
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
  - The list shows today's arrivals for the selected clinic: the given name the patient goes by and
    surname, personnummer, arrival time and waiting time, ordered by arrival (G15, G24).
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
- Recognising a patient across the group's hospitals already in S1 — the user chose separate records
  per hospital, linked later (G19, G20).
- A central copy of patient information — the user chose an index only (G20).
- PDL's default inside one care provider (visible unless the patient blocks) — the user chose opt-in
  consent (G21).
- One step, "Create and check in" — the user chose two separate steps (G23).
- A story in S1 to find and delete orphaned registrations (the user's idea) — the user accepted Claude's
  suggestion to keep them in S1 and clean up automatically in C6 once Q-015 is answered (G26).

## Intent impact

| Section | Change | Status transition | Applied? |
| --- | --- | --- | --- |
| §5 First Slice | None. Grooming refines S1 inside §5 without changing it. | — | — |
| §3 Context | Replace "does not support … record sharing with other care providers" with per-hospital records, consent-based requests between the group's hospitals through a group-level index, and sharing with national services (NPÖ, National Medication List) (G19–G22) | emerging -> emerging | yes |
