"""Parse and validate LLM JSON responses into typed extraction results."""

import json
import re
from typing import Any
from uuid import UUID

from app.adapters.llm.port import (
    ConceptResult,
    ConfidenceResult,
    DraftNoteResult,
    ExtractedFactResult,
    LlmExtractionResult,
    SuggestionResult,
    SupportingFactRef,
    TranscriptInput,
)


class LlmResponseParseError(ValueError):
    """Raised when LLM output cannot be parsed or fails grounding validation."""


def _strip_json_fence(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _parse_uuid(value: str, field_name: str) -> UUID:
    try:
        return UUID(str(value))
    except (ValueError, TypeError) as exc:
        msg = f"Invalid UUID for {field_name}: {value!r}"
        raise LlmResponseParseError(msg) from exc


def _confidence(level: str, score: float) -> ConfidenceResult:
    normalized = level if level in {"low", "moderate", "high"} else "moderate"
    bounded = max(0.0, min(1.0, float(score)))
    return ConfidenceResult(level=normalized, score=bounded)


def parse_extraction_response(
    raw_content: str,
    *,
    transcript: list[TranscriptInput],
    model_id: str,
    provider: str,
    prompt_version: str,
    parameters: dict[str, Any],
) -> LlmExtractionResult:
    segment_ids = {segment.segment_id for segment in transcript}
    try:
        payload = json.loads(_strip_json_fence(raw_content))
    except json.JSONDecodeError as exc:
        msg = f"LLM response is not valid JSON: {exc}"
        raise LlmResponseParseError(msg) from exc

    facts: list[ExtractedFactResult] = []
    fact_by_key: dict[str, ExtractedFactResult] = {}
    for index, item in enumerate(payload.get("facts", [])):
        segment_id = _parse_uuid(item.get("source_segment_id"), "source_segment_id")
        if segment_id not in segment_ids:
            msg = f"Fact {index} references unknown segment_id {segment_id}"
            raise LlmResponseParseError(msg)
        fact_type = item.get("fact_type", "symptom")
        if fact_type not in {
            "chief_complaint",
            "symptom",
            "onset_duration",
            "severity",
            "medical_history",
            "allergy",
            "medication",
            "vital_sign",
            "exam_finding",
            "relevant_negative",
            "risk_factor",
            "red_flag_symptom",
        }:
            fact_type = "symptom"
        fact = ExtractedFactResult(
            fact_key=str(item.get("fact_key") or f"fact_{index}"),
            fact_type=fact_type,  # type: ignore[arg-type]
            value=str(item.get("value") or ""),
            source_segment_ref=segment_id,
            confidence=_confidence(
                str(item.get("confidence_level") or "moderate"),
                float(item.get("confidence_score") or 0.7),
            ),
        )
        facts.append(fact)
        fact_by_key[fact.fact_key] = fact

    if not facts:
        msg = "LLM response contained no facts"
        raise LlmResponseParseError(msg)

    draft = payload.get("draft_note") or {}
    draft_note = DraftNoteResult(
        subjective=str(draft.get("subjective") or ""),
        objective=str(draft.get("objective") or ""),
        assessment=str(draft.get("assessment") or ""),
        plan=str(draft.get("plan") or ""),
    )

    suggestions: list[SuggestionResult] = []
    for index, item in enumerate(payload.get("suggestions", [])):
        suggestion_type = item.get("suggestion_type", "next_step")
        if suggestion_type not in {
            "differential_diagnosis",
            "missing_question",
            "recommended_exam",
            "next_step",
            "red_flag",
        }:
            suggestion_type = "next_step"
        supporting: list[SupportingFactRef] = []
        for fact_key in item.get("supporting_fact_keys") or []:
            fact = fact_by_key.get(str(fact_key))
            if fact is not None:
                supporting.append(
                    SupportingFactRef(
                        fact_key=fact.fact_key,
                        text=fact.value,
                        source_segment_ref=fact.source_segment_ref,
                    )
                )
        suggestions.append(
            SuggestionResult(
                suggestion_type=suggestion_type,  # type: ignore[arg-type]
                concept=ConceptResult(
                    label=str(item.get("concept_label") or f"Suggestion {index + 1}"),
                    code_system=item.get("concept_code_system"),
                    code=item.get("concept_code"),
                ),
                supporting_facts=supporting,
                missing_information=[str(v) for v in item.get("missing_information") or []],
                red_flag_warnings=[str(v) for v in item.get("red_flag_warnings") or []],
                confidence=_confidence(
                    str(item.get("confidence_level") or "moderate"),
                    float(item.get("confidence_score") or 0.7),
                ),
                uncertainty_notes=str(item.get("uncertainty_notes") or ""),
            )
        )

    return LlmExtractionResult(
        facts=facts,
        summary=str(payload.get("summary") or "AI-generated summary for clinician review."),
        draft_note=draft_note,
        suggestions=suggestions,
        model_id=model_id,
        provider=provider,  # type: ignore[arg-type]
        prompt_version=prompt_version,
        parameters=parameters,
    )
