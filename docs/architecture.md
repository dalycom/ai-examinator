# Architecture — AI Examinator

- **Status:** Draft v1 (Phase 0)
- **Last updated:** 2026-06-20

---

## 1. Architectural style

A **modular monolith** with **clean / hexagonal (ports-and-adapters)** boundaries. One deployable backend and one
frontend, organized into clear bounded contexts (modules). Each module owns its domain, application services,
infrastructure, and API. External and AI dependencies are accessed only through **ports** so that high-load
services (e.g. transcription) can later be extracted into separate services without rewriting callers.

**Why not microservices now:** premature distribution adds operational cost, latency, and failure modes that a
pilot does not need. Boundaries are kept strict so extraction is cheap later. See [ADR-0002](./adr/0002-modular-monolith.md).

## 2. High-level system diagram

```
                         ┌──────────────────────────────────────────────┐
                         │                  Browser (SPA)               │
                         │  Next.js + React + Tailwind + shadcn/ui      │
                         │  next-intl (EN/AR/FR, RTL/LTR)               │
                         └───────────────┬───────────────┬──────────────┘
                                  HTTPS  │          WSS   │ (live transcript/status)
                                         ▼                ▼
                         ┌──────────────────────────────────────────────┐
                         │              FastAPI (modular monolith)       │
                         │  API v1 routers │ application services │ domain│
                         │  ┌─────────────── Ports (adapters) ─────────┐ │
                         │  │ STT │ LLM │ Translation │ LangDetect │   │ │
                         │  │ MedicalNLP │ Storage │ Terminology │ ... │ │
                         │  └──────────────────────────────────────────┘ │
                         └───┬─────────┬──────────┬───────────┬───────────┘
                             │         │          │           │
                   ┌─────────▼──┐ ┌────▼────┐ ┌───▼─────┐ ┌───▼────────────┐
                   │ PostgreSQL │ │  Redis  │ │ S3/MinIO│ │ Celery workers │
                   │ (+pgvector)│ │ cache/  │ │ audio/  │ │ (idempotent)   │
                   │  + RLS     │ │ broker  │ │ docs    │ │                │
                   └────────────┘ └─────────┘ └─────────┘ └───┬────────────┘
                                                               │ ports
                                          ┌────────────────────▼─────────────────────┐
                                          │  AI providers (config-switchable)         │
                                          │  default: self-hosted (Whisper, local LLM)│
                                          │  optional: cloud (Azure/AWS/GCP) w/ BAA   │
                                          └───────────────────────────────────────────┘
```

## 3. Backend layering (per module)

```
modules/<context>/
├── domain/          # entities, value objects, domain services, invariants (no framework imports)
├── application/     # use cases, command/query handlers, Pydantic DTOs, port interfaces used
├── infrastructure/  # SQLAlchemy models, repository implementations, mappers
└── api/             # FastAPI routers, request/response schemas, dependency wiring (/api/v1)
```

**Dependency rule:** `api → application → domain`; `infrastructure` implements interfaces defined in
`application`/`domain`. Domain never imports framework or infrastructure code.

## 4. Ports & adapters (provider-agnostic AI)

Defined under `backend/app/adapters/` with an interface (port) + one or more implementations:

| Port | Responsibility | Default (self-hosted) | Optional (cloud) |
|---|---|---|---|
| `SpeechToTextPort` | audio → transcript segments | Whisper (local) | Azure Speech / AWS Transcribe Medical / GCP |
| `DiarizationPort` | speaker segmentation | pyannote (local) | provider diarization |
| `LanguageDetectionPort` | detect EN/AR/FR | fastText/local | cloud |
| `TranslationPort` | translate between EN/AR/FR | local NMT | cloud |
| `MedicalNlpPort` | entity/normalization helpers | local rules/models | cloud |
| `LlmPort` | structured extraction / generation | local LLM endpoint | Azure OpenAI / etc. |
| `ObjectStoragePort` | encrypted blobs + signed URLs | MinIO | S3 / Azure Blob |
| `TerminologyPort` | ICD-10/RxNorm/LOINC/SNOMED lookups | public/stub data | licensed services |

Selection is driven by configuration + **feature flags**. No business logic references a concrete provider.
See [ADR-0003](./adr/0003-provider-agnostic-ai.md).

## 5. Multi-tenancy & isolation

- Every tenant-owned row carries `organization_id`.
- **Repository layer** injects and asserts the active `organization_id` from the request context — the single
  enforcement choke point.
- **PostgreSQL Row-Level Security** policies provide defense-in-depth so a coding mistake cannot leak across tenants.
- Clinic-level and record-level scoping is applied via ABAC on top of RBAC.
- See [ADR-0004](./adr/0004-tenant-isolation.md).

## 6. AI suggestion data flow (human-in-the-loop)

```
transcript (corrected) ─► extraction use case ─► LlmPort (structured schema)
        │                                          │
        │                              validate against Pydantic schema
        │                                          │ (reject if invalid)
        ▼                                          ▼
  ExtractedFact rows  ◄── grounding check ──  AISuggestion + AIProvenance rows
        │                                          │  status = PENDING
        ▼                                          ▼
  Doctor reviews ──► approve / edit / reject ──► decision recorded (audited)
        │
        ▼
  Only APPROVED content can be included in a SIGNED ClinicalNote
```

No AI output is ever auto-applied. Signing is a separate, doctor-only, append-only action that seals the note
with a content hash.

## 7. Real-time pipeline (streaming consultation)

1. Browser captures audio, streams chunks over **WSS** to a consultation gateway endpoint.
2. Gateway persists encrypted chunks to object storage and enqueues transcription jobs (Redis/Celery).
3. Worker calls `SpeechToTextPort` + `DiarizationPort`; emits transcript segments.
4. Segments are pushed back to the client over WSS and persisted.
5. On disconnect, session state in Redis enables **interrupted-recording recovery**.

## 8. Cross-cutting concerns

- **Config:** Pydantic Settings, env-injected secrets, no secrets in code.
- **Errors:** structured error envelope, typed exceptions, problem-detail responses.
- **Logging:** structured JSON logs with a **PHI redaction filter**; correlation IDs; no patient data.
- **Observability:** OpenTelemetry traces, Prometheus-style metrics, health/readiness endpoints.
- **Jobs:** Celery with idempotency keys, retries with backoff, dead-letter handling, outbox dispatch.
- **API versioning:** path-based `/api/v1`; additive changes preferred; breaking changes bump version.
- **i18n:** server returns locale-aware messages; UI uses next-intl with EN/AR/FR resource bundles.

## 9. Frontend architecture

```
frontend/src/
├── app/                 # Next.js App Router (locale segment: /[locale]/...)
├── components/ui/       # shadcn/ui primitives
├── features/<domain>/   # feature-scoped components, hooks, api clients
├── lib/                 # api client, auth, query client, utils
├── i18n/                # next-intl config + messages/{en,ar,fr}.json
└── hooks/               # shared hooks
```

- **Forms:** React Hook Form + Zod (schemas shared in spirit with backend Pydantic contracts).
- **Data:** TanStack Query for server state; WebSocket hook for live consultation.
- **RTL:** direction derived from locale; logical CSS properties; mirrored layouts; tested in AR.
- **Provenance UI:** distinct visual treatment for patient-provided / doctor-entered / AI-extracted /
  AI-suggested / doctor-approved data.

## 10. Environments

| Env | Purpose | Data |
|---|---|---|
| local | developer machines (docker-compose) | synthetic only |
| ci | automated tests & scans | synthetic only |
| staging | integration & UAT | synthetic / de-identified |
| production | pilot | real PHI (guarded) |

## 11. Technology choices

See [ADR-0001](./adr/0001-tech-stack.md) for full rationale. Summary in the root README.

## 12. Future extraction candidates

- Transcription/diarization workers (CPU/GPU heavy) → dedicated service.
- LLM inference gateway → dedicated service behind `LlmPort`.
- FHIR integration layer → dedicated service if external traffic grows.
These are isolated behind ports today, so extraction does not require caller changes.
