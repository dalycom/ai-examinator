# API Specification — AI Examinator

- **Status:** Draft v1 — Phase 1 endpoints documented; Phase 2 endpoints **implemented** (OpenAPI is authoritative).
- **Last updated:** 2026-06-21

---

## 1. Conventions

- **Base path:** `/api/v1`. Versioning is path-based; breaking changes bump the version.
- **Auth:** `Authorization: Bearer <access_token>`. Access tokens are short-lived; refresh via `/auth/refresh`.
- **Tenancy:** the active `organization_id` is derived from the authenticated principal — never accepted from the
  client body for scoping. Cross-tenant references are rejected.
- **Locale:** `Accept-Language: en | ar | fr` controls localized messages and report rendering.
- **Idempotency:** mutating endpoints that may be retried accept `Idempotency-Key` header.
- **Pagination:** cursor-based: `?limit=&cursor=`; responses include `next_cursor`.
- **Content type:** `application/json` (file upload endpoints use multipart or signed-URL flow).

### Standard error envelope (RFC 7807-style)

```json
{
  "type": "https://errors.ai-examinator/validation",
  "title": "Validation failed",
  "status": 422,
  "code": "VALIDATION_ERROR",
  "detail": "Localized human-readable message",
  "errors": [{ "field": "email", "message": "invalid email" }],
  "trace_id": "01J..."
}
```

> Error `detail`/messages are localized and **never** contain PHI.

### Standard success envelope (collections)

```json
{ "data": [ ... ], "next_cursor": "...", "total_estimate": 42 }
```

---

## 2. Health & meta

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | none | liveness |
| GET | `/ready` | none | readiness (db, redis, storage) |
| GET | `/api/v1/openapi.json` | none | OpenAPI document |

---

## 3. Phase 1 — Auth

| Method | Path | Permission | Description |
|---|---|---|---|
| POST | `/api/v1/auth/register-organization` | public (bootstrap) | create org + first admin |
| POST | `/api/v1/auth/login` | public | email + password → tokens (MFA challenge if enabled) |
| POST | `/api/v1/auth/mfa/verify` | public (mfa session) | verify TOTP |
| POST | `/api/v1/auth/refresh` | refresh token | rotate access/refresh |
| POST | `/api/v1/auth/logout` | authed | revoke refresh token |
| GET | `/api/v1/auth/me` | authed | current principal + permissions + locale |
| POST | `/api/v1/auth/mfa/enroll` | authed | begin TOTP enrollment |

**Example — login**
```http
POST /api/v1/auth/login
Content-Type: application/json

{ "email": "doctor@example-clinic.test", "password": "••••••" }
```
```json
{
  "access_token": "…", "token_type": "bearer", "expires_in": 900,
  "refresh_token": "…",
  "mfa_required": false,
  "user": { "id": "…", "full_name": "Dr Example", "preferred_locale": "ar" }
}
```

---

## 4. Phase 1 — Identity & Admin

| Method | Path | Permission | Description |
|---|---|---|---|
| GET/POST | `/api/v1/clinics` | `clinic:read` / `clinic:manage` | list/create clinics |
| GET/PATCH | `/api/v1/clinics/{id}` | `clinic:read`/`clinic:manage` | get/update clinic |
| GET/POST | `/api/v1/users` | `user:read`/`user:manage` | list/invite users |
| PATCH | `/api/v1/users/{id}` | `user:manage` | update user/status |
| GET | `/api/v1/roles` | `role:read` | list roles |
| POST | `/api/v1/users/{id}/roles` | `role:assign` | assign role (optional clinic scope) |
| GET | `/api/v1/audit-logs` | `audit:read` | query audit (compliance officer) |

---

## 5. Phase 2 — Patients & records (implemented)

| Method | Path | Permission | Notes |
|---|---|---|---|
| GET/POST | `/api/v1/patients` | `patient:read` / `patient:create` | List ordered by name; auto MRN |
| GET/PATCH | `/api/v1/patients/{id}` | `patient:read` / `patient:update` | Audit on update |
| GET/POST | `/api/v1/patients/{id}/allergies` | `patient:read` / `patient:update` | RxNorm-ready `substance_code` |
| GET/POST | `/api/v1/patients/{id}/medications` | `patient:read` / `patient:update` | RxNorm-ready `drug_code` |
| GET/POST | `/api/v1/patients/{id}/history` | `patient:read` / `patient:update` | Categories: medical, surgical, family, social |
| POST | `/api/v1/patients/{id}/problems` | `patient:update` | ICD-10-ready `icd10_code` |
| POST | `/api/v1/patients/{id}/vitals` | `patient:update` | LOINC-ready `loinc_code` |
| GET/POST | `/api/v1/appointments` | `appointment:read` / `appointment:manage` | |
| POST | `/api/v1/encounters` | `consultation:start` | Optional `appointment_id` link |
| GET | `/api/v1/encounters/{id}` | `patient:read` | |
| POST | `/api/v1/patients/{id}/documents:create-upload` | `document:upload` | Returns presigned PUT URL |
| POST | `/api/v1/documents/{id}:finalize` | `document:upload` | Marks upload complete |
| GET | `/api/v1/patients/{id}/documents` | `document:read` | |
| GET | `/api/v1/patients/{id}/timeline` | `patient:read` | Chronological read model |
| GET | `/api/v1/terminology/icd10` | `patient:read` | Stub sample codes |
| GET | `/api/v1/terminology/rxnorm` | `patient:read` | Stub sample codes |

**Document upload flow:** `POST …/documents:create-upload` → client PUT to presigned URL → `POST …/documents/{id}:finalize`.

**Frontend (Phase 2):** `/[locale]/login`, `/[locale]/patients`, `/[locale]/patients/[id]` — see [phase-2-completion-report.md](./phase-2-completion-report.md).

**Frontend (Phase 3):** `/[locale]/patients/[id]/consultation/[sessionId]` — see [phase-3-completion-report.md](./phase-3-completion-report.md).

**Deferred:** lab/imaging result records → Phase 5.

---

## 6. Phase 3 — Consultation (implemented)

| Method | Path | Permission | Notes |
|---|---|---|---|
| POST | `/api/v1/patients/{id}/consents` | `consent:capture` | Scopes: `recording`, `ai_processing` |
| GET | `/api/v1/patients/{id}/consents` | `patient:read` | |
| POST | `/api/v1/consents/{id}:revoke` | `consent:capture` | |
| POST | `/api/v1/encounters/{id}/sessions` | `consultation:start` | Creates session + draft note |
| GET | `/api/v1/sessions/{id}` | `consultation:start` | |
| POST | `/api/v1/sessions/{id}/recording:start` | `recording:write` | **Requires active recording consent** |
| POST | `/api/v1/sessions/{id}/audio:create-upload` | `recording:write` | Presigned PUT URL |
| POST | `/api/v1/sessions/{id}/audio:finalize` | `recording:write` | Triggers batch STT (stub) |
| POST | `/api/v1/sessions/{id}/recovery?last_seq=` | `recording:write` | Recovery checkpoint |
| GET | `/api/v1/sessions/{id}/transcript` | `transcript:read` | |
| PATCH | `/api/v1/sessions/{id}/transcript/{segId}` | `transcript:edit` | Doctor correction |
| GET/PATCH | `/api/v1/sessions/{id}/note` | `note:read` / `note:edit` | SOAP JSON content |
| POST | `/api/v1/sessions/{id}/note:sign` | `note:sign` | SHA-256 content hash; immutable |
| POST | `/api/v1/sessions/{id}/note:addendum` | `note:edit` | After signed note |

**Frontend:** `/[locale]/patients/[id]/consultation/[sessionId]` — consent, recording, transcript, note tabs.

### WebSocket — live consultation (scaffold)
`WSS /api/v1/ws/sessions/{id}?token=<access_token>` — chunk ack + resume; full streaming STT deferred.

```json
{ "type": "audio_chunk", "seq": 12, "data": "<base64>" }
{ "type": "chunk_ack", "seq": 12 }
{ "type": "resume", "last_seq": 12 }
{ "type": "resume_ack", "last_seq": 12, "session_status": "recording" }
```

Recovery: on reconnect the client sends `{ "type": "resume", "last_seq": 12 }`.

---

## 7. Phase 4 — AI assistant (implemented)

| Method | Path | Permission | Notes |
|---|---|---|---|
| POST | `/api/v1/sessions/{id}/extract` | `ai:run` | Runs structured extraction (stub LLM; sync) |
| GET | `/api/v1/sessions/{id}/facts` | `ai:read` | Extracted facts + run status |
| GET | `/api/v1/sessions/{id}/summary` | `ai:read` | Generated summary (`is_ai_generated: true`) |
| GET | `/api/v1/sessions/{id}/suggestions` | `ai:read` | DDx / missing-q / exams / red flags |
| POST | `/api/v1/suggestions/{id}/decision` | `ai:review` | `{ "decision": "approved\|edited\|rejected", ... }` |
| GET | `/api/v1/suggestions/{id}/provenance` | `ai:read` | model/prompt/version/input_hash |
| GET | `/api/v1/governance/feature-flags` | `governance:manage` | Org AI feature flags |

**Requires:** active `ai_processing` consent. Cloud LLM blocked unless `AI_ALLOW_EXTERNAL_PHI=true`.

**Async extraction:** set `AI_USE_CELERY_EXTRACTION=true` and run the Celery worker; default is synchronous for local/test.

**Frontend:** consultation workspace **AI assistant** tab — `/[locale]/patients/[id]/consultation/[sessionId]`.

---

## 8. Phase 5 — Integrations & reporting

Base: `/api/v1`

| Method | Path | Permission | Notes |
|---|---|---|---|
| GET | `/fhir/Patient/{id}` | `patient:read` | FHIR R4 Patient resource |
| GET | `/fhir/Encounter/{id}` | `patient:read` | FHIR R4 Encounter resource |
| GET | `/fhir/Observation?patient={id}` | `patient:read` | Bundle of vitals + lab/imaging |
| GET | `/patients/{id}/lab-imaging-results` | `patient:read` | LOINC/DICOM-ready rows |
| POST | `/patients/{id}/lab-imaging-results` | `patient:update` | Create lab or imaging result |
| GET | `/dashboard/summary` | `patient:read` | Org clinical KPIs |
| POST | `/reports` | `note:read` | Generate localized HTML report |
| GET | `/reports/{id}` | `note:read` | Fetch report body |
| POST | `/export-jobs` | `export:run` | DSAR export (sync default; Celery optional) |
| GET | `/export-jobs/{id}` | `export:run` | Job status |
| GET | `/export-jobs/{id}/download` | `export:run` | JSON export bundle |
| GET/POST | `/erasure-requests` … | `erasure:run` | DSAR erasure workflow |
| GET | `/notifications` | `patient:read` | In-app notifications |
| POST | `/notifications/{id}/read` | `patient:read` | Mark read |
| GET/PUT | `/retention-policies` … | `governance:manage` | Retention config |
| GET | `/governance/dashboard` | `governance:manage` | Flags + eval + retention |

**Async export:** set `EXPORT_USE_CELERY=true` and run the Celery worker; default is synchronous for local/test.

**Frontend:** `/[locale]/dashboard`, `/admin`, `/governance` — EN/AR/FR + RTL.

---

## 9. Security headers & limits

Implemented in Phase 6:

- **Headers:** `X-Content-Type-Options: nosniff`, `Referrer-Policy`, `X-Frame-Options: DENY`, `Permissions-Policy`, HSTS when `APP_ENV=staging|production`.
- **Rate limits:** Redis-backed fixed window on `/api/v1/auth/*` and `/api/v1/*` when `RATE_LIMIT_ENABLED=true`.
- CORS strict allowlist (existing).
- Request size limits; audio chunk size caps; upload virus/type scanning hook (planned for production WAF).
