# Architecture Decision Records

ADRs capture significant, hard-to-reverse decisions and their rationale. Each record is immutable once accepted;
changes are made by adding a new ADR that supersedes a previous one.

| ADR | Title | Status |
|---|---|---|
| [0001](./0001-tech-stack.md) | Technology stack | Accepted |
| [0002](./0002-modular-monolith.md) | Modular monolith architecture | Accepted |
| [0003](./0003-provider-agnostic-ai.md) | Provider-agnostic AI (both self-hosted & cloud, default self-hosted) | Accepted |
| [0004](./0004-tenant-isolation.md) | Multi-tenant isolation (scoping + Postgres RLS) | Accepted |
| [0005](./0005-localization-rtl.md) | Localization & RTL strategy (EN/AR/FR) | Accepted |
| [0006](./0006-ai-human-in-the-loop.md) | AI human-in-the-loop & immutable signed records | Accepted |

## Template

```
# ADR-NNNN: Title
- Status: Proposed | Accepted | Superseded by ADR-XXXX
- Date: YYYY-MM-DD
## Context
## Decision
## Consequences (positive / negative / follow-ups)
## Alternatives considered
```
