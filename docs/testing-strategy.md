# Testing Strategy — AI Examinator

- **Status:** Draft v1 (Phase 0)
- **Last updated:** 2026-06-20

> **Golden rule:** No real patient data in any test, fixture, or evaluation dataset. All data is synthetic or
> properly de-identified.

---

## 1. Test pyramid

| Level | Scope | Tooling (planned) |
|---|---|---|
| Unit | domain logic, value objects, validators, pure functions | pytest (backend), vitest (frontend) |
| Integration | repositories, DB (RLS), Redis, storage adapters, services | pytest + testcontainers/ephemeral Postgres |
| API / contract | FastAPI routes, auth, error envelopes, OpenAPI conformance | pytest + httpx, schemathesis |
| Security | authz, tenant isolation, prompt injection, redaction | pytest security suite + SAST/scanners |
| E2E | critical user journeys across FE+BE | Playwright (EN/AR/FR + RTL) |
| AI evaluation | extraction/suggestion quality, safety | custom eval harness on synthetic data |

## 2. Mandatory quality gates (CI must pass)

1. **Format:** ruff format (Python), prettier (TS).
2. **Lint:** ruff (Python), eslint (TS).
3. **Type-check:** mypy/pyright (Python, strict), tsc (TS, strict).
4. **Unit + integration + API tests** green.
5. **Security suite** green (authz, isolation, redaction).
6. **Dependency scan:** pip-audit, npm audit (high/critical fail build).
7. **Container scan:** Trivy on built images.
8. **Coverage thresholds:** domain/application ≥ 85%; security suite must cover every permission key.

## 3. Security & privacy test focus

- **Tenant isolation:** programmatic proof that a principal in Org A cannot read/write Org B data via any endpoint
  or repository path; RLS verified independently of app-layer checks.
- **Authorization matrix:** a test per cell of the [permission matrix](./permission-matrix.md) (allowed/denied/ABAC).
- **Signing/prescribing guards:** non-doctors cannot sign/prescribe; no auto-sign path exists.
- **PHI redaction:** assert logs/traces/error responses contain no PHI for representative flows.
- **Signed-URL scope:** documents/audio inaccessible without valid short-lived URL; URLs expire.
- **Rate limiting:** auth/AI endpoints enforce limits.

## 4. AI safety test focus (Phase 4)

- **Schema validation:** malformed model output is rejected, never displayed/stored.
- **Grounding:** ungrounded facts/citations are dropped/rejected.
- **Single-subject:** synthetic multi-patient context attempts are blocked (cross-patient-leak rate = 0).
- **Prompt injection:** transcripts/documents containing injected instructions do not alter behavior or trigger tools.
- **HITL:** pending suggestions cannot enter a signed note; decisions are audited.
- **Degradation:** provider-down scenarios degrade gracefully.

## 5. Internationalization & accessibility testing

- **Locale parity:** EN/AR/FR render all key screens; missing-translation detection in CI.
- **RTL:** Arabic layouts mirrored correctly; logical CSS properties verified; E2E run in AR.
- **A11y:** automated axe checks + keyboard-navigation E2E; contrast checks; focus management.
- **States:** empty, loading, error, and interrupted-recording recovery have explicit tests.

## 6. Test data management

- **Synthetic factories** (e.g. Faker with medical-safe generators) produce patients/encounters/transcripts.
- **De-identification** utilities for any data derived from real sources (not used in pilot dev).
- **Seed scripts** clearly marked non-production and refuse to run against production config.

## 7. Performance & resilience testing (Phase 6)

- Load tests for streaming transcription (WSS concurrency) and AI endpoints.
- Soak tests for memory/queue stability; chaos tests for provider outages.
- Disaster-recovery restore test from backups.

## 8. CI/CD integration

- All gates run on every PR; security/AI suites also run nightly.
- Migrations tested (upgrade + downgrade) against ephemeral Postgres.
- Build artifacts scanned before promotion to staging/production.

## 9. Definition of Done (per module)

- [ ] Unit + integration + API tests added and green.
- [ ] Authz + tenant-isolation tests added for new endpoints.
- [ ] EN/AR/FR + RTL verified for new UI.
- [ ] No PHI in logs; redaction verified.
- [ ] Docs (data dictionary / API / relevant spec) updated.
- [ ] Lint/format/type-check/scans pass.
