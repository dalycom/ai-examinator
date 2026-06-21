"""Run synthetic AI evaluation gates (Phase 6 sign-off)."""

import argparse
import json
import sys

from app.adapters.llm import get_llm_adapter
from app.adapters.llm.stub_adapter import StubLlmAdapter
from app.modules.ai.eval import run_eval_suite, run_red_flag_eval
from app.modules.ai.eval_dataset import case_count


def main() -> int:
    parser = argparse.ArgumentParser(description="Run AI Examinator synthetic evaluation gates")
    parser.add_argument(
        "--provider",
        choices=("stub", "configured"),
        default="stub",
        help="stub=deterministic CI gates; configured=use LLM_PROVIDER from environment",
    )
    parser.add_argument(
        "--red-flags-only",
        action="store_true",
        help="Run only cases that require red_flag suggestions",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-case failures",
    )
    parser.add_argument(
        "--persist",
        action="store_true",
        help="Persist eval results to eval_run table (requires DB)",
    )
    args = parser.parse_args()

    adapter = get_llm_adapter() if args.provider == "configured" else StubLlmAdapter()
    metrics = run_red_flag_eval(adapter=adapter) if args.red_flags_only else run_eval_suite(adapter=adapter)

    from app.adapters.llm.settings_resolver import resolve_llm_config
    from app.core.config import get_settings

    llm = resolve_llm_config(get_settings())
    payload = {
        "dataset_size": case_count(),
        "total_cases": metrics.total_cases,
        "passed_cases": metrics.passed_cases,
        "failed_cases": metrics.failed_cases,
        "schema_validity_rate": round(metrics.schema_validity_rate, 4),
        "grounding_rate": round(metrics.grounding_rate, 4),
        "red_flag_recall": round(metrics.red_flag_recall, 4),
        "suggestion_count_avg": round(metrics.suggestion_count_avg, 2),
        "passed": metrics.passed,
        "provider_mode": args.provider,
        "model_id": llm.model_id,
        "preset": llm.preset_name,
        "prompt_version": llm.prompt_version,
    }
    print(json.dumps(payload, indent=2))

    if args.persist:
        from app.core.database import SessionLocal
        from app.modules.ai.eval_persistence import persist_eval_run

        db = SessionLocal()
        try:
            run = persist_eval_run(db, metrics, provider_mode=args.provider)
            print(f"Persisted eval_run id={run.id}", file=sys.stderr)
        finally:
            db.close()

    if args.verbose and metrics.failed_cases:
        print("\nFailed cases:", file=sys.stderr)
        for result in metrics.case_results:
            if not result.passed:
                print(f"  - {result.case_name}: {result.failure_reason}", file=sys.stderr)

    if not metrics.passed:
        print("AI evaluation gates FAILED", file=sys.stderr)
        return 1
    print("AI evaluation gates PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
