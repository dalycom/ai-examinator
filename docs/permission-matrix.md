# Permission Matrix — AI Examinator

- **Status:** Draft v1 (Phase 0)
- **Last updated:** 2026-06-20

RBAC with ABAC overlays. Roles are assigned per organization and optionally scoped to a clinic. Permissions are
fine-grained keys (`resource:action`). ABAC adds record-level constraints (e.g. clinic membership, ownership).

## Roles

| Role key | Description |
|---|---|
| `org_admin` | Organization-wide administration & AI governance |
| `clinic_admin` | Manage a clinic's staff, schedule, config |
| `doctor` | Full clinical workflow incl. signing & prescribing (document) |
| `nurse` | Vitals, documents, patient prep; no signing |
| `compliance_officer` | Audit, consent, export/erasure; no clinical edits |
| `system_admin` | Platform config, providers, feature flags; **no PHI by default** |

## Permission keys (Phase 1–4)

`org:manage`, `clinic:read`, `clinic:manage`, `user:read`, `user:manage`, `role:read`, `role:assign`,
`audit:read`, `patient:read`, `patient:create`, `patient:update`, `patient:delete`,
`consent:capture`, `appointment:read`, `appointment:manage`, `document:upload`, `document:read`,
`consultation:start`, `recording:write`, `transcript:read`, `transcript:edit`,
`note:read`, `note:edit`, `note:sign`, `prescription:write`,
`ai:run`, `ai:read`, `ai:review`, `governance:manage`, `export:run`, `erasure:run`,
`config:manage`, `flag:manage`.

## Matrix (✓ = allowed; ▲ = allowed with ABAC scope; ✗ = denied)

| Permission | org_admin | clinic_admin | doctor | nurse | compliance | system_admin |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| org:manage | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| clinic:read | ✓ | ▲ | ▲ | ▲ | ✓ | ✗ |
| clinic:manage | ✓ | ▲ | ✗ | ✗ | ✗ | ✗ |
| user:read | ✓ | ▲ | ✗ | ✗ | ✓ | ✗ |
| user:manage | ✓ | ▲ | ✗ | ✗ | ✗ | ✗ |
| role:read | ✓ | ▲ | ✗ | ✗ | ✓ | ✗ |
| role:assign | ✓ | ▲ | ✗ | ✗ | ✗ | ✗ |
| audit:read | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ |
| patient:read | ✓ | ▲ | ▲ | ▲ | ▲ | ✗ |
| patient:create | ✓ | ▲ | ▲ | ▲ | ✗ | ✗ |
| patient:update | ✓ | ▲ | ▲ | ▲ | ✗ | ✗ |
| patient:delete | ▲ | ✗ | ✗ | ✗ | ▲ | ✗ |
| consent:capture | ✗ | ▲ | ▲ | ▲ | ✗ | ✗ |
| appointment:read | ✓ | ▲ | ▲ | ▲ | ✗ | ✗ |
| appointment:manage | ✓ | ▲ | ▲ | ▲ | ✗ | ✗ |
| document:upload | ✗ | ▲ | ▲ | ▲ | ✗ | ✗ |
| document:read | ✓ | ▲ | ▲ | ▲ | ▲ | ✗ |
| consultation:start | ✗ | ✗ | ▲ | ✗ | ✗ | ✗ |
| recording:write | ✗ | ✗ | ▲ | ▲ | ✗ | ✗ |
| transcript:read | ✗ | ✗ | ▲ | ▲ | ✗ | ✗ |
| transcript:edit | ✗ | ✗ | ▲ | ✗ | ✗ | ✗ |
| note:read | ✗ | ✗ | ▲ | ▲ | ▲ | ✗ |
| note:edit | ✗ | ✗ | ▲ | ✗ | ✗ | ✗ |
| **note:sign** | ✗ | ✗ | **▲** | ✗ | ✗ | ✗ |
| **prescription:write** | ✗ | ✗ | **▲** | ✗ | ✗ | ✗ |
| ai:run | ✗ | ✗ | ▲ | ▲ | ✗ | ✗ |
| ai:read | ✗ | ✗ | ▲ | ▲ | ✗ | ✗ |
| **ai:review** | ✗ | ✗ | **▲** | ✗ | ✗ | ✗ |
| governance:manage | ✓ | ✗ | ✗ | ✗ | ✗ | ▲ |
| export:run | ▲ | ✗ | ✗ | ✗ | ✓ | ✗ |
| erasure:run | ▲ | ✗ | ✗ | ✗ | ✓ | ✗ |
| config:manage | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| flag:manage | ▲ | ✗ | ✗ | ✗ | ✗ | ✓ |

## ABAC rules (overlays)

- **Clinic scope:** `clinic_admin`, `doctor`, `nurse` act only within clinics they are members of (`clinic_membership`).
- **Patient scope:** clinical roles access only patients within their clinic(s)/organization.
- **Ownership:** transcript/note **edit** typically limited to the assigned clinician of the encounter (configurable).
- **Signing:** only the responsible doctor of the encounter may sign that encounter's note.
- **System admin & PHI:** `system_admin` is denied PHI access by default; any break-glass access is heavily audited and time-boxed.

## Enforcement points

1. **API dependency** checks the required permission key per route.
2. **Application service** re-checks permission + ABAC constraints (defense-in-depth).
3. **Repository** enforces `organization_id` scoping + Postgres RLS.

## Notes

- System roles are immutable; custom roles can be created per organization (Phase 5 admin).
- Break-glass / emergency access is a Phase 6 consideration with mandatory justification + alerting.
