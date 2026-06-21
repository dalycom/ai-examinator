# Product Requirements Document — AI Examinator

- **Status:** Draft v1 (Phase 0)
- **Last updated:** 2026-06-20
- **Owner:** Product / Clinical Architecture

---

## 1. Vision

AI Examinator is a multilingual clinical decision-support platform that reduces clinician documentation
burden and improves decision quality by listening to consultations, transcribing and structuring them, and
surfacing **evidence-based, fully-traceable suggestions** that a doctor reviews and approves. The doctor
always remains the decision-maker.

## 2. Goals & non-goals

### Goals
- Cut documentation time by automating transcription, structuring, and draft note generation.
- Improve completeness of clinical records (symptoms, history, red flags, relevant negatives).
- Support EN/AR/FR consultations and UI, including full Arabic RTL.
- Provide safe, traceable AI suggestions (DDx, missing questions, recommended exams, next steps).
- Maintain a defensible, auditable, compliance-ready record of every action.

### Non-goals (for the pilot)
- Autonomous diagnosis or treatment decisions.
- Automatic prescribing or auto-signing of records.
- Native mobile apps (web-first, responsive desktop/tablet).
- Billing/insurance claims processing.
- Real e-prescribing transmission to national systems (document-only until integration is confirmed).

## 3. Personas

| Persona | Needs | Key permissions |
|---|---|---|
| **Doctor / Clinician** | Fast documentation, reliable suggestions, full control, sign records | Create/edit encounters, approve AI output, sign reports, prescribe (document) |
| **Nurse / Medical Staff** | Capture vitals, prep patient, manage docs | Edit vitals/docs, view records, no signing |
| **Clinic Admin** | Manage staff, schedules, clinic config | Manage users/roles within clinic, view reports |
| **Organization Admin** | Manage clinics, org-wide policy, AI governance | Org-wide settings, AI governance, retention policy |
| **Compliance / Privacy Officer** | Audit access, manage consent/retention, handle DSAR | Read audit logs, run export/erasure workflows |
| **System Administrator** | Operate platform, configure providers | System config, provider/feature flags, no PHI by default |
| **Patient** (out of app for pilot) | Consent, receive reports | N/A in pilot UI; consent captured by clinician |

## 4. Primary clinical workflow (canonical)

1. Doctor opens or creates a **patient profile**.
2. Doctor records the patient's **consent** for audio recording and AI processing.
3. Doctor starts a **consultation session**.
4. System **records/streams** the conversation securely.
5. System performs **multilingual speech-to-text**.
6. System attempts **speaker diarization** (doctor vs patient).
7. Doctor **reviews/corrects** the transcript.
8. AI **extracts structured clinical information** (chief complaint, symptoms, onset/duration, severity/progression,
   medical & surgical history, family & social history, allergies, current/previous medications, vitals & exam
   findings, risk factors, relevant negatives, red-flag symptoms).
9. AI generates a **structured summary and draft note**.
10. AI may suggest **differential diagnoses, missing questions, recommended examinations, next steps**.
11. Each suggestion includes **reasoning, supporting facts, uncertainty, and warning signs**.
12. Doctor **confirms / edits / rejects** every AI conclusion.
13. Only **doctor-approved** content enters the **signed medical record**.
14. The full consultation, approved report, transcript, prescriptions, documents, and **audit history** are stored securely.

## 5. Functional requirements (by module)

See [module-map.md](./module-map.md) for boundaries. Summary:

- **Identity & Access:** auth, MFA-ready, SSO-ready, RBAC+ABAC, multi-org/multi-clinic.
- **Patients & Records:** registration, medical profile, history, allergies, medications, documents, timeline.
- **Scheduling:** appointments and calendar.
- **Consultation:** consent, secure recording, upload, transcription, diarization, transcript correction, note editor, draft/signed states.
- **AI Assistant:** extraction, summary, note generation, missing-question & DDx suggestions, red-flag detection, review/approval, provenance, evaluation.
- **Clinical data:** diagnoses/problem lists, prescriptions, drug-interaction & allergy warnings, vitals/exam, lab/imaging.
- **Integration & Reporting:** FHIR layer, lab/imaging readiness, dashboards, reports, export, notifications, admin, AI governance.
- **Governance:** consent & privacy, immutable audit logs, retention/deletion/export workflows.

## 6. Non-functional requirements

| Category | Requirement |
|---|---|
| **Security** | Encryption in transit & at rest; tenant isolation; least privilege; signed URLs; immutable audit; no PHI in logs. |
| **Privacy** | Explicit consent; retention policies; de-identification for analytics/eval; right to erasure. |
| **Availability** | Target 99.5% pilot; graceful degradation when AI/STT providers are down. |
| **Performance** | Live transcript latency target < 3s for streaming; note-draft generation < 30s typical. |
| **Reliability** | Idempotent background jobs; interrupted-recording recovery; transactional writes. |
| **Accessibility** | WCAG 2.1 AA target; keyboard nav; high contrast; readable typography; RTL parity. |
| **Internationalization** | EN/AR/FR full parity; locale-aware dates/numbers; RTL/LTR layout. |
| **Observability** | Centralized logs, metrics, tracing, alerting, health checks. |
| **Maintainability** | Strict typing, linting, module boundaries, ADRs, API versioning. |

## 7. AI safety requirements (summary)

Every AI suggestion must carry: suggested concept, supporting facts, missing info, conflicting info, confidence,
red-flag warnings, source references, model & prompt version, generation timestamp, and the doctor's decision.
The system must **never** present AI output as a confirmed diagnosis, auto-sign, auto-prescribe, hide uncertainty,
invent data, or leak one patient's data into another's context. Full detail in [ai-safety-spec.md](./ai-safety-spec.md).

## 8. Compliance scope

Compliance-readiness for UAE healthcare requirements, **UAE PDPL**, **HIPAA** where applicable, and **GDPR** where
applicable. See [compliance-checklist.md](./compliance-checklist.md).

## 9. Healthcare data standards

Design for compatibility with HL7 FHIR R4, ICD-10, SNOMED CT (subject to licensing), LOINC, DICOM references, and
RxNorm / approved regional medication terminology. Licensed terminologies sit behind interfaces and remain disabled
until licensing is confirmed.

## 10. Success metrics (pilot)

- Median documentation time reduced vs baseline.
- ≥ X% of AI-extracted facts accepted without edit (target set during clinical validation).
- Zero cross-patient data leakage incidents.
- 100% of signed records have complete consent + audit trail.
- Clinician satisfaction (SUS) ≥ target.

## 11. Open questions

Tracked in the [README of the chat plan and ADRs]; notably: data residency region, external-AI BAA/DPA status,
terminology licensing, SSO/IdP choice, and statutory retention periods. These do not block Phase 1.
