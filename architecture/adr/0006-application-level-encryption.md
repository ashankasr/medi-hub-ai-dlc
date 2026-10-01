# ADR-0006: Application-level encryption of personal data at rest

- **Status:** Accepted
- **Date:** 2026-10-01
- **Deciders:** Project owner
- **Serves:** Drivers "application-level encryption", EU/GDPR; architecture §2.6, §3.5

## Context

Encrypting personal data is a must. Disk- or storage-level encryption (which
Azure Database for PostgreSQL provides anyway) protects against stolen disks,
but not against anyone who can query the database, read a backup, or see a
replicated table, queue or outbox row. Health data needs protection that
holds even when the database itself is exposed.

## Decision

- The **application** encrypts and decrypts personal data, field by field.
- **Envelope encryption:** AES-GCM with a **data key per tenant**; data keys
  are wrapped by a **master key** in Azure Key Vault (a local master key from
  developer secrets in development). Ciphertext stores the key version.
- Applied through **EF Core value converters**, behind a key-provider
  abstraction, so module code does not handle cryptography.
- **Blind indexes** (keyed hashes) support exact-match lookups on encrypted
  fields.
- Messages, outbox rows and saga state carry identifiers, not personal data
  (ADR-0003). Logs, traces and exceptions never contain decrypted values.
- **Which fields** are encrypted is decided per requirement during grooming.

## Alternatives considered

- **Storage-level encryption only (TDE / managed disk encryption)** — no
  protection against database-level access or backups.
- **Database-side encryption (pgcrypto)** — keys or plaintext pass through the
  database server and can surface in query logs and statistics.

## Consequences

**Positive**

- A database dump, backup or replica alone does not reveal personal data.
- Per-tenant keys align with database-per-tenant isolation (ADR-0004).
- One pattern for every module.

**Negative / costs**

- Encrypted columns cannot be searched with `LIKE`, `pg_trgm`, ranges or
  sorting; only exact lookups via blind indexes.
- Tension with EMPI fuzzy matching and name search: such fields need a
  deliberate decision each time.
- Key rotation requires a re-encryption process.
- CPU cost on every read and write of protected fields.

**Open points**

- The list of encrypted fields → requirement grooming, per field.
- Whether request/response payloads carrying personal data need encrypting in
  transit over RabbitMQ → production architecture document.
