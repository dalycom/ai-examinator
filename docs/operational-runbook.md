# Operational Runbook — AI Examinator

- **Status:** Draft v1 (Phase 0) — expanded as operations mature (Phase 5–6).
- **Last updated:** 2026-06-20

> When handling incidents involving PHI, follow the privacy incident process: minimize exposure, do not copy PHI
> into tickets/logs, and notify the DPO/compliance officer.

---

## 1. Health & monitoring

| Signal | Endpoint / source | Healthy |
|---|---|---|
| Liveness | `GET /health` | 200 |
| Readiness | `GET /ready` | 200 (db, redis, storage OK) |
| Queue depth | Celery/Redis metrics | within threshold |
| Error rate | metrics/traces | below SLO |
| AI provider | adapter circuit-breaker state | closed |

Dashboards & alerts cover API latency/error rate, worker backlog, DB connections, storage errors, auth failures,
rate-limit triggers, and AI validation-failure rate.

## 2. Common operational tasks

### Run / verify migrations
```bash
alembic current
alembic upgrade head      # pre-deploy job; backup first in prod
alembic downgrade -1      # rollback last (only if backward-compatible)
```

### Rotate secrets
- Rotate in secret manager → roll deployments → revoke old. Never log secret values.

### Reprocess a failed transcription/AI job
- Jobs are idempotent. Re-enqueue by job id; confirm provenance/audit entries; do not duplicate records.

### Investigate audit trail
- Query `audit_log` (permission `audit:read`). Verify hash chain integrity:
  each `record_hash == hash(prev_hash + canonical(record))`.

## 3. Incident playbooks

### P1 — Suspected cross-tenant or cross-patient data exposure
1. **Contain:** disable the suspect endpoint/feature flag; revoke affected sessions if needed.
2. **Assess:** identify scope via audit logs (no PHI in incident notes).
3. **Eradicate:** patch isolation defect; add regression test proving fix.
4. **Notify:** DPO/compliance; follow PDPL/GDPR/HIPAA breach-notification timelines if confirmed.
5. **Review:** post-incident review; update threat model & tests.

### P2 — AI safety violation (e.g. ungrounded output displayed, label missing)
1. **Disable** the related AI feature flag immediately.
2. Capture provenance (model/prompt version) — not PHI.
3. Fix validation/grounding; add eval + test case; re-run eval suite before re-enabling.

### P3 — AI/STT provider outage
1. Confirm circuit breaker open; system should already degrade gracefully.
2. Communicate status; clinical documentation continues manually.
3. Optionally switch provider via config (if alternate is authorized).

### P4 — Auth incident (suspected account takeover)
1. Revoke refresh tokens/sessions for affected users; force re-auth + MFA.
2. Review auth audit logs; check rate-limit/lockout efficacy.
3. Notify affected org admins; rotate any exposed secrets.

### P5 — Data integrity (signed note tamper attempt)
1. Verify `content_hash`; signed notes are immutable — investigate source of change attempt.
2. Restore from backup if needed; preserve audit evidence.

## 4. Backup & disaster recovery

- Automated encrypted backups of Postgres + object storage; retention per policy.
- **DR drill (Phase 6):** restore to clean environment, verify integrity, measure RTO/RPO.
- Audit log periodically exported to WORM/immutable storage.

## 5. Data lifecycle operations

- **Export (DSAR):** `export-jobs` workflow produces machine-readable patient data; audited.
- **Erasure:** `erasure-requests` workflow respects legal holds/retention; audited; irreversible after grace period.
- **Retention sweep:** scheduled job applies retention policies (periods TBC for UAE).

## 6. Release operations

- Pre-deploy: backup, run migrations job, smoke tests.
- Deploy: blue/green or canary; watch error/latency/queue metrics.
- Post-deploy: verify health/readiness, run smoke E2E (incl. AR/RTL), check AI validation-failure rate.
- Rollback: switch traffic to previous; reverse migration only if backward-compatible.

## 7. On-call & escalation

- Severity definitions (P1–P5 above), response targets, and escalation contacts maintained in the ops directory
  (to be populated before pilot). PHI never included in alerts/tickets.
