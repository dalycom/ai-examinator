# Data Dictionary — AI Examinator

- **Status:** Draft v1 (Phase 0) — Phase 1 tables fully specified; later tables specified as they are implemented.
- **Last updated:** 2026-06-20

Conventions: all ids are UUID primary keys. `organization_id` is present on every tenant-owned table and is the
RLS predicate. Timestamps are `timestamptz`. "FK→X" denotes a foreign key. Sensitive fields are flagged.

## Common columns (all tenant-owned tables)

| Column | Type | Null | Notes |
|---|---|---|---|
| id | uuid | no | PK |
| organization_id | uuid | no | FK→organization; RLS |
| created_at | timestamptz | no | default now() |
| updated_at | timestamptz | no | auto-update |
| created_by | uuid | yes | FK→user |
| updated_by | uuid | yes | FK→user |
| deleted_at | timestamptz | yes | soft delete |
| data_classification | enum | no | public/internal/phi/sensitive_phi |

---

## Phase 1 tables

### organization
| Column | Type | Null | Notes |
|---|---|---|---|
| id | uuid | no | PK |
| name | text | no | |
| slug | text | no | unique |
| status | enum | no | active/suspended |
| default_locale | enum | no | en/ar/fr |
| created_at/updated_at | timestamptz | no | |

> Root tenant; not itself scoped by `organization_id`.

### clinic
| Column | Type | Null | Notes |
|---|---|---|---|
| id | uuid | no | PK |
| organization_id | uuid | no | FK→organization |
| name | text | no | |
| timezone | text | no | IANA tz |
| address | jsonb | yes | |
| status | enum | no | active/inactive |

### user
| Column | Type | Null | Notes |
|---|---|---|---|
| id | uuid | no | PK |
| organization_id | uuid | no | FK→organization |
| email | citext | no | unique per org |
| full_name | text | no | |
| password_hash | text | no | **sensitive** (Argon2) |
| mfa_secret | text | yes | **sensitive**, field-encrypted |
| mfa_enabled | bool | no | default false |
| status | enum | no | invited/active/disabled |
| preferred_locale | enum | no | en/ar/fr |
| last_login_at | timestamptz | yes | |

### clinic_membership
| Column | Type | Null | Notes |
|---|---|---|---|
| id | uuid | no | PK |
| organization_id | uuid | no | FK→organization |
| clinic_id | uuid | no | FK→clinic |
| user_id | uuid | no | FK→user |
| is_primary | bool | no | default false |

### role
| Column | Type | Null | Notes |
|---|---|---|---|
| id | uuid | no | PK |
| organization_id | uuid | yes | null = system/global role |
| key | text | no | e.g. doctor, nurse, clinic_admin |
| name | text | no | localizable label key |
| is_system | bool | no | system roles immutable |

### permission
| Column | Type | Null | Notes |
|---|---|---|---|
| id | uuid | no | PK |
| key | text | no | e.g. `patient:read`, `note:sign` |
| description | text | no | |

### user_role
| Column | Type | Null | Notes |
|---|---|---|---|
| id | uuid | no | PK |
| organization_id | uuid | no | FK→organization |
| user_id | uuid | no | FK→user |
| role_id | uuid | no | FK→role |
| clinic_id | uuid | yes | optional clinic scope (ABAC) |

### role_permission
| Column | Type | Null | Notes |
|---|---|---|---|
| role_id | uuid | no | FK→role (PK part) |
| permission_id | uuid | no | FK→permission (PK part) |

### audit_log
| Column | Type | Null | Notes |
|---|---|---|---|
| id | uuid | no | PK |
| organization_id | uuid | yes | scope (null for system events) |
| actor_user_id | uuid | yes | FK→user |
| action | text | no | e.g. `auth.login`, `patient.read`, `ai.suggestion.approve` |
| resource_type | text | yes | |
| resource_id | uuid | yes | |
| metadata | jsonb | yes | **no PHI**; redacted summary only |
| ip_hash | text | yes | hashed source IP |
| prev_hash | text | yes | previous record hash |
| record_hash | text | no | hash(prev_hash + canonical(record)) |
| created_at | timestamptz | no | |

> Append-only. No updates/deletes. Hash chain provides tamper-evidence.

### refresh_token / session
| Column | Type | Null | Notes |
|---|---|---|---|
| id | uuid | no | PK |
| user_id | uuid | no | FK→user |
| token_hash | text | no | **sensitive** (hashed) |
| expires_at | timestamptz | no | |
| revoked_at | timestamptz | yes | |
| user_agent / ip_hash | text | yes | |

---

## Phase 2+ tables (summary — full columns added at implementation time)

| Table | Key fields | Notes |
|---|---|---|
| patient | mrn, given/family name, dob, sex, contact (jsonb), national_id (**sensitive**) | org-scoped |
| consent_record | patient_id, type (recording/ai_processing), scope, granted_by, method, granted_at, revoked_at | required before recording |
| allergy | patient_id, substance (RxNorm), reaction, severity, status | |
| medication | patient_id, drug (RxNorm), dose, route, frequency, start/end, status | |
| medical_history_entry | patient_id, category (medical/surgical/family/social), description, onset | |
| problem | patient_id, encounter_id, code (ICD-10), description, status, onset | problem list |
| vital_sign | encounter_id, type (LOINC), value, unit, measured_at | |
| lab_imaging_result | patient_id, code (LOINC), value/unit or dicom_ref, status, observed_at | |
| document | patient_id, kind, storage_key, mime, size, checksum | bytes in object storage |
| appointment | patient_id, clinic_id, clinician_id, start/end, status | |
| encounter | patient_id, appointment_id, clinician_id, type, started_at, status | |

## Phase 3+ tables (summary)

| Table | Key fields | Notes |
|---|---|---|
| consultation_session | encounter_id, status, locale, started/ended_at | lifecycle in erd.md |
| audio_recording | session_id, storage_key (**encrypted**), duration_ms, status, checksum | |
| transcript_segment | session_id, speaker_label, language, text (**phi**), confidence, start_ms, end_ms, edited | |
| clinical_note | session_id, status (draft/signed), body (**phi**), content_hash, signed_by, signed_at | immutable when signed |
| prescription | session_id, items (jsonb, RxNorm), status, confirmed_by | document-only |

## Phase 4 tables (AI)

| Table | Key fields | Notes |
|---|---|---|
| extracted_fact | session_id, fact_type, value (**phi**), source_segment_ref, confidence, status, provenance_id | |
| ai_suggestion | session_id, suggestion_type, concept, supporting_facts (jsonb), missing_info, conflicting_info, confidence, red_flag_warnings (jsonb), source_refs (jsonb), decision, decided_by, decided_at, provenance_id | HITL |
| ai_provenance | model_id, provider, prompt_version, input_hash, parameters (jsonb), generation_timestamp, latency_ms | no raw PHI in input_hash |
| prompt_version | key, version, template_ref, created_at | governance |
| eval_dataset / eval_run | name, items (synthetic), metrics (jsonb), prompt_version | synthetic data only |
| feature_flag | key, enabled, scope, conditions | experimental AI gating |

## Data classification policy

- `sensitive_phi`: transcript text, clinical note body, extracted facts, national_id, mfa_secret — field-level
  protection + strict access logging.
- `phi`: most patient records.
- `internal`: org/clinic config, roles.
- `public`: localizable labels, terminology codes.

All PHI columns are excluded from logs, traces, and non-de-identified exports.
