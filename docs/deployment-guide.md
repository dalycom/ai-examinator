# Deployment Guide — AI Examinator

- **Status:** Draft v1 (Phase 0) — local development is implemented in Phase 1; staging/production hardened in Phase 6.
- **Last updated:** 2026-06-20

---

## 1. Topology

| Component | Local (docker-compose) | Staging/Prod (Kubernetes-ready) |
|---|---|---|
| Frontend (Next.js) | container | container / managed |
| Backend API (FastAPI) | container | horizontally scalable deployment |
| Worker (Celery) | container | separate deployment (CPU/GPU pools for AI) |
| PostgreSQL (+pgvector) | container | managed Postgres + read replicas |
| Redis | container | managed Redis |
| Object storage | MinIO container | S3-compatible (encrypted) |
| AI providers | self-hosted (default) | self-hosted in-boundary; cloud optional w/ BAA |

## 2. Local development (target Phase 1 experience)

Prerequisites: Docker + Docker Compose, Make (optional), Node 20+, Python 3.12+.

```bash
# 1. Copy env templates (never commit real secrets)
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# 2. Start the stack
docker compose up --build

# 3. Run migrations + seed SYNTHETIC data
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.scripts.seed_synthetic

# Services
# Frontend  http://localhost:3000
# API docs  http://localhost:8000/api/v1/docs
# MinIO     http://localhost:9001
```

## 3. Configuration (environment variables, no secrets in code)

Representative keys (full list maintained in `.env.example` files):

```
# Core
APP_ENV=local|staging|production
SECRET_KEY=...
DATABASE_URL=postgresql+psycopg://...
REDIS_URL=redis://...
OBJECT_STORAGE_ENDPOINT=...
OBJECT_STORAGE_BUCKET=...
OBJECT_STORAGE_KEY/SECRET=...        # via secret manager in prod

# Auth
ACCESS_TOKEN_TTL_SECONDS=900
REFRESH_TOKEN_TTL_SECONDS=1209600
MFA_ISSUER=AI-Examinator

# AI providers (provider-agnostic; default self-hosted)
AI_STT_PROVIDER=self_hosted|azure|aws|gcp
AI_LLM_PROVIDER=self_hosted|azure_openai|...
AI_ALLOW_EXTERNAL_PHI=false          # must be true + BAA to enable cloud PHI
FEATURE_FLAGS_BACKEND=db

# i18n
DEFAULT_LOCALE=en
SUPPORTED_LOCALES=en,ar,fr
```

Secrets in staging/production come from a secret manager (Vault/cloud KMS), never `.env` files.

## 4. Database & migrations

- Alembic for schema; every change is a reviewed migration with upgrade + downgrade.
- RLS policies are part of migrations.
- Migrations run as a pre-deploy job; backups taken before production migrations.

## 5. CI/CD pipeline (GitHub Actions, planned)

```
on PR:  install → lint → type-check → unit/integration/api/security tests
        → dependency scan (pip-audit, npm audit) → build images → Trivy scan
on main: above → push images → deploy staging → smoke tests
release: manual approval → deploy production (blue/green) → post-deploy checks
```

## 6. Production hardening checklist (Phase 6)

- [ ] TLS termination + HSTS; WSS only.
- [ ] Secrets in KMS/Vault; rotation policy.
- [ ] Network policies; private datastores; least-privilege IAM.
- [ ] Encrypted volumes/buckets; backup + tested restore (DR drill).
- [ ] Centralized logging (PHI-redacted), metrics, tracing, alerting.
- [ ] Autoscaling; resource limits; pod security.
- [ ] WAF / rate limiting at edge.
- [ ] Data-residency region confirmed; key jurisdiction confirmed.
- [ ] Image signing + provenance (supply-chain).

## 7. Rollback

- Blue/green or canary deploys; keep previous image.
- Database migrations are backward-compatible where possible; destructive changes are two-phase
  (expand → migrate → contract) to allow rollback.

## 8. Environments & promotion

`local → ci → staging (UAT, synthetic/de-identified) → production (pilot, guarded PHI)`.
No real PHI below production.
