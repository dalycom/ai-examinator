# AI Examinator — Documentation Index

This folder contains all Phase 0 architecture and governance deliverables. Documents are living artifacts:
they are updated at the end of every module and phase.

## Reading order

1. [Product Requirements Document](./product-requirements.md) — what we're building and why.
2. [Architecture](./architecture.md) — how the system is structured.
3. [Module Map](./module-map.md) — bounded contexts and dependencies.
4. [ERD](./erd.md) + [Data Dictionary](./data-dictionary.md) — the data model.
5. [API Specification](./api-specification.md) — REST + WebSocket contracts.
6. [AI Safety Specification](./ai-safety-spec.md) — guardrails for all AI behavior.
7. [Threat Model](./threat-model.md) + [Permission Matrix](./permission-matrix.md) + [Compliance Checklist](./compliance-checklist.md) — security & compliance.
8. [Testing Strategy](./testing-strategy.md) — quality gates.
9. [Deployment Guide](./deployment-guide.md) + [Operational Runbook](./operational-runbook.md) — running it.
10. [Backlog](./backlog.md) — phased implementation plan.
11. [Phase 1 Completion Report](./phase-1-completion-report.md) · … · [Phase 6 Completion Report](./phase-6-completion-report.md)
12. [Pilot Deployment Guide](./pilot-deployment-guide.md) · [Clinical Validation Checklist](./clinical-validation-checklist.md)
13. [Compliance](./compliance/) (DPIA, privacy notice, sub-processors, residency)
14. [ADRs](./adr/) — architecture decision records.

## Document ownership & change control

- Every document has a **status** and a **last-updated** date in its header.
- Material changes to architecture, data model, or security posture require a new or updated **ADR**.
- Changes that affect AI behavior require an update to the **AI Safety Specification** and its evaluation suite.

## Glossary (selected)

| Term | Meaning |
|---|---|
| PHI | Protected Health Information |
| PDPL | UAE Personal Data Protection Law |
| RLS | PostgreSQL Row-Level Security |
| Diarization | Distinguishing which speaker said what |
| DDx | Differential diagnosis |
| HITL | Human-in-the-loop |
| Provenance | Full traceability metadata attached to an AI output |
| Signed record | Doctor-approved, immutable, hash-sealed clinical document |
