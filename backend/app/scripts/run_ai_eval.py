"""Run synthetic AI evaluation gates (Phase 6 sign-off)."""

import json
import sys

from app.modules.ai.eval import run_stub_eval


def main() -> int:
    metrics = run_stub_eval()
    payload = {
        "schema_validity_rate": metrics.schema_validity_rate,
        "grounding_rate": metrics.grounding_rate,
        "red_flag_present": metrics.red_flag_present,
        "suggestion_count": metrics.suggestion_count,
        "passed": metrics.passed,
    }
    print(json.dumps(payload, indent=2))
    if not metrics.passed:
        print("AI evaluation gates FAILED", file=sys.stderr)
        return 1
    print("AI evaluation gates PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
