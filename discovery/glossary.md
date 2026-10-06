# Glossary

Domain terms as used in this project. Swedish terms are kept where they have no exact English
equivalent.

| Term | Meaning | Source |
| --- | --- | --- |
| Hospital group | The customer: one private healthcare provider operating several hospitals. One per deployment. | D19, D20 |
| Care provider (*vårdgivare*) | The legal entity that runs healthcare and is accountable under PDL; GDPR data controller. The hospital group is one care provider. | [2026-10-02](sessions/2026-10-02-platform-scope-and-first-slice.md) D7, D8 |
| Hospital | A hospital of the group; one tenant with its own database. | D8, D20 |
| Care unit (*vårdenhet*) | A clinic or department within a hospital (e.g. ED, outpatient clinic). The level where PDL care relationships and blocking apply. | D8 |
| PDL (*Patientdatalagen*) | Swedish Patient Data Act (SFS 2008:355), governing patient records and access to them. Interpretation pending verification (Q-004). | session |
| Personnummer | Swedish personal identity number. | session |
| Samordningsnummer | Coordination number for people without a personnummer. | session |
| Reserve number (*reservnummer*) | Temporary local identity for a patient whose identity is unknown or who has no Swedish number. | session |
| Protected personal data (*skyddade personuppgifter*) | Population-register marking for people whose details, especially address, must not be disclosed. | D13 |
| Test personnummer | Personnummer published by Skatteverket for testing; used in the stubbed register. | D14 |
| Walk-in | A patient who arrives without an appointment. | D5, D10 |
| Group-level patient index (EMPI) | Central index of which hospitals of the group know a patient. Holds no copy of patient details; a hospital requests details from the hospital that holds them. | G20 |
| Consent (*samtycke*) | In this project, the patient's advance permission for one hospital of the group to access information held by another. Details open (Q-013). | G21 |
| NPÖ (*Nationell patientöversikt*) | National Patient Overview: national service through which care providers can read each other's records with the patient's consent. | G22 |
| National Medication List (*Nationella läkemedelslistan*) | National register of a patient's prescribed and dispensed medicines, shared across care providers. | G22 |
| Tilltalsnamn | The given name a person goes by, marked in the population register among their given names. Shown on the waiting list. | G24 |
| Orphaned registration | A patient created at a hospital but never checked in. Kept in S1; cleanup rule open (Q-015). | G26 |
