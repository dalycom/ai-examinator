"""Persist synthetic evaluation runs to the eval_run table."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.adapters.llm.settings_resolver import resolve_llm_config
from app.core.config import get_settings
from app.modules.ai.eval import EvalMetrics
from app.modules.ai.models import EvalDataset, EvalRun


DATASET_NAME = "synthetic_eval_v1"


def ensure_eval_dataset(db: Session) -> EvalDataset:
    from app.modules.ai.eval_dataset import EVAL_CASES

    dataset = db.query(EvalDataset).filter(EvalDataset.name == DATASET_NAME).one_or_none()
    items = [
        {
            "name": case.name,
            "description": case.description,
            "locale": case.locale,
            "requires_red_flag": case.requires_red_flag,
            "expected_fact_types": sorted(case.expected_fact_types),
            "tags": sorted(case.tags),
        }
        for case in EVAL_CASES
    ]
    if dataset is None:
        dataset = EvalDataset(
            name=DATASET_NAME,
            description="Synthetic clinical extraction evaluation library (no PHI).",
            items=items,
            is_synthetic=True,
        )
        db.add(dataset)
        db.flush()
        return dataset

    dataset.items = items
    dataset.description = "Synthetic clinical extraction evaluation library (no PHI)."
    db.flush()
    return dataset


def persist_eval_run(
    db: Session,
    metrics: EvalMetrics,
    *,
    provider_mode: str,
) -> EvalRun:
    dataset = ensure_eval_dataset(db)
    llm = resolve_llm_config(get_settings())
    run = EvalRun(
        dataset_id=dataset.id,
        prompt_version=llm.prompt_version,
        passed_gates=metrics.passed,
        metrics={
            "provider_mode": provider_mode,
            "model_id": llm.model_id,
            "preset": llm.preset_name,
            "total_cases": metrics.total_cases,
            "passed_cases": metrics.passed_cases,
            "failed_cases": metrics.failed_cases,
            "schema_validity_rate": metrics.schema_validity_rate,
            "grounding_rate": metrics.grounding_rate,
            "red_flag_recall": metrics.red_flag_recall,
            "suggestion_count_avg": metrics.suggestion_count_avg,
            "failed_case_names": [result.case_name for result in metrics.case_results if not result.passed],
        },
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def latest_eval_run(db: Session) -> EvalRun | None:
    return db.query(EvalRun).order_by(EvalRun.created_at.desc()).first()
