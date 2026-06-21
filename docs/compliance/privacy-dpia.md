# Data Protection Impact Assessment (DPIA) — AI Examinator

- **Status:** Engineering draft for legal/DPO review (Phase 6)
- **Version:** 1.0
- **Last updated:** 2026-06-21

> Not legal advice. Requires sign-off by Data Protection Officer and legal counsel before pilot.

---

## 1. Processing overview

| Field | Value |
|---|---|
| **Controller** | Pilot clinic / organization tenant |
| **Processor** | AI Examinator platform operator (TBC for pilot) |
| **Purpose** | Clinical documentation, decision support, DSAR/export, audit |
| **Lawful basis (indicative)** | Healthcare provision + explicit consent (recording, AI) |
| **Data subjects** | Patients, clinicians, administrative staff |
| **Special category data** | Health data (PHI) — audio, transcripts, clinical notes |

## 2. Data flows

1. Clinician captures **consent** (recording + AI processing).
2. Audio uploaded via **signed URL** to encrypted object storage.
3. Transcription + AI extraction produce **labeled suggestions** (never auto-signed).
4. Clinician reviews/approves before signed record.
5. **Export/erasure** workflows support DSAR (Phase 5).

## 3. Risks & mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Cross-tenant data leak | Low (with controls) | Critical | RLS + service scoping + isolation tests |
| Unauthorized AI cloud PHI | Medium (misconfig) | Critical | `AI_ALLOW_EXTERNAL_PHI=false` default; feature flags |
| Autonomous clinical decision | Low | Critical | HITL required; AI safety spec; no auto-sign |
| Insider abuse | Medium | High | RBAC, audit chain, least privilege |
| DSAR failure | Low | High | Export/erasure APIs + audit |
| Backup loss | Low | High | DR scripts + drill checklist |

## 4. Necessity & proportionality

- Audio/transcription: necessary for consultation documentation workflow.
- AI suggestions: optional, consent-gated, human-reviewed only.
- Retention: org-configurable policies (defaults in product).

## 5. Sign-off

| Role | Name | Date | Signature |
|---|---|---|---|
| DPO | | | |
| Legal | | | |
| Clinical lead | | | |
| Engineering | | | |
