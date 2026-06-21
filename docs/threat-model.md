# Threat Model — AI Examinator

- **Status:** Draft v1 (Phase 0)
- **Last updated:** 2026-06-20
- **Methodology:** STRIDE per data-flow, plus AI/LLM-specific threats (OWASP LLM Top 10) and multi-tenant risks.

---

## 1. Assets

| Asset | Sensitivity | Notes |
|---|---|---|
| Patient PHI (records, transcripts, notes, audio) | Critical | core protected data |
| Consent records | Critical | legal basis for processing |
| Audit logs | Critical | tamper-evidence, legal defensibility |
| Credentials / tokens / MFA secrets | Critical | account takeover risk |
| AI provenance & prompts | High | governance, reproducibility |
| Terminology/config | Medium | integrity matters |
| Object storage (audio/docs) | Critical | encrypted at rest, signed URLs only |

## 2. Trust boundaries

1. Browser ↔ API (public internet, TLS/WSS).
2. API ↔ datastores (Postgres/Redis/object storage) — internal network.
3. API/Workers ↔ AI providers — **self-hosted (in-boundary)** by default; **cloud (external)** only when explicitly configured with BAA/DPA.
4. Tenant ↔ Tenant — logical boundary enforced by `organization_id` + RLS.
5. User role ↔ user role — RBAC/ABAC boundary.

## 3. Data-flow diagram (textual)

```
Browser ──TLS──► API ──► AppServices ──► Repositories ──► Postgres(RLS)
   │                       │                  └────────────► Redis
   └──WSS──► Gateway ──► Queue ──► Workers ──► STT/LLM ports ──► (self-hosted | cloud)
                                   └──► Object Storage (encrypted, signed URLs)
```

## 4. STRIDE analysis (selected, high-priority)

### Spoofing
- **T-S1 Credential stuffing / weak auth.** → Argon2, rate limiting, lockout, MFA-ready, breach-password checks.
- **T-S2 Token theft / replay.** → short-lived access tokens, rotating refresh, token binding to UA/IP hash, revoke on logout, secure cookie/storage guidance.
- **T-S3 WebSocket auth bypass.** → authenticate WSS handshake; authorize session ownership per message.

### Tampering
- **T-T1 Tamper with signed clinical note.** → notes immutable after signing; `content_hash`; amendments are linked addenda; DB constraints + app guard.
- **T-T2 Audit log tampering.** → append-only table, hash chain, no update/delete grants, periodic export to WORM storage.
- **T-T3 Mass assignment / scope injection (client sets organization_id).** → server derives tenant from principal; DTOs exclude scoping fields; reject mismatches.

### Repudiation
- **T-R1 Doctor denies approving AI suggestion.** → every approve/edit/reject is audited with actor, timestamp, before/after, provenance link.
- **T-R2 Missing consent trail.** → consent is a first-class, audited record; recording blocked without active consent.

### Information disclosure
- **T-I1 Cross-tenant data leak.** → repository-enforced scoping + Postgres RLS (defense-in-depth); automated isolation tests in CI.
- **T-I2 Cross-patient leak in AI context.** → every AI request bound to a single patient/session id; context assembly asserts single-subject; outputs validated.
- **T-I3 PHI in logs/traces/errors.** → structured logging with redaction filter; error messages localized & PHI-free; deny-list of sensitive fields.
- **T-I4 Unsigned/over-broad file access.** → object storage private; short-lived signed URLs; per-request authorization.
- **T-I5 PHI to external AI without authorization.** → default self-hosted; cloud providers gated behind explicit config + feature flag + recorded BAA/DPA.

### Denial of service
- **T-D1 Resource exhaustion (large audio, AI floods).** → size limits, chunk caps, rate limits, queue backpressure, per-tenant quotas.
- **T-D2 Expensive AI calls.** → token/cost guards, timeouts, circuit breakers on ports, graceful degradation.

### Elevation of privilege
- **T-E1 Horizontal/vertical privilege escalation.** → centralized RBAC/ABAC checks at API + service layer; least privilege; no client-trusted roles.
- **T-E2 Nurse signs a note / auto-sign.** → `note:sign` is doctor-only; signing is a deliberate, separate action; no automated signing path exists.

## 5. AI/LLM-specific threats (OWASP LLM Top 10 mapping)

| Threat | Mitigation |
|---|---|
| LLM01 Prompt injection (via transcript/uploaded docs) | input fencing, instruction/data separation, treat content as untrusted, no tool-execution from model text, allow-listed tools only |
| LLM02 Insecure output handling | strict Pydantic schema validation; reject/quarantine invalid output; never render raw model HTML |
| LLM03 Training-data/data poisoning | self-hosted models pinned & versioned; no training on patient data without governance |
| LLM05 Improper output as fact | mandatory `is_ai_generated` labels, confidence, HITL approval before any record entry |
| LLM06 Sensitive info disclosure | single-subject context, no cross-patient data, PHI minimization in prompts, provenance hashing |
| LLM08 Excessive agency | no autonomous actions: no auto-sign, no auto-prescribe; tools are read-only/allow-listed |
| LLM09 Overreliance | uncertainty surfaced, red-flags shown, doctor must decide; fabrication grounding checks |
| Hallucinated citations/findings | grounding check against transcript spans; reject ungrounded facts/citations |

## 6. Multi-tenant & privacy specifics

- RLS policies tested per release; "Org A cannot read Org B" is a CI gate.
- De-identification pipeline for analytics/eval; never real PHI in non-prod.
- Right-to-erasure & retention workflows with audit.

## 7. Residual risks / follow-ups

- Final data-residency region pending (affects provider choice & encryption keys).
- External-AI BAA/DPA status pending; cloud path stays disabled until confirmed.
- Statutory retention periods to be confirmed for UAE.
- Penetration test + threat-model review scheduled in Phase 6.

## 8. Security testing tie-in

See [testing-strategy.md](./testing-strategy.md) — includes authz tests, tenant-isolation tests, prompt-injection
tests, dependency/container scanning (pip-audit, npm audit, Trivy), and SAST in CI.
