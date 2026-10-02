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
