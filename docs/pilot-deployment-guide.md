# Pilot Deployment Guide — AI Examinator

- **Status:** Phase 6 controlled pilot
- **Last updated:** 2026-06-21

---

## 1. Prerequisites

- [ ] Phase 6 completion report reviewed and approved
- [ ] DPIA, privacy notice, sub-processors signed off ([compliance/](./compliance/))
- [ ] Data residency decision approved ([data-residency-decision.md](./compliance/data-residency-decision.md))
- [ ] Clinical validation checklist completed ([clinical-validation-checklist.md](./clinical-validation-checklist.md))
- [ ] AI eval gates passing in CI (`python -m app.scripts.run_ai_eval`)

## 2. Environment

| Variable | Pilot recommendation |
|---|---|
| `APP_ENV` | `staging` |
| `AI_ALLOW_EXTERNAL_PHI` | `false` |
| `RATE_LIMIT_ENABLED` | `true` |
| `SECRET_KEY` | From secret manager (≥32 chars) |
| Database / Redis / Storage | Region-locked, encrypted |

Use strong secrets and TLS termination at the ingress (HSTS enabled automatically when `APP_ENV=staging|production`).

## 3. Deploy steps

```bash
# 1. Build and push images (CI or manual)
docker compose build

# 2. Run migrations on pilot database
docker compose exec backend alembic upgrade head

# 3. Seed synthetic UAT org OR import pilot org via register-organization API
docker compose exec backend python -m app.scripts.seed_synthetic

# 4. Smoke tests
curl -f https://<pilot-host>/health
python scripts/load_smoke.py --base-url https://<pilot-host> --auth-smoke
```

## 4. Post-deploy checks

- [ ] Login + MFA policy (if enabled)
- [ ] Tenant isolation spot-check (two orgs)
- [ ] Audit log writes on auth and AI review
- [ ] Backup job scheduled (`scripts/dr_backup.sh` or managed service)
- [ ] Monitoring alerts configured (error rate, latency, disk)

## 5. Rollback

1. Stop traffic at ingress.
2. Restore database from last backup if schema/data issue (`scripts/dr_restore.sh`).
3. Redeploy previous image tag.
4. Document incident in runbook.

## 6. Pilot scope limits

- Maximum **N** clinics (define per contract)
- Synthetic eval only until clinical sign-off on real cases
- No public internet exposure without WAF + IP allowlist (recommended)

## 7. External assessments (scheduled, not blocking local sign-off)

| Activity | Owner | Target |
|---|---|---|
| Third-party penetration test | Security | Before production scale |
| DAST on staging | Security | Each release candidate |
| WCAG audit with assistive tech | UX/QA | Before AR patient-facing pilot |

---

See also [deployment-guide.md](./deployment-guide.md) and [operational-runbook.md](./operational-runbook.md).
