# Sub-processors Register — AI Examinator

- **Status:** Phase 6 pilot baseline
- **Last updated:** 2026-06-21

| Sub-processor | Purpose | Data processed | Region (pilot default) | PHI allowed |
|---|---|---|---|---|
| **Self-hosted Postgres** | Primary database | PHI metadata, clinical records | UAE (pilot TBC) | Yes |
| **Self-hosted Redis** | Cache, rate limits, Celery broker | Session/rate-limit keys (no PHI content) | UAE | No PHI by design |
| **S3-compatible storage (MinIO / AWS S3)** | Documents, audio | PHI blobs | UAE | Yes (encrypted) |
| **Self-hosted LLM (default)** | AI extraction/suggestions | Transcript text (consent-gated) | In-tenant boundary | Yes (default path) |
| **Cloud LLM (optional)** | AI extraction | Transcript text | Vendor region | **Blocked unless** `AI_ALLOW_EXTERNAL_PHI=true` + contract/BAA |

## Change management

1. New sub-processors require DPO + legal review.
2. Customer notification per DPA (30 days standard).
3. Updated register committed to repo and pilot contract annex.

## Pilot note

Local development uses Docker containers only — **not** production sub-processors. Pilot environment must replace this table with contracted vendors and regions.
