# ADR-0004: Multi-tenant isolation (scoping + Postgres RLS)

- **Status:** Accepted
- **Date:** 2026-06-20
- **Decision input:** Stakeholder selected multi-tenant SaaS (shared DB).

## Context

We operate a multi-tenant SaaS over a shared PostgreSQL database. Cross-tenant (and cross-patient) data leakage is
the highest-severity risk for a healthcare platform.

## Decision

Use a **layered, defense-in-depth** isolation model:
1. Every tenant-owned table has `organization_id`.
2. The **repository layer** is the single choke point that injects and asserts the active `organization_id` from
   request context; scoping fields are never accepted from client bodies.
3. **PostgreSQL Row-Level Security** policies enforce `organization_id` independently, so an application bug cannot
   leak across tenants.
4. Clinic-/record-level access uses **ABAC** overlays on top of RBAC.
5. CI includes an isolation test proving Org A cannot access Org B via any path.

## Consequences

**Positive:** strong, testable isolation; bug-resilient; single cost-effective database.
**Negative:** RLS adds query/session complexity (must set tenant GUC per connection); careful connection pooling needed.
**Follow-ups:** implement per-request tenant context propagation to DB session; add RLS policies in migrations;
consider per-tenant encryption keys later for highly sensitive fields.

## Alternatives considered

- Database-per-tenant (rejected for pilot: operational overhead, migration complexity; revisit for large customers).
- App-layer-only scoping (rejected: single point of failure; no defense-in-depth).
