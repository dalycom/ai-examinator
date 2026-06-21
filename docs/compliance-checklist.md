# Compliance Checklist — AI Examinator

- **Status:** Draft v1 (Phase 0) — readiness tracker, not legal advice.
- **Last updated:** 2026-06-20
- **Scope:** UAE healthcare requirements, UAE PDPL, HIPAA (where applicable), GDPR (where applicable).

> This is an engineering readiness checklist. Final compliance requires legal/DPO review and, where relevant,
> regulator-specific attestations (e.g. DoH/DHA/MOHAP in the UAE).

Legend: ☐ planned · ◐ in progress · ☑ done · N/A.

---

## 1. Lawful basis, consent & transparency

| # | Control | Status | Phase |
|---|---|---|---|
| C1 | Explicit, recorded consent for **audio recording** before any capture | ☐ | 3 |
| C2 | Explicit, recorded consent for **AI processing** of the consultation | ☐ | 3 |
| C3 | Consent scope, method, timestamp, granting user captured & audited | ☐ | 3 |
| C4 | Consent withdrawal workflow stops further processing | ☐ | 3 |
| C5 | Clear AI transparency: outputs labeled as suggestions requiring review | ☐ | 4 |
| C6 | Privacy notice / processing purposes documented | ☐ | 1 |

## 2. Data subject rights (PDPL / GDPR)

| # | Control | Status | Phase |
|---|---|---|---|
| C7 | Right of access / data export (machine-readable) | ☐ | 5 |
| C8 | Right to rectification (record correction + audit) | ☐ | 2 |
| C9 | Right to erasure workflow (with legal-hold/retention overrides) | ☐ | 5 |
| C10 | Audit trail of all DSAR actions | ☐ | 5 |

## 3. Security safeguards (HIPAA Security Rule / PDPL / GDPR Art.32)

| # | Control | Status | Phase |
|---|---|---|---|
| C11 | Encryption in transit (TLS/WSS) | ☐ | 1 |
| C12 | Encryption at rest (DB + object storage) | ☐ | 1 |
| C13 | Field-level protection for sensitive PHI | ☐ | 1–3 |
| C14 | Strong authentication (Argon2) + MFA readiness | ☐ | 1 |
| C15 | RBAC + ABAC least-privilege | ☐ | 1 |
| C16 | Tenant isolation (scoping + RLS) with tests | ☐ | 1 |
| C17 | Immutable, tamper-evident audit logs | ☐ | 1 |
| C18 | No PHI in logs/traces; redaction filter | ☐ | 1 |
| C19 | Signed URLs for protected files | ☐ | 2 |
| C20 | Secret management (no secrets in code) | ☐ | 1 |
| C21 | Rate limiting & abuse protection | ☐ | 1 |
| C22 | Dependency & container scanning in CI | ☐ | 1 |
| C23 | Session management (rotation, revocation, timeout) | ☐ | 1 |
| C24 | Security event monitoring & alerting | ☐ | 5–6 |

## 4. Data governance & lifecycle

| # | Control | Status | Phase |
|---|---|---|---|
| C25 | Data classification applied to all entities | ☐ | 1 |
| C26 | Retention policies (statutory periods TBC for UAE) | ☐ | 5 |
| C27 | Backup & disaster recovery with tested restore | ☐ | 6 |
| C28 | De-identification for analytics/eval/testing | ☐ | 4 |
| C29 | No real patient data in dev/demo/fixtures/tests | ☐ | 1 (policy) |
| C30 | Data residency in approved region (region TBC) | ☐ | deploy |

## 5. AI governance & safety

| # | Control | Status | Phase |
|---|---|---|---|
| C31 | Human-in-the-loop approval for all clinical AI output | ☐ | 4 |
| C32 | No autonomous diagnosis/prescribing/auto-signing | ☐ | 4 |
| C33 | Full provenance (model, prompt version, timestamp, confidence) | ☐ | 4 |
| C34 | Structured output validation before display/storage | ☐ | 4 |
| C35 | Prompt-injection & cross-patient-leak defenses | ☐ | 4 |
| C36 | AI evaluation suite with synthetic/de-identified data | ☐ | 4 |
| C37 | Feature flags for experimental AI | ☐ | 4 |
| C38 | External-AI use gated by BAA/DPA (default self-hosted) | ☐ | 4/deploy |

## 6. Vendor & third-party

| # | Control | Status | Phase |
|---|---|---|---|
| C39 | BAA/DPA in place before any external PHI processor used | ☐ | deploy |
| C40 | Sub-processor register maintained | ☐ | deploy |

## 7. Healthcare interoperability standards

| # | Control | Status | Phase |
|---|---|---|---|
| C41 | FHIR R4 compatibility layer | ☐ | 5 |
| C42 | ICD-10 coding for problems/diagnoses | ☐ | 2 |
| C43 | RxNorm (or approved regional) for medications | ☐ | 2 |
| C44 | LOINC for labs/vitals | ☐ | 2/5 |
| C45 | SNOMED CT only after licensing confirmed | ☐ | TBC |
| C46 | DICOM references for imaging | ☐ | 5 |

## Open compliance items (blocking before pilot, not before Phase 1)

- Data-residency region & key-management jurisdiction.
- Statutory retention periods (UAE healthcare records).
- BAA/DPA for any external AI/STT provider.
- Terminology licensing (SNOMED CT, possibly LOINC subsets).
- DPO/legal sign-off on privacy notice and DPIA.
