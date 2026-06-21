import json
from uuid import uuid4

import httpx
import pytest

from app.adapters.llm.local_adapter import LocalLlmAdapter
from app.adapters.llm.port import TranscriptInput
from app.adapters.llm.response_parser import LlmResponseParseError, parse_extraction_response
from app.adapters.llm.stub_adapter import StubLlmAdapter
from app.modules.ai.eval import run_eval_suite
from app.modules.ai.eval_dataset import EVAL_CASES, case_count


def test_eval_dataset_has_minimum_cases() -> None:
    assert case_count() >= 50


def test_stub_eval_suite_passes_all_cases() -> None:
    metrics = run_eval_suite(adapter=StubLlmAdapter())
    assert metrics.passed is True
    assert metrics.failed_cases == 0
    assert metrics.red_flag_recall == 1.0


def test_stub_adapter_grounds_all_facts() -> None:
    segment_id = uuid4()
    transcript = [
        TranscriptInput(segment_id=segment_id, speaker="patient", text="Chest pain for one hour."),
        TranscriptInput(segment_id=uuid4(), speaker="doctor", text="Any shortness of breath?"),
        TranscriptInput(segment_id=uuid4(), speaker="patient", text="No shortness of breath."),
    ]
    result = StubLlmAdapter().extract_clinical_information(transcript=transcript, locale="en")
    assert all(fact.source_segment_ref in {item.segment_id for item in transcript} for fact in result.facts)
    assert any(item.suggestion_type == "red_flag" for item in result.suggestions)


def test_response_parser_validates_segment_ids() -> None:
    segment_id = uuid4()
    transcript = [TranscriptInput(segment_id=segment_id, speaker="patient", text="Headache.")]
    raw = json.dumps(
        {
            "facts": [
                {
                    "fact_key": "cc",
                    "fact_type": "chief_complaint",
                    "value": "Headache",
                    "source_segment_id": str(uuid4()),
                    "confidence_level": "high",
                    "confidence_score": 0.9,
                }
            ],
            "summary": "Summary",
            "draft_note": {"subjective": "s", "objective": "o", "assessment": "a", "plan": "p"},
            "suggestions": [],
        }
    )
    with pytest.raises(LlmResponseParseError):
        parse_extraction_response(
            raw,
            transcript=transcript,
            model_id="test",
            provider="self_hosted",
            prompt_version="v1",
            parameters={},
        )


def test_local_adapter_parses_openai_compatible_response(monkeypatch: pytest.MonkeyPatch) -> None:
    segment_id = uuid4()
    transcript = [TranscriptInput(segment_id=segment_id, speaker="patient", text="Headache for two days.")]

    llm_json = {
        "facts": [
            {
                "fact_key": "cc_headache",
                "fact_type": "chief_complaint",
                "value": "Headache for two days",
                "source_segment_id": str(segment_id),
                "confidence_level": "high",
                "confidence_score": 0.92,
            },
            {
                "fact_key": "symptom_headache",
                "fact_type": "symptom",
                "value": "Headache",
                "source_segment_id": str(segment_id),
                "confidence_level": "high",
                "confidence_score": 0.9,
            },
            {
                "fact_key": "neg_fever",
                "fact_type": "relevant_negative",
                "value": "No fever reported",
                "source_segment_id": str(segment_id),
                "confidence_level": "moderate",
                "confidence_score": 0.75,
            },
        ],
        "summary": "AI summary for review.",
        "draft_note": {
            "subjective": "Headache",
            "objective": "Pending exam",
            "assessment": "Draft only",
            "plan": "Supportive care",
        },
        "suggestions": [
            {
                "suggestion_type": "red_flag",
                "concept_label": "Sudden severe headache",
                "supporting_fact_keys": ["cc_headache"],
                "red_flag_warnings": ["Consider emergent evaluation"],
                "confidence_level": "high",
                "confidence_score": 0.85,
            },
            {
                "suggestion_type": "missing_question",
                "concept_label": "Vision changes?",
                "supporting_fact_keys": ["symptom_headache"],
                "confidence_level": "moderate",
                "confidence_score": 0.7,
            },
        ],
    }

    class MockHttpClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self) -> "MockHttpClient":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def post(self, url: str, **kwargs: object) -> httpx.Response:
            assert str(url).endswith("/chat/completions")
            request = httpx.Request("POST", url)
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": json.dumps(llm_json)}}]},
                request=request,
            )

    monkeypatch.setenv("LLM_ENDPOINT_URL", "http://llm.test/v1")
    monkeypatch.setenv("LLM_MODEL_ID", "clinical-llm-v1")
    monkeypatch.setattr("app.adapters.llm.local_adapter.httpx.Client", MockHttpClient)
    from app.core.config import get_settings

    get_settings.cache_clear()

    result = LocalLlmAdapter().extract_clinical_information(transcript=transcript, locale="en")
    assert result.provider == "self_hosted"
    assert len(result.facts) == 3
    assert any(item.suggestion_type == "red_flag" for item in result.suggestions)


def test_eval_cases_cover_specialties() -> None:
    tags = {tag for case in EVAL_CASES for tag in case.tags}
    assert "red_flag" in tags
    assert "multilingual" in tags
    assert "edge_case" in tags
    assert "pediatrics" in tags
