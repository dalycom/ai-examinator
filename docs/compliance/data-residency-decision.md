# Data Residency Decision — AI Examinator Pilot

- **Status:** Phase 6 recommendation (pending executive sign-off)
- **Last updated:** 2026-06-21
- **Decision owner:** Product + Legal + Pilot clinic sponsor

---

## Recommendation

Deploy the **controlled pilot** with all PHI-processing components in a **single UAE region** (e.g. AWS `me-central-1` or equivalent sovereign cloud), unless the pilot clinic contract mandates a different jurisdiction.

## Rationale

- Aligns with UAE healthcare data sensitivity expectations
- Keeps audio, transcripts, and clinical records within agreed boundary
- Simplifies DPIA and sub-processor review for first pilot

## Configuration gates

| Setting | Pilot value |
|---|---|
| `APP_ENV` | `staging` or `production` |
| `AI_ALLOW_EXTERNAL_PHI` | `false` |
| Object storage | Region-locked bucket |
| Database | Region-locked managed Postgres |
| Backups | Same region; encrypted |

## Exceptions

Cross-border transfer requires:

1. Updated DPIA
2. Patient/clinic transparency update
3. Contractual safeguards (SCCs / UAE PDPL mechanisms as applicable)

## Sign-off

| Role | Approved | Date |
|---|---|---|
| Legal | ☐ | |
| DPO | ☐ | |
| Pilot clinic | ☐ | |
| Engineering | ☐ | |
