# Discovery: Platform scope, first country and first slice

- **Date:** 2026-10-02
- **Participants:** Ashanka Randeniya, Claude
- **Intent section served:** none existed — this session proposes new sections (§3 Context, §4 Platform Scope, §5 First Slice)
- **Depth:** quick pass on scope and context; deep dive on the first slice
- **Resolves questions:** Q-001, Q-002, Q-006, Q-008 (raised and answered in this session)

## Scope

Which areas the hospital platform covers, which country comes first, how the customer's organisation
is structured with respect to Swedish regulation, and which thin slice is built first. Funding and fees
were explicitly parked. Architecture choices were out of scope.

## Decisions

- **D1.** The platform's long-run scope is: patient administration, outpatient scheduling, clinical
  documentation, orders and results, medication and pharmacy, emergency department, theatre, billing,
  claims, patient portal, management reporting.
- **D2.** ~~Laboratory and radiology are out of scope as areas, not only as integrations.~~
  *Superseded by D16.*
- **D3.** First country is **Sweden** (a real country). "I am building a solution for entire EU. That's
  the first step." For now the product is **Sweden only** — no country-variation abstraction.
- **D4.** The first slice should deliver something a user can feel, not prove the architecture: "Let's
  go and build something that user can feel rather than going through the architecture."
- **D5.** First persona and moment: **a receptionist checking in a walk-in patient.**
- **D6.** ~~The area is named clinical documentation; EMR's status open.~~ *Superseded by D15* — Claude
  had misread "Let's stick to clinical documentation"; the user later said to ignore that comment.
- **D7.** The customer is **one private healthcare provider, one legal entity**, whose hospitals are in
  different Swedish regions. One deployment therefore has **one care provider (vårdgivare)**.
- **D8.** Organisational structure (confirmed: "this structure works for me"). *Region and funding
  model removed by D20; the rest stands.*

  ```
  Deployment = 1 care provider (legal entity; PDL accountability, GDPR controller)
  └─ Hospital = tenant (own database)
      │   region:        the Swedish region it is located in
      │   funding model: region-contracted | private-pay (whole hospital)
      └─ Care unit (vårdenhet) — PDL care relationships and blocking apply here
          └─ Location (later) — reception desk, ward, room
  ```

  The care provider stays a real concept in the model with exactly one row, so a second one can be
  added later without a rewrite. The system "doesn't need to support all the possibilities".
  **Not supported:** several care providers per deployment; a region as the customer; mixed funding
  within a hospital; record sharing with other care providers (sammanhållen journalföring, NPÖ).
  *Record sharing with other care providers superseded by G22 in
  [2026-10-06](2026-10-06-groom-patient-administration.md): information is shared with NPÖ and the
  National Medication List.*
- **D9.** A hospital is either region-funded or private-pay, never both. *Parked by D20 together with
  funding (D11).*
- **D10.** Walk-in patients can arrive at many places in a hospital.
- **D11.** Funding and fees (patient fee, högkostnadsskydd, frikort, EHIC as payer) are **deferred**.
- **D12.** The *Patient Registration & Identity* epic breakdown below is accepted as the candidate map
  of the area ("Looks fine").
- **D13.** First slice: **drop-in check-in at an outpatient clinic for a patient with a personnummer**,
  using a stubbed population register, ending with the patient on the clinic's waiting list. It
  includes a **protected-identity guard**: if the register reports protected personal data, check-in
  stops and directs the receptionist to the manual routine.
- **D14.** The stubbed population register is filled with **Skatteverket's official test personnummer**,
  so no real person's number appears in development.
- **D15.** **EMR and clinical documentation are two different areas, both in scope.** (Answers Q-002.)
  Where the boundary lies is open (Q-009).
- **D16.** **Laboratory and radiology are not out of scope; they are covered in a later phase.** Orders
  and results stays in scope. (Answers Q-001; replaces D2.) This conflicts with the architecture doc's
  "imaging, lab and device integration: out of scope (Decided)" — see Q-010.
- **D17.** Order of arrival points after the drop-in clinic, as proposed by Claude and approved by the
  user (answers Q-006):
  - **S1** Drop-in check-in for a patient with a personnummer (D13)
  - **S2** Hard cases at the same desk: reserve number, proper protected-identity handling (replaces
    the S1 guard), duplicate warnings
  - **S3** ED arrival: fast minimal registration, unknown or unconscious patients, handover to triage
  - **S4** Ambulance pre-registration
  - **S5** Check-in for booked appointments (needs outpatient scheduling)
  - **S6** Self check-in at a kiosk or in the app with BankID (needs S5 and funding)
- **D18.** Staff login for version one is **username and password** (through Keycloak, ADR-0005).
  (Answers Q-008 for version one.)
- **D19.** **Treat the product as a hospital group management system.** "We don't have to worry about
  whether this is a region, hospital, or anything like that." Each hospital is served from its own
  tenant database; hospital-group functions need some **aggregated information** handled differently.
  (Answers Q-003; A1 no longer applies.) Which group functions and which data is open (Q-011).
- **D20.** Region and funding model are dropped from the structure for now. The model is:

  ```
  Hospital group = 1 care provider (one legal entity; PDL accountability, GDPR controller)
  └─ Hospital = tenant (own database)
      └─ Care unit (vårdenhet) — PDL care relationships and blocking apply here
          └─ Location (later)
  ```

  Group-level functions are yet to be discovered and must not block other work (Q-011 deferred).
- **D21.** **The stubbed population register is used in production as well, for now.** "For now Q-007
  let's keep the stubb for prod as well." (Answers Q-007 for now.) Consequences for real patients are
  open (Q-012).
- **D22.** The boundary between EMR and clinical documentation is decided **case by case when each module
  is addressed**: "Let's take them case by case when we address modules." (Q-009 deferred; A3 remains the
  working assumption until then.)

## Assumptions accepted

- **A1.** *Withdrawn by D19.* A region-contracted private hospital has a care agreement (vårdavtal) with the region it is
  located in, which sets patient fees, referral rules and reporting. Claude's domain knowledge; the user
  was unsure how the government side works. — revisit when funding is discovered (Q-003).
- **A2.** PDL as described by Claude: care provider = legal entity; access needs a care relationship
  and is logged and reviewed; patients can block information between care units of the same care
  provider; records kept at least 10 years; sharing across care providers needs consent. — revisit when
  checked against a Swedish legal source (Q-004).
- **A3.** Working boundary between the two areas: **EMR** is the patient's ongoing record that is read
  (diagnoses, allergies, current medications, history, timeline); **clinical documentation** is writing
  entries into it (visit notes, nursing notes, discharge summaries, templates, signing). Claude's
  framing, not confirmed. — revisit when either area is discovered (Q-009).

## Open questions

- **Q-001** ~~What does orders and results cover now that laboratory and radiology are out?~~ —
  answered by D16.
- **Q-002** ~~Is EMR the same thing as clinical documentation, or out of scope?~~ — answered by D15.
- **Q-003** ~~How does a private hospital relate to its region?~~ — answered by D19.
- **Q-004** Verify the PDL interpretation (A2) against a Swedish legal source. — matters because it
  shapes authorization, audit, blocking and retention requirements.
- **Q-005** Funding and fees at check-in. — deferred by the user (D11).
- **Q-006** ~~Which arrival points come after the drop-in clinic, and in which order?~~ — answered by D17.
- **Q-007** ~~When and how does the real population register replace the stub?~~ — answered for now by
  D21. Background for when it is revisited (Claude's domain knowledge, to be verified with Inera): the
  likely route is Inera's PU-tjänsten, fed from Skatteverket; connecting needs an Inera customer
  agreement, a SITHS *function* (system) certificate, HSA-ids for the care provider and care units, and
  integration through Inera's national service platform. Alternatives are SPAR (limited data for
  protected persons) and Navet (usually authorities and regions only). Sub-questions then: which route;
  behaviour when the register is unavailable; whether the stub mirrors the PU-tjänsten response shape.
- **Q-008** ~~How do staff authenticate?~~ — answered for version one by D18.
- **Q-009** Where is the boundary between EMR and clinical documentation? — matters because each module
  needs a clear owner of the data; A3 is the working assumption. *Deferred by D22: case by case per
  module.* Scenarios to use then: an allergy mentioned in a visit note; ownership of the current
  medication list (EMR vs medication and pharmacy); correcting a signed note.
- **Q-010** The architecture doc marks imaging, lab and device integration as out of scope (Decided),
  which conflicts with D16. — needs a superseding ADR before the later phase that brings lab and
  radiology in.
- **Q-012** Will production hold **real patients** while the stub is in use (D21)? — if yes, real
  personnummer will not be in the stub, so check-in needs manual entry (C2), and protected identity
  cannot be detected from the register, which is **safety-relevant**. If production holds only test
  identities, D21 has no such impact. *Deferred by the user: "we don't really need to worry about it yet."*
- **Q-011** Which group-level functions need aggregated information across hospitals, and what data do
  they aggregate (counts only, or identifiable patients)? — decides what lives centrally vs in tenant
  databases, and how PDL applies. *Deferred by the user (D20).*

## Candidate requirements

**Epic: Patient Registration & Identity** — every patient who arrives is identified correctly,
registered once, and checked in to the right care unit, in line with PDL. (D12)

- **C1. Patient identification & lookup** — search by personnummer (checksum validated); by
  samordningsnummer; fallback by name and date of birth; possible matches within the hospital;
  population-register lookup (stub first).
- **C2. Patient record creation & maintenance** — create from register data; create from manual entry;
  patient-provided contact details separate from registered address; next of kin, emergency contacts,
  guardians for minors; language and interpreter need; deceased status.
- **C3. Patients without a Swedish ID** — reserve number; foreign visitors (passport, EHIC identity
  only); asylum seekers (LMA card); unknown or unconscious patients; later linking to a real
  personnummer.
- **C4. Protected identity & privacy** — protected personal data handling; PDL access logging of every
  read; patient blocking between care units (may belong to a records epic).
- **C5. Arrival & check-in** — walk-in at drop-in or outpatient clinic; booked appointment check-in;
  ED arrival with minimal data; ambulance pre-registration; self check-in (kiosk, app, BankID);
  waiting list per care unit; labels and wristbands; cancel check-in.
- **C6. Identity data quality** — duplicate detection, merge and unmerge; personnummer changes;
  refresh from the population register; history of demographic changes.
- **C7. Cross-hospital recognition (EMPI)** — recognise a patient known at another hospital of the
  same care provider, respecting blocking; group-level patient index.

**First slice (D13)** — candidate acceptance points:

- A personnummer with an invalid checksum is rejected before lookup — verified by test with invalid
  test numbers — traces to D13.
- A patient already registered at the hospital is found and shown, not re-created — verified by a
  repeat check-in of the same test personnummer — traces to D13, C6.
- An unknown personnummer is fetched from the stub and the patient is created after receptionist
  confirmation — verified end to end with Skatteverket test data — traces to D13, D14.
- A checked-in patient appears on the selected clinic's waiting list with arrival time — verified in
  the UI — traces to D4, D5, D13.
- A test person flagged with protected personal data stops check-in and shows the manual-routine
  message; no address is displayed — verified by test, **safety-relevant, needs a human approval gate**
  — traces to D13.
- Every read of a patient registration is access-logged — verified by inspecting the audit trail —
  traces to A2, C4.

## Suggestions not adopted

- EMPI (patient registration with cross-hospital matching) as the first slice — the user chose a slice
  a user can feel; EMPI stays as C7.
- A fictional "reference country" — the user chose Sweden.
- Designing for country variation from day one — the user chose Sweden only.
- Care provider configurable per tenant (option C) — replaced by the simpler one-care-provider
  structure (D8).
- Second factor (MFA) for the version-one username and password login — mentioned by Claude, not
  confirmed.
- Principle that each clinical data item (allergy, diagnosis, medication list, note) has exactly one
  owning module, decided when the first feature needing it is discovered — proposed by Claude; the user
  chose case by case (D22) without confirming the principle.
- Adding SITHS eID staff login before the stub is replaced by the real population register —
  recommended by Claude, not adopted. Claude later corrected this: the register integration likely
  needs a SITHS *system* certificate, not staff SITHS login, so D18 does not block it.

## Intent impact

| Section | Change | Status transition | Applied? |
| --- | --- | --- | --- |
| §3 Context | New: hospital group (one care provider), Sweden first, regulatory frame, group → hospital → care unit | new -> emerging | yes |
| §4 Platform Scope | New: areas in scope, EMR and clinical documentation separate, lab and radiology in a later phase | new -> emerging | yes |
| §5 First Slice | New: drop-in check-in for a patient with a personnummer, test identities only, later-slice order | new -> settled | yes |
