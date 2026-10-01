# Elicitation lenses

Pick the lenses that matter for the topic at hand. These are prompts for *your* thinking about what to
ask — not a checklist to read out to the user.

## Contents

1. Stakeholder lens
2. Entity lifecycle lens
3. Workflow & unhappy-path lens
4. Non-functional lens
5. Healthcare-specific lens
6. AI-DLC lens
7. Gap-detection checklist

---

## 1. Stakeholder lens

Ask "who touches this, and what do they need from it?" for each relevant role:

- **Patients** and their carers / guardians / next of kin
- **Clinicians** — doctors (attending, resident, specialist), nurses, allied health
- **Front desk & administration** — registration, scheduling, admissions/discharge/transfer
- **Ancillary services** — pharmacy, laboratory, radiology, blood bank
- **Finance** — billing, insurance/claims, cashier
- **Hospital management** — reporting, capacity, KPIs
- **IT, security & compliance** — access control, audit, data protection officer
- **External parties** — government health authorities, insurers, referring clinics, other hospitals

Also ask who is *not* allowed to see or change something. Negative permissions are often where the real
requirements hide.

## 2. Entity lifecycle lens

For each core thing (patient record, appointment, admission, order, prescription, invoice, bed…):

- How is it created, and by whom?
- What states does it pass through? What moves it between states?
- Can it be corrected, amended, cancelled, merged (duplicate patients!), or deleted? Who may do that?
- How long must it be kept, and what happens at the end?
- Who is the source of truth if two systems disagree?

## 3. Workflow & unhappy-path lens

Walk a concrete scenario end to end, then ask what happens when:

- information is missing (unconscious patient, no ID, unknown insurer)
- something is urgent (emergency overrides normal flow — "break-glass" access)
- something fails mid-way (system down, integration unavailable, payment declined)
- two people act at once (two nurses updating the same chart, a bed double-booked)
- the process crosses a shift change, a department boundary or another organisation

## 4. Non-functional lens

Turn every vague quality word into something measurable, or into an explicit open question:

- **Security & privacy** — authentication strength, role-based vs. attribute-based access, consent
- **Auditability** — who did what, when, and why; is the audit log itself protected?
- **Availability** — what can never go down (ED, medication administration)? What's the downtime procedure?
- **Performance** — response times for the actions people do hundreds of times a day
- **Scalability** — one hospital, a group, a national network?
- **Usability & accessibility** — clinical staff under time pressure; patients with varied abilities/languages
- **Observability & operability** — how would ops know something is wrong?
- **Data residency** — where may data physically live?

## 5. Healthcare-specific lens

Offer these as domain knowledge the user can accept, reject or defer — the project's jurisdiction and
scope are deliberately still open, so don't assume one:

- **Regulatory regime** — which jurisdiction(s)? That drives privacy law (e.g. HIPAA, GDPR, national
  equivalents), retention periods and reporting duties.
- **Interoperability standards** — HL7 v2, FHIR, DICOM, coding systems (ICD, SNOMED CT, LOINC).
- **Government integration** — national patient identifiers, notifiable disease reporting, public
  insurance / claims schemes, e-prescription networks.
- **Clinical safety** — medication interactions, allergies, patient identification errors, alert fatigue.
- **Consent** — for treatment, for data sharing, for research use; minors and incapacitated patients.

## 6. AI-DLC lens

Because the project is also about practicing AI-DLC, ask for each emerging requirement:

- How would we *verify* this is met? (If there's no answer, the requirement isn't clear yet.)
- Which intent section does this trace back to?
- Is this a security- or safety-relevant requirement that will need a threat model or human approval gate?
- Is it small enough to become a Story, or is it really a Capability/Feature to be split later?

## 7. Gap-detection checklist

Listen for these in the user's answers (and in the intent itself):

| Signal | Example | Ask |
| --- | --- | --- |
| Vague qualifier | "must be fast" | Fast for which action, measured how, under what load? |
| Undefined term | "episode", "encounter", "visit" | What exactly do you mean? Are these the same thing? |
| Missing actor | "the system notifies them" | Who is "them"? Through what channel? |
| Passive voice | "the record is updated" | Updated by whom, triggered by what? |
| Universal quantifier | "all staff can see…" | Really all? Including agency staff, students, billing? |
| Happy path only | "the patient pays and leaves" | What if they can't pay, or leave before paying? |
| Hidden assumption | "like our current system" | Which system? What about it should stay, what should change? |
| Conflict | contradicts intent or a past session | Name both statements; ask which wins, and why |
| Solution in disguise | "we need a dropdown for…" | What problem is the dropdown solving? |
