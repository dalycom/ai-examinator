"""Phase status matrix for AI agent training roadmap."""

# AI Agent Training — Phase Completion Status

- **Last updated:** 2026-06-21
- **Repository:** https://github.com/dalycom/ai-examinator

This document distinguishes **engineering complete** (automated in repo/CI) from **operational complete** (requires clinicians, legal, or live infrastructure).

---

## Summary

| Phase | Engineering | Operational | Overall |
|---|---|---|---|
| **Phase 1** — Synthetic evaluation (weeks 1–4) | ✅ Complete | ✅ Complete | ✅ Complete |
| **Phase 2** — Self-hosted clinical LLM (weeks 3–6) | ✅ Complete | ⏳ Pending live model | 🟡 Partial |
| **Phase 3** — HITL validation (weeks 7–8) | ✅ Complete | ⏳ Pending clinician UAT | 🟡 Partial |
| **Phase 4** — Pilot readiness | ✅ Complete | ⏳ Pending sign-offs | 🟡 Partial |

---

## Phase 1 — Synthetic evaluation (weeks 1–4)

| Task | Status | Evidence |
|---|---|---|
| Expand eval dataset to 50+ cases | ✅ | **71 cases** in `backend/app/modules/ai/eval_dataset.py` |
| Specialty scenarios (cardiology, pediatrics, oncology, etc.) | ✅ | Tags: oncology, neurology, rheumatology, dermatology, ob_gyn, … |
| Multilingual EN/AR/FR cases | ✅ | 15+ multilingual cases |
| Edge cases (injection, multi-speaker) | ✅ | `synthetic_edge_*` cases |
| CI eval gates | ✅ | `python -m app.scripts.run_ai_eval` in CI |
| Persist results to `eval_run` | ✅ | `--persist` flag + `seed_ai_training.py` |

---

## Phase 2 — Self-hosted clinical LLM (weeks 3–6)

| Task | Status | Evidence |
|---|---|---|
| `LocalLlmAdapter` OpenAI-compatible HTTP client | ✅ | `backend/app/adapters/llm/local_adapter.py` |
| JSON schema validation + grounding checks | ✅ | `response_parser.py` |
| **Meditron 7B/70B presets** | ✅ | `LLM_MODEL_PRESET=meditron-7b` |
| **BioMistral 7B presets** (Ollama + vLLM) | ✅ | `LLM_MODEL_PRESET=biomistral-7b` |
| Prompt version pinning (v2) | ✅ | `seed_ai_training.py` seeds Meditron/BioMistral prompt versions |
| Live model passes all 71 eval cases | ⏳ | Requires GPU + `run_ai_eval --provider configured` |
| Celery async extraction at scale | ✅ | Config flag `AI_USE_CELERY_EXTRACTION` (off by default locally) |

### Enable Meditron (Ollama)

```bash
ollama pull meditron:7b
```

```env
LLM_PROVIDER=local
LLM_MODEL_PRESET=meditron-7b
LLM_ENDPOINT_URL=http://host.docker.internal:11434
```

### Enable BioMistral (Ollama)

```bash
ollama pull biomistral:7b
```

```env
LLM_PROVIDER=local
LLM_MODEL_PRESET=biomistral-7b
```

Validate:

```bash
docker compose exec backend python -m app.scripts.run_ai_eval --provider configured --verbose
```

---

## Phase 3 — HITL validation (weeks 7–8)

| Task | Status | Evidence |
|---|---|---|
| Per-patient consultation workflow in product | ✅ | Patient → consultation → consent → extract → review → sign |
| AI outputs labeled as suggestions | ✅ | `test_hitl_validation.py::test_hitl_s1_*` |
| Red flags reviewable | ✅ | `test_hitl_s2_*` |
| Consent required before extraction | ✅ | `test_hitl_v2_*` |
| No auto-sign from AI | ✅ | `test_hitl_s5_*` |
| Approve/reject/edit audited | ✅ | `test_hitl_v4_v5_*` + `test_ai.py` |
| Clinician UAT (2+ clinicians) | ⏳ | [clinical-validation-checklist.md](./clinical-validation-checklist.md) — manual sign-off |
| Arabic RTL clinical workflow validated by clinicians | ⏳ | Manual UAT |

---

## Phase 4 — Pilot readiness

| Task | Status | Evidence |
|---|---|---|
| DPIA + privacy notice drafted | ✅ | `docs/compliance/` |
| Pilot deployment guide | ✅ | `docs/pilot-deployment-guide.md` |
| Clinical validation checklist | ✅ | `docs/clinical-validation-checklist.md` |
| Automated engineering readiness script | ✅ | `python -m app.scripts.run_pilot_readiness` |
| Security headers + rate limiting | ✅ | Phase 6 |
| Load smoke + DR scripts | ✅ | `scripts/load_smoke.py`, `scripts/dr_*.sh` |
| DPIA signed off | ⏳ | Legal/clinical lead |
| Penetration test | ⏳ | External vendor |
| Controlled pilot executed | ⏳ | Per pilot guide |

---

## Commands

```bash
# Phase 1 — eval gates (71 cases)
docker compose exec backend python -m app.scripts.run_ai_eval

# Seed dataset + prompt versions, persist eval run
docker compose exec backend python -m app.scripts.seed_ai_training
docker compose exec backend python -m app.scripts.run_ai_eval --persist

# Phase 2 — live Meditron/BioMistral eval
docker compose exec backend python -m app.scripts.run_ai_eval --provider configured --verbose

# Phase 3 — automated HITL tests
docker compose exec backend pytest tests/test_hitl_validation.py -q

# Phase 4 — engineering readiness
docker compose exec backend python -m app.scripts.run_pilot_readiness
```

---

## What you still need to do manually

1. **Pull and run Meditron or BioMistral** on a GPU host; run `--provider configured` eval until all 71 cases pass.
2. **Complete clinician UAT** with two independent clinicians using the clinical validation checklist.
3. **Obtain DPIA / legal sign-off** before processing real patient data.
4. **Execute controlled pilot** per the pilot deployment guide.
