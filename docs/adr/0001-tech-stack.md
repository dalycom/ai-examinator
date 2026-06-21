# ADR-0001: Technology stack

- **Status:** Accepted
- **Date:** 2026-06-20

## Context

We need a productive, well-typed, widely-supported stack for a healthcare platform with real-time transcription,
AI integration, strong typing, and i18n/RTL needs. The brief recommends a specific stack; we evaluate and adopt it.

## Decision

- **Frontend:** Next.js (App Router) + TypeScript (strict), React, Tailwind CSS, shadcn/ui, next-intl for i18n,
  React Hook Form + Zod, TanStack Query, native WebSocket (WSS) for live updates.
- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2 (typed), Pydantic v2, Alembic, Celery (Redis broker), OpenAPI.
- **Data/Infra:** PostgreSQL (+pgvector where justified), Redis, S3-compatible storage (MinIO locally), Docker,
  Kubernetes-ready, GitHub Actions CI/CD with security scanning.

## Consequences

**Positive:** strong typing end-to-end; first-class OpenAPI; mature i18n/RTL; large ecosystems; clear async/job story.
**Negative:** two languages (TS/Python) to maintain; Celery adds operational surface.
**Follow-ups:** confirm self-hosted model runtime; choose pyright vs mypy (default: both where feasible, pyright in editor).

## Alternatives considered

- Node/NestJS full-stack (rejected: weaker ML / medical NLP ecosystem compared to Python for AI work).
- Django (rejected: FastAPI better fits async streaming + typed DTOs).
- Pages Router (rejected: App Router better for locale segments + server components).
