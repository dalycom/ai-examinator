# ADR-0002: Modular monolith architecture

- **Status:** Accepted
- **Date:** 2026-06-20

## Context

The platform spans many bounded contexts (identity, records, consultation, AI, integration). We need clear
boundaries and the ability to scale specific high-load services (transcription, AI inference) later, without the
operational overhead of microservices during a pilot.

## Decision

Build a **modular monolith** with clean/hexagonal boundaries. Each module has `domain`, `application`,
`infrastructure`, and `api` layers. External/AI dependencies are accessed only via **ports** in `adapters/`.
One deployable backend, one frontend, shared database with strict module ownership of tables.

## Consequences

**Positive:** simpler deploy/observability; fast local dev; strong boundaries enable later extraction; single
transaction boundary where needed.
**Negative:** risk of boundary erosion without discipline; one process for many concerns.
**Follow-ups:** enforce import rules (lint/architecture tests); identify extraction candidates (workers, LLM gateway,
FHIR) and keep them behind ports.

## Alternatives considered

- Microservices from day one (rejected: premature complexity, latency, failure modes).
- Unstructured monolith (rejected: would not allow clean later extraction).
