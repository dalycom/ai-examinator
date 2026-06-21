"""Synthetic AI evaluation harness (no real PHI)."""

from dataclasses import dataclass
from uuid import uuid4

from app.adapters.llm.port import LlmPort, TranscriptInput
from app.adapters.llm.stub_adapter import StubLlmAdapter
from app.modules.ai.eval_dataset import EVAL_CASES, EvalCase, RED_FLAG_CASES, case_count


@dataclass(frozen=True)
class CaseEvalResult:
    case_name: str
    passed: bool
    schema_validity_rate: float
    grounding_rate: float
    red_flag_present: bool
    suggestion_count: int
    missing_fact_types: frozenset[str]
    failure_reason: str = ""


@dataclass(frozen=True)
class EvalMetrics:
    total_cases: int
    passed_cases: int
    failed_cases: int
    schema_validity_rate: float
    grounding_rate: float
    red_flag_recall: float
    suggestion_count_avg: float
    passed: bool
    case_results: tuple[CaseEvalResult, ...]


def _evaluate_case(adapter: LlmPort, case: EvalCase) -> CaseEvalResult:
    segment_ids = [uuid4() for _ in case.transcript]
    transcript = [
        TranscriptInput(segment_id=segment_ids[index], speaker=line.speaker, text=line.text)
        for index, line in enumerate(case.transcript)
    ]
    result = adapter.extract_clinical_information(transcript=transcript, locale=case.locale)

    grounded = sum(1 for fact in result.facts if fact.source_segment_ref in segment_ids)
    grounding_rate = grounded / len(result.facts) if result.facts else 0.0
    fact_types = {fact.fact_type for fact in result.facts}
    missing = case.expected_fact_types - fact_types
    schema_ok = not missing
    red_flag_present = any(item.suggestion_type == "red_flag" for item in result.suggestions)
    suggestion_count = len(result.suggestions)

    red_flag_ok = red_flag_present if case.requires_red_flag else True
    passed = (
        schema_ok
        and grounding_rate >= 1.0
        and red_flag_ok
        and suggestion_count >= case.min_suggestions
    )

    failure_reason = ""
    if not passed:
        reasons: list[str] = []
        if missing:
            reasons.append(f"missing fact types: {sorted(missing)}")
        if grounding_rate < 1.0:
            reasons.append(f"grounding_rate={grounding_rate:.2f}")
        if case.requires_red_flag and not red_flag_present:
            reasons.append("missing red_flag suggestion")
        if suggestion_count < case.min_suggestions:
            reasons.append(f"suggestions={suggestion_count} < min={case.min_suggestions}")
        failure_reason = "; ".join(reasons)

    return CaseEvalResult(
        case_name=case.name,
        passed=passed,
        schema_validity_rate=1.0 if schema_ok else 0.0,
        grounding_rate=grounding_rate,
        red_flag_present=red_flag_present,
        suggestion_count=suggestion_count,
        missing_fact_types=frozenset(missing),
        failure_reason=failure_reason,
    )


def run_eval_suite(*, adapter: LlmPort | None = None, cases: tuple[EvalCase, ...] = EVAL_CASES) -> EvalMetrics:
    llm = adapter or StubLlmAdapter()
    case_results = tuple(_evaluate_case(llm, case) for case in cases)
    passed_cases = sum(1 for result in case_results if result.passed)
    failed_cases = len(case_results) - passed_cases

    schema_rate = sum(result.schema_validity_rate for result in case_results) / len(case_results)
    grounding_rate = sum(result.grounding_rate for result in case_results) / len(case_results)
    suggestion_avg = sum(result.suggestion_count for result in case_results) / len(case_results)

    red_flag_cases = [result for result, case in zip(case_results, cases, strict=True) if case.requires_red_flag]
    red_flag_hits = sum(1 for result in red_flag_cases if result.red_flag_present)
    red_flag_recall = red_flag_hits / len(red_flag_cases) if red_flag_cases else 1.0

    passed = failed_cases == 0 and red_flag_recall >= 1.0
    return EvalMetrics(
        total_cases=len(case_results),
        passed_cases=passed_cases,
        failed_cases=failed_cases,
        schema_validity_rate=schema_rate,
        grounding_rate=grounding_rate,
        red_flag_recall=red_flag_recall,
        suggestion_count_avg=suggestion_avg,
        passed=passed,
        case_results=case_results,
    )


def run_stub_eval() -> EvalMetrics:
    """Backward-compatible entry point used by CI gates."""
    return run_eval_suite(adapter=StubLlmAdapter())


def run_red_flag_eval(*, adapter: LlmPort | None = None) -> EvalMetrics:
    return run_eval_suite(adapter=adapter, cases=RED_FLAG_CASES)
