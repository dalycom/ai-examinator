# AI Examinator

A production-grade, multilingual (English / Arabic / French) **clinical decision-support platform**
that helps doctors document consultations and make better-informed decisions by securely listening to
doctor–patient conversations, transcribing them, structuring the medical information, generating clinical
summaries, and presenting **evidence-based suggestions for the doctor's review**.

> ⚠️ **Safety first.** AI Examinator never replaces the doctor, never makes an autonomous diagnosis, and never
> approves treatment without human confirmation. Every AI output is clearly labeled as a *suggestion* and
> requires explicit doctor review, edit, approval, or rejection before it can enter a signed medical record.

---

## Status

**Phase 1 — complete.** See [Phase 1 Completion Report](./docs/phase-1-completion-report.md).

**Phase 2 — Patient & Clinical Records — complete.** See [Phase 2 Completion Report](./docs/phase-2-completion-report.md).

**Phase 3 — Consultation Workspace — complete.** See [Phase 3 Completion Report](./docs/phase-3-completion-report.md).

**Phase 4 — AI Clinical Assistant — complete.** See [Phase 4 Completion Report](./docs/phase-4-completion-report.md).

**Phase 5 — Integrations & Reporting — complete.** See [Phase 5 Completion Report](./docs/phase-5-completion-report.md).

**Phase 6 — Hardening & Pilot Preparation — complete (engineering).** See [Phase 6 Completion Report](./docs/phase-6-completion-report.md).

**Next:** Controlled pilot execution — see [pilot deployment guide](./docs/pilot-deployment-guide.md).

```bash
cp .env.example .env
docker compose up --build
# in another terminal:
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.scripts.seed_synthetic
docker compose exec backend python -m app.scripts.seed_demo_clinical
```

**Demo sign-in** (after seed):

| Role | Email | Password |
|---|---|---|
| Doctor | `doctor@synthetic-demo.example.com` | `SyntheticDoctor123!` |
| Org admin | `admin@synthetic-demo.example.com` | `SyntheticDemo123!` |

- API: http://localhost:8000/api/v1/docs
- Frontend: http://localhost:3000/en (also `/ar`, `/fr`)

## Key decisions (locked in Phase 0)

| Decision | Choice |
|---|---|
| AI delivery | Provider-agnostic; **both** self-hosted and cloud paths, config-switchable, **default self-hosted** (PHI-safe) |
| Tenancy | **Multi-tenant SaaS**: shared PostgreSQL + `organization_id` scoping + Row-Level Security |
| Region | Region-agnostic for now (finalize before pilot; UAE residency assumed likely) |
| Architecture | **Modular monolith** with clean/hexagonal boundaries and ports-and-adapters |

## Languages

English, **Arabic (full RTL)**, French — across UI, documentation, transcription, summaries, notifications, and reports.

## Documentation

All deliverables live in [`docs/`](./docs/). Start with the [documentation index](./docs/README.md).

| Document | Path |
|---|---|
| Product Requirements | [docs/product-requirements.md](./docs/product-requirements.md) |
| Architecture | [docs/architecture.md](./docs/architecture.md) |
| Module Map | [docs/module-map.md](./docs/module-map.md) |
| ERD | [docs/erd.md](./docs/erd.md) |
| Data Dictionary | [docs/data-dictionary.md](./docs/data-dictionary.md) |
| API Specification | [docs/api-specification.md](./docs/api-specification.md) |
| Threat Model | [docs/threat-model.md](./docs/threat-model.md) |
| Permission Matrix | [docs/permission-matrix.md](./docs/permission-matrix.md) |
| AI Safety Specification | [docs/ai-safety-spec.md](./docs/ai-safety-spec.md) |
| Compliance Checklist | [docs/compliance-checklist.md](./docs/compliance-checklist.md) |
| Testing Strategy | [docs/testing-strategy.md](./docs/testing-strategy.md) |
| Deployment Guide | [docs/deployment-guide.md](./docs/deployment-guide.md) |
| Operational Runbook | [docs/operational-runbook.md](./docs/operational-runbook.md) |
| Phase-by-phase Backlog | [docs/backlog.md](./docs/backlog.md) |
| Phase 1 Completion Report | [docs/phase-1-completion-report.md](./docs/phase-1-completion-report.md) |
| Phase 2 Completion Report | [docs/phase-2-completion-report.md](./docs/phase-2-completion-report.md) |
| Phase 3 Completion Report | [docs/phase-3-completion-report.md](./docs/phase-3-completion-report.md) |
| Phase 4 Completion Report | [docs/phase-4-completion-report.md](./docs/phase-4-completion-report.md) |
| Phase 5 Completion Report | [docs/phase-5-completion-report.md](./docs/phase-5-completion-report.md) |
| Phase 6 Completion Report | [docs/phase-6-completion-report.md](./docs/phase-6-completion-report.md) |
| Pilot Deployment Guide | [docs/pilot-deployment-guide.md](./docs/pilot-deployment-guide.md) |
| AI Agent Training Roadmap | [docs/ai-agent-training-roadmap.md](./docs/ai-agent-training-roadmap.md) |
| Clinical Validation Checklist | [docs/clinical-validation-checklist.md](./docs/clinical-validation-checklist.md) |
| Compliance (DPIA, privacy, residency) | [docs/compliance/](./docs/compliance/) |
| Architecture Decision Records | [docs/adr/](./docs/adr/) |

## Planned technology stack

- **Frontend:** Next.js (App Router) + TypeScript, React, Tailwind CSS, shadcn/ui, next-intl, React Hook Form + Zod, TanStack Query, secure WebSockets.
- **Backend:** Python, FastAPI, SQLAlchemy 2, Pydantic v2, Alembic, Celery (Redis broker), OpenAPI.
- **Data/Infra:** PostgreSQL (+ pgvector where justified), Redis, S3-compatible encrypted storage (MinIO locally), Docker, Kubernetes-ready, CI/CD with security scanning.

## Privacy note

**No real patient data** is ever used in development, demos, fixtures, or tests. All seed and evaluation data is
synthetic or properly de-identified.
