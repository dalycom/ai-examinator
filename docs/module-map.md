# Module Map — AI Examinator

- **Status:** Draft v1 (Phase 0)
- **Last updated:** 2026-06-20

Bounded contexts grouped into layers. Dependencies flow downward only; a lower layer must never import an upper
layer. AI modules read from Consultation/Records via application services, never raw DB access.

## Layers

```
┌────────────────────────────────────────────────────────────────────────────┐
│ FOUNDATION                                                                   │
│  core · auth · identity (orgs/clinics) · rbac · audit · i18n · notifications │
└───────────────┬──────────────────────────────────────────────────────────-─┘
                │
┌───────────────▼──────────────────────────────────────────────────────────--┐
│ CLINICAL RECORDS                                                             │
│  patients · medical_history · allergies · medications · vitals · problems    │
│  appointments · encounters · documents · clinical_timeline · lab_imaging     │
└───────────────┬───────────────────────────────────────────────────────────-┘
                │
┌───────────────▼──────────────────────────────────────────────────────────--┐
│ CONSULTATION WORKSPACE                                                       │
│  consent · recording · transcription · diarization · transcript_edit         │
│  clinical_note · consultation_state · prescriptions                          │
└───────────────┬──────────────────────────────────────────────────────────-─┘
                │
┌───────────────▼───────────────────────────────────────────────────────────-┐
│ AI CLINICAL ASSISTANT                                                        │
│  extraction · summary · note_gen · suggestions (ddx, missing_q, exams, next) │
│  red_flags · review_approval · ai_provenance · evaluation · governance       │
└───────────────┬──────────────────────────────────────────────────────────-─┘
                │
┌───────────────▼───────────────────────────────────────────────────────────-┐
│ INTEGRATION & REPORTING                                                      │
│  fhir · lab_imaging_integration · dashboards · reports · export ·            │
│  retention_deletion · admin · ai_governance_dashboard                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Module catalog

| Module | Layer | Responsibility | Key dependencies |
|---|---|---|---|
| `core` | Foundation | config, db session, security primitives, error handling, logging, base repository | — |
| `auth` | Foundation | login/registration, sessions, JWT, MFA-ready, SSO-ready | core |
| `identity` | Foundation | organizations, clinics, memberships | core, auth |
| `rbac` | Foundation | roles, permissions, RBAC+ABAC enforcement | core, identity |
| `audit` | Foundation | immutable, hash-chained audit log | core |
| `i18n` | Foundation | server-side locale messages, locale negotiation | core |
| `notifications` | Foundation | notifications & reminders (in-app, email-ready) | core, identity |
| `patients` | Records | patient registration & medical profile | identity, rbac, audit |
| `medical_history` | Records | history entries, family/social history | patients |
| `allergies` | Records | allergy records + interaction checks | patients, medications |
| `medications` | Records | medication & prescription records, drug interactions | patients |
| `vitals` | Records | vital signs & exam findings | patients, encounters |
| `problems` | Records | diagnoses & problem lists (ICD-10) | patients, encounters |
| `appointments` | Records | scheduling & calendar | identity, patients |
| `encounters` | Records | clinical encounters | patients, appointments |
| `documents` | Records | attachments, signed-URL access | patients, storage adapter |
| `clinical_timeline` | Records | unified chronological view | patients + read models |
| `lab_imaging` | Records | lab/imaging results & DICOM references (LOINC) | patients, encounters |
| `consent` | Consultation | recording & AI-processing consent | patients, audit |
| `recording` | Consultation | secure capture/upload of audio | consent, storage adapter |
| `transcription` | Consultation | STT orchestration (streaming + batch) | recording, STT/diarization ports |
| `transcript_edit` | Consultation | doctor transcript correction | transcription |
| `clinical_note` | Consultation | note editor, draft & signed states, hashing | encounters, transcript_edit |
| `consultation_state` | Consultation | session lifecycle, recovery | recording, transcription |
| `prescriptions` | Consultation | prescription records (document-only) | medications, clinical_note |
| `extraction` | AI | structured clinical info extraction | transcript_edit, LlmPort, ai_provenance |
| `summary` | AI | consultation summary | extraction, LlmPort |
| `note_gen` | AI | draft note generation | extraction, summary, LlmPort |
| `suggestions` | AI | DDx, missing questions, exams, next steps | extraction, LlmPort |
| `red_flags` | AI | red-flag detection | extraction, suggestions |
| `review_approval` | AI | HITL approve/edit/reject workflow | all AI outputs, audit |
| `ai_provenance` | AI | model/prompt/version/timestamp/confidence records | core |
| `evaluation` | AI | eval datasets & metrics per prompt version | ai_provenance |
| `governance` | AI | AI config, feature flags, prompt versions | rbac, ai_provenance |
| `fhir` | Integration | FHIR R4 read/write mapping | records + clinical modules |
| `dashboards` | Integration | clinical dashboards | read models |
| `reports` | Integration | report generation (EN/AR/FR) | clinical_note, records |
| `export` | Integration | data export workflows | records, audit |
| `retention_deletion` | Integration | retention policy, right-to-erasure | records, audit |
| `admin` | Integration | org/clinic administration | identity, rbac |
| `ai_governance_dashboard` | Integration | governance UI/back-end | governance, evaluation |

## Adapters (cross-module ports)

`stt`, `diarization`, `language_detection`, `translation`, `medical_nlp`, `llm`, `object_storage`, `terminology`.
All live in `backend/app/adapters/` and are injected via dependency wiring. See [architecture.md](./architecture.md#4-ports--adapters-provider-agnostic-ai).

## Build order (maps to phases)

1. **Phase 1:** core, auth, identity, rbac, audit, i18n, notifications (scaffold).
2. **Phase 2:** patients, medical_history, allergies, medications, vitals, problems, appointments, encounters, documents, clinical_timeline.
3. **Phase 3:** consent, recording, transcription, diarization, transcript_edit, clinical_note, consultation_state, prescriptions.
4. **Phase 4:** extraction, summary, note_gen, suggestions, red_flags, review_approval, ai_provenance, evaluation, governance.
5. **Phase 5:** fhir, lab_imaging, dashboards, reports, export, notifications (full), admin, ai_governance_dashboard.
6. **Phase 6:** hardening across all modules.
