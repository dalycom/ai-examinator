"""Synthetic AI evaluation harness (no real PHI)."""

from dataclasses import dataclass
from uuid import uuid4

from app.adapters.llm.port import TranscriptInput
from app.adapters.llm.stub_adapter import StubLlmAdapter

SYNTHETIC_HEADACHE_CASE = {
    "name": "synthetic_headache_v1",
    "description": "Two-day headache consultation with red-flag screening",
    "transcript": [
        {"speaker": "doctor", "text": "Good morning. What brings you in today?"},
        {"speaker": "patient", "text": "I've had a headache for two days."},
        {"speaker": "doctor", "text": "Any fever, vision changes, or neck stiffness?"},
    ],
    "expected_fact_types": {"chief_complaint", "symptom", "relevant_negative"},
    "min_suggestions": 2,
    "requires_red_flag": True,
}


@dataclass(frozen=True)
class EvalMetrics:
    schema_validity_rate: float
    grounding_rate: float
    red_flag_present: bool
    suggestion_count: int
    passed: bool


def run_stub_eval() -> EvalMetrics:
    adapter = StubLlmAdapter()
    segment_ids = [uuid4() for _ in SYNTHETIC_HEADACHE_CASE["transcript"]]
    transcript = [
        TranscriptInput(segment_id=segment_ids[index], speaker=item["speaker"], text=item["text"])
        for index, item in enumerate(SYNTHETIC_HEADACHE_CASE["transcript"])
    ]
    result = adapter.extract_clinical_information(transcript=transcript, locale="en")

    grounded = sum(1 for fact in result.facts if fact.source_segment_ref in segment_ids)
    grounding_rate = grounded / len(result.facts) if result.facts else 0.0
    fact_types = {fact.fact_type for fact in result.facts}
    expected = set(SYNTHETIC_HEADACHE_CASE["expected_fact_types"])
    schema_ok = expected.issubset(fact_types)
    red_flag_present = any(item.suggestion_type == "red_flag" for item in result.suggestions)
    suggestion_count = len(result.suggestions)

    passed = (
        schema_ok
        and grounding_rate >= 1.0
        and red_flag_present
        and suggestion_count >= SYNTHETIC_HEADACHE_CASE["min_suggestions"]
    )
    return EvalMetrics(
        schema_validity_rate=1.0 if schema_ok else 0.0,
        grounding_rate=grounding_rate,
        red_flag_present=red_flag_present,
        suggestion_count=suggestion_count,
        passed=passed,
    )
