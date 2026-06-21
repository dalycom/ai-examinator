"""Automated pilot readiness checks (engineering gates)."""

import json
import sys

from app.adapters.llm.model_presets import list_model_presets
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.modules.ai.eval import run_eval_suite
from app.modules.ai.eval_dataset import case_count
from app.modules.ai.eval_persistence import latest_eval_run


def main() -> int:
    settings = get_settings()
    metrics = run_eval_suite()
    db = SessionLocal()
    try:
        last_run = latest_eval_run(db)
    finally:
        db.close()

    checks = {
        "eval_dataset_cases_gte_70": case_count() >= 70,
        "stub_eval_gates_pass": metrics.passed,
        "schema_validity_100": metrics.schema_validity_rate >= 1.0,
        "grounding_rate_100": metrics.grounding_rate >= 1.0,
        "red_flag_recall_100": metrics.red_flag_recall >= 1.0,
        "ai_allow_external_phi_false": settings.ai_allow_external_phi is False,
        "clinical_model_presets_available": len(list_model_presets()) >= 4,
    }

    informational = {
        "eval_run_persisted": last_run is not None,
        "latest_eval_run_passed": bool(last_run and last_run.passed_gates),
    }

    operational_pending = {
        "dpia_signed_off": False,
        "clinical_validation_checklist_signed": False,
        "configured_model_eval_passed": False,
        "penetration_test_complete": False,
        "controlled_pilot_executed": False,
    }

    engineering_ready = all(checks.values())
    payload = {
        "engineering_ready": engineering_ready,
        "checks": checks,
        "informational": informational,
        "operational_pending": operational_pending,
        "eval_metrics": {
            "total_cases": metrics.total_cases,
            "passed_cases": metrics.passed_cases,
            "failed_cases": metrics.failed_cases,
        },
        "latest_eval_run_id": str(last_run.id) if last_run else None,
        "note": (
            "Engineering gates can pass in CI. Operational items require clinician sign-off, "
            "live model eval (--provider configured), and pilot execution."
        ),
    }
    print(json.dumps(payload, indent=2))

    if not engineering_ready:
        print("Pilot readiness: ENGINEERING gates FAILED", file=sys.stderr)
        return 1
    print("Pilot readiness: ENGINEERING gates PASSED (operational items still pending)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
