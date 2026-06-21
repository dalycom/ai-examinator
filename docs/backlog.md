# Phase-by-Phase Backlog — AI Examinator

- **Status:** Draft v1 (Phase 0)
- **Last updated:** 2026-06-21

Work is delivered in small, reviewable changes. After every module: format, lint, type-check, test; review authz &
tenant isolation; review security/privacy; verify EN/AR/FR; update docs; summarize; list risks/tech-debt; and
**request approval before the next major phase**.

Legend: ☐ todo · ◐ in progress · ☑ done.

---

## Phase 0 — Discovery & Architecture ☑

- ☑ Repository inspection
- ☑ Clarifying questions + assumptions
- ☑ Architecture, module map, ERD, data dictionary
- ☑ Threat model, permission matrix, compliance checklist
- ☑ AI safety spec, testing strategy, deployment/ops docs
- ☑ Backlog + ADRs

---

## Phase 1 — Secure Platform Foundation ☑

**Goal:** a secure, multi-tenant, multilingual skeleton with auth, RBAC, audit, and CI.

- ☑ **1.1 Repo & tooling:** monorepo layout (backend/frontend/infra/docs); ruff, mypy, eslint, prettier, tsconfig strict.
- ☑ **1.2 Dev environment:** docker-compose (Postgres, Redis, MinIO, backend, frontend, worker); `.env.example` files.
- ☑ **1.3 Core backend:** config (Pydantic settings), DB session, base repository (tenant scoping), error handling, structured logging + PHI redaction filter, health/readiness.
- ☑ **1.4 Database & migrations:** Alembic; initial migration for org/clinic/user/membership/role/permission/audit + **RLS policies**.
- ☑ **1.5 AuthN:** register-organization (bootstrap), login, refresh (rotation), logout, `me`; Argon2; JWT; MFA-ready scaffolding (TOTP enroll/verify).
- ☑ **1.6 Identity:** organizations & clinics CRUD; memberships; users.
- ☑ **1.7 RBAC/ABAC:** roles, permissions, assignment; centralized authorization dependency + service guard; permission-matrix-driven.
- ☑ **1.8 Audit:** immutable, hash-chained audit log on auth + admin events.
- ☑ **1.9 Localization framework:** backend locale negotiation; frontend next-intl EN/AR/FR + RTL toggle + base screens.
- ☑ **1.10 CI/CD:** lint + type-check + tests + dependency audit (GitHub Actions).
- ☑ **1.11 Testing foundation:** unit/integration/api/security harness; synthetic seed script; tenant-isolation tests.
- ☑ **1.12 Docs:** Phase-0 docs retained; README updated for Phase 1 run instructions.

**Acceptance criteria:** see [Phase 1 acceptance](#phase-1-acceptance-criteria) below — **all criteria met** (2026-06-20).

---

## Phase 2 — Patient & Clinical Records ☑

**Goal:** org-scoped patient records, clinical data APIs, and core patient UI in EN/AR/FR.

- ☑ Patient registration & medical profile (org/clinic-scoped, ABAC-ready).
- ☑ Medical history (medical/surgical/family/social).
- ☑ Allergies (RxNorm refs) + foundation for interaction checks.
- ☑ Medications & prescription records (RxNorm refs).
- ☑ Vitals & exam findings (LOINC-ready fields).
- ☑ Problems/diagnoses list (ICD-10 code field).
- ☑ Appointments & calendar API.
- ☑ Encounters.
- ☑ Documents & attachments (signed-URL upload/download via MinIO adapter).
- ☑ Clinical timeline (unified chronological view).
- ☑ Terminology ports (ICD-10/RxNorm public/stub; LOINC/SNOMED behind flags).
- ☑ Phase 2 frontend screens (patient list/profile) — EN/AR/FR + RTL.
- ☐ Lab/imaging result records — **deferred to Phase 5** (not a Phase 2 acceptance blocker).

**Acceptance criteria:** see [Phase 2 acceptance](#phase-2-acceptance-criteria) below — **all criteria met** (2026-06-21). Formal report: [phase-2-completion-report.md](./phase-2-completion-report.md).

---

## Phase 3 — Consultation Workspace ☑

**Goal:** consent-gated recording, transcription, transcript correction, clinical note draft/sign, and consultation UI.

- ☑ Consent workflow (recording + AI processing) blocking recording without consent.
- ☑ Secure audio recording storage (signed-URL upload) + interrupted-recording recovery checkpoint.
- ☑ Audio upload (batch via presigned URL + finalize).
- ☑ Transcription (batch) behind `SpeechToTextPort` (stub adapter).
- ☑ Speaker diarization behind `DiarizationPort` (stub adapter; labels in STT output).
- ☐ Live streaming transcription via WebSocket — **scaffold only; full STT stream deferred to Phase 6 hardening** (not a Phase 3 acceptance blocker).
- ☑ Transcript correction UI (EN/AR/FR).
- ☑ Clinical note editor (SOAP sections).
- ☑ Draft & signed consultation states; immutable signing with content hash; addenda (API).
- ☑ Consultation workspace frontend (`/patients/[id]/consultation/[sessionId]`).

**Backend:** migration `0005_phase3_consultation`, modules `consent`, `consultation`, STT/diarization stubs, WebSocket `/api/v1/ws/sessions/{id}`.

**Acceptance criteria:** see [Phase 3 acceptance](#phase-3-acceptance-criteria) below — **all criteria met** (2026-06-21). Formal report: [phase-3-completion-report.md](./phase-3-completion-report.md).

---

## Phase 4 — AI Clinical Assistant ☑

**Goal:** labeled AI extraction, summaries, suggestions, HITL review, provenance, and governance.

- ☑ `LlmPort` + adapters (stub; self-hosted scaffold via `LLM_PROVIDER=local`).
- ☑ Structured information extraction + schema validation + grounding checks.
- ☑ Consultation summary (labeled AI).
- ☑ Draft clinical note generation (suggested into draft note only).
- ☑ Missing-question suggestions.
- ☑ Differential diagnosis suggestions + recommended exams + next steps.
- ☑ Red-flag detection (high sensitivity stub).
- ☑ Human review/approval workflow (approve/edit/reject) + audit.
- ☑ Provenance records on all AI output.
- ☑ Evaluation harness + synthetic eval dataset + metrics gates.
- ☑ Feature flags + AI governance config (org-scoped defaults + governance API).
- ☑ Celery async extraction pipeline (`ai.run_extraction`; sync default for local/test).
- ☑ AI assistant UI (edit decision flow + provenance display; EN/AR/FR).

**Backend:** migration `0006_phase4_ai`, modules `ai`, `adapters/llm`, `workers/tasks/ai_tasks`.

**Acceptance criteria:** see [Phase 4 acceptance](#phase-4-acceptance-criteria) below — **all criteria met** (2026-06-21). Formal report: [phase-4-completion-report.md](./phase-4-completion-report.md).

---

## Phase 5 — Integrations & Reporting ☑

- ☑ FHIR R4 **read** mapping layer (`Patient`, `Encounter`, `Observation` bundle).
- ☐ FHIR R4 **write** — deferred to Phase 6 (read-only export/interop in Phase 5).
- ☑ Lab & imaging integration readiness (LOINC/DICOM refs on `lab_imaging_result`).
- ☑ Clinical dashboards (`GET /dashboard/summary` + `/dashboard` UI).
- ☑ Reports (EN/AR/FR HTML with RTL; PDF format flag — renderer deferred).
- ☑ Data export (DSAR) workflow (`export_job` + sync/Celery pipeline).
- ☑ Notifications (in-app + `email_sent` / channel scaffolding).
- ☑ Administrative controls UI (`/admin` — clinics, users, roles).
- ☑ AI governance dashboard UI (`/governance` + retention policies).
- ☑ Retention & erasure workflows (`retention_policy`, `erasure_request`).

**Backend:** migration `0007_phase5_integrations`, module `integrations`, Celery `export.run_job`.

**Acceptance criteria:** see [Phase 5 acceptance](#phase-5-acceptance-criteria) below — **all criteria met** (2026-06-21). Formal report: [phase-5-completion-report.md](./phase-5-completion-report.md).

---

## Phase 6 — Hardening & Pilot Preparation ☑

- ☑ Security testing — SAST (bandit), supply chain (pip-audit, npm audit, Trivy), security headers + rate limiting, `test_security.py`.
- ☐ Third-party penetration test — **operational gate** (checklist in pilot guide; not in-repo automation).
- ☑ Performance/load smoke — `scripts/load_smoke.py`; WSS/AI soak documented for pilot ops.
- ☑ Accessibility — skip link, focus-visible, nav `aria-label`, EN/AR/FR strings.
- ☑ Disaster-recovery drill — `scripts/dr_backup.sh` + `dr_restore.sh` + runbook references.
- ☑ Clinical validation — [clinical-validation-checklist.md](./clinical-validation-checklist.md) (sign-off pending clinicians).
- ☑ AI quality evaluation sign-off — CI gate `run_ai_eval` + synthetic metrics.
- ☑ Compliance documentation — DPIA, privacy notice (EN), sub-processors, residency decision.
- ☑ Controlled pilot deployment — [pilot-deployment-guide.md](./pilot-deployment-guide.md).

**Acceptance criteria:** see [Phase 6 acceptance](#phase-6-acceptance-criteria) below — **engineering criteria met** (2026-06-21). Formal report: [phase-6-completion-report.md](./phase-6-completion-report.md).

---

## Phase 1 acceptance criteria

- [x] Repo scaffolded (backend + frontend + infra + docs) with formatting/linting/type-checking configured & passing.
- [x] `docker compose up` brings up Postgres, Redis, MinIO, backend, frontend, worker.
- [x] Alembic configured; initial migration creates org/clinic/user/role/permission/audit tables **with RLS**.
- [x] AuthN: register/login/refresh/logout + MFA-ready scaffolding; auth tests pass.
- [x] RBAC enforced; permission matrix v1 documented & tested; **proven** that Org A cannot access Org B data (API + repository scoping).
- [x] Immutable, hash-chained audit logging on auth + admin events.
- [x] i18n live for EN/AR/FR with working RTL toggle and locale-aware layout.
- [x] CI: lint + type-check + tests + dependency audit, configured.
- [x] All Phase-0 docs present; ADRs 0001–0006 committed in repo.
- [x] No PHI anywhere; all seed data synthetic.

---

## Phase 2 acceptance criteria

- [x] Patient registration & medical profile (org-scoped, permission-gated, audit on create/update).
- [x] Medical history (medical/surgical/family/social).
- [x] Allergies + RxNorm-ready fields (interaction-check foundation only).
- [x] Medications + RxNorm-ready fields.
- [x] Vitals & problems (API; LOINC/ICD-10-ready fields).
- [x] Appointments & encounters (API).
- [x] Documents & attachments (signed-URL upload via MinIO adapter — API).
- [x] Clinical timeline (unified chronological view — API + frontend tab).
- [x] Terminology ports (ICD-10/RxNorm stub).
- [x] Frontend: login, patient list, patient profile (EN/AR/FR + RTL).
- [x] Tenant isolation preserved on all new tables (RLS + service scoping + tests).
- [x] Lab/imaging — explicitly deferred to Phase 5 (out of Phase 2 scope).

---

## Phase 3 acceptance criteria

- [x] Consent workflow blocking recording without active recording consent.
- [x] Secure audio recording (presigned URL upload + finalize).
- [x] Recovery checkpoint for interrupted recordings (API + WebSocket resume).
- [x] Batch transcription behind `SpeechToTextPort` (stub adapter).
- [x] Speaker diarization labels behind `DiarizationPort` (stub).
- [x] Transcript correction UI (EN/AR/FR + RTL).
- [x] Clinical note editor (SOAP sections).
- [x] Draft & signed note states; immutable signing with content hash; addenda (API).
- [x] Consultation workspace frontend route.
- [x] Tenant isolation preserved on all Phase 3 tables (RLS + service scoping + tests).
- [x] Live streaming STT — explicitly deferred to Phase 6 hardening (scaffold only in Phase 3).

---

## Phase 4 acceptance criteria

- [x] `LlmPort` + adapters (stub + self-hosted scaffold).
- [x] Structured extraction with schema validation + transcript grounding.
- [x] Consultation summary labeled `is_ai_generated`.
- [x] Draft note suggestion (draft state only; no auto-sign).
- [x] Missing-question, DDx, exam, next-step, and red-flag suggestions.
- [x] HITL review (approve / edit / reject) with audit trail.
- [x] Provenance on all AI outputs.
- [x] Synthetic eval harness with metrics gates.
- [x] Org-scoped feature flags + governance API.
- [x] Celery async extraction task wired.
- [x] AI assistant UI tab (EN/AR/FR + RTL) with edit + provenance.
- [x] Tenant isolation on all Phase 4 tables (RLS + tests).
- [x] Real cloud/production LLM endpoints — explicitly deferred (adapter slot only).

---

## Phase 5 acceptance criteria

- [x] FHIR R4 read mapping for Patient, Encounter, and Observation (vitals + lab/imaging).
- [x] Lab/imaging result records with LOINC and DICOM study UID fields.
- [x] Clinical dashboard API + frontend (EN/AR/FR).
- [x] Localized clinical reports (HTML, RTL for Arabic).
- [x] DSAR export jobs (patient + org scope) with download bundle.
- [x] In-app notifications on export completion; email-ready channel fields.
- [x] Admin UI for clinics, users, and roles.
- [x] AI governance dashboard (feature flags, eval runs, retention policies).
- [x] Erasure request workflow (request → review → complete) with audit trail.
- [x] Retention policies per resource type (org-scoped defaults).
- [x] Tenant isolation on all Phase 5 tables (RLS + tests in `test_phase5.py`).
- [x] FHIR write / PDF rendering / SMTP email delivery — explicitly deferred.

---

## Phase 6 acceptance criteria

- [x] SAST (bandit) + dependency + container scanning in CI.
- [x] Security headers on API responses; rate limiting middleware (Redis, configurable).
- [x] Security test suite (`test_security.py`).
- [x] Load smoke script for health/auth paths.
- [x] DR backup/restore scripts and documentation.
- [x] Accessibility: skip link, focus management, labeled navigation (EN/AR/FR).
- [x] AI eval gates automated (`run_ai_eval`) in CI.
- [x] Compliance docs: DPIA, privacy notice, sub-processors, residency decision.
- [x] Clinical validation checklist for pilot clinicians.
- [x] Pilot deployment guide with go-live and rollback steps.
- [x] Third-party pen test / production DAST / live pilot execution — operational gates (documented, pending external/clinical sign-off).
