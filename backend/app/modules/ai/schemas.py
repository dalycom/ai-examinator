from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


ConfidenceLevel = Literal["low", "moderate", "high"]
SuggestionType = Literal[
    "differential_diagnosis",
    "missing_question",
    "recommended_exam",
    "next_step",
    "red_flag",
]
DecisionStatus = Literal["pending", "approved", "edited", "rejected"]


class ProvenanceBlock(BaseModel):
    model_id: str
    provider: str
    prompt_version: str
    input_hash: str
    generated_at: datetime
    parameters: dict[str, Any] = Field(default_factory=dict)
    latency_ms: int | None = None


class ConceptBlock(BaseModel):
    label: str
    code_system: str | None = None
    code: str | None = None


class SupportingFactBlock(BaseModel):
    fact_id: UUID | None = None
    text: str
    source_segment_ref: UUID


class ConfidenceBlock(BaseModel):
    level: ConfidenceLevel
    score: float = Field(ge=0.0, le=1.0)


class ExtractedFactResponse(BaseModel):
    id: UUID
    session_id: UUID
    fact_type: str
    value: str
    source_segment_ref: UUID
    confidence: ConfidenceBlock
    status: str
    is_ai_generated: bool = True
    provenance: ProvenanceBlock


class SuggestionResponse(BaseModel):
    id: UUID
    session_id: UUID
    suggestion_type: SuggestionType
    concept: ConceptBlock
    supporting_facts: list[SupportingFactBlock]
    missing_information: list[str]
    conflicting_information: list[str]
    confidence: ConfidenceBlock
    red_flag_warnings: list[str]
    source_references: list[dict[str, Any]]
    uncertainty_notes: str | None
    is_ai_generated: bool = True
    provenance: ProvenanceBlock
    decision: dict[str, Any]


class ExtractionRunResponse(BaseModel):
    id: UUID
    session_id: UUID
    status: str
    error_message: str | None
    completed_at: datetime | None


class FactsListResponse(BaseModel):
    run: ExtractionRunResponse | None
    facts: list[ExtractedFactResponse]


class SummaryResponse(BaseModel):
    is_ai_generated: bool = True
    summary: str | None
    run_status: str | None
    provenance: ProvenanceBlock | None = None


class SuggestionsListResponse(BaseModel):
    suggestions: list[SuggestionResponse]


class SuggestionDecisionRequest(BaseModel):
    decision: Literal["approved", "edited", "rejected"]
    edited_value: dict[str, Any] | None = None
    reason: str | None = None

    @field_validator("edited_value")
    @classmethod
    def require_edit_payload(cls, value: dict[str, Any] | None, info: Any) -> dict[str, Any] | None:
        decision = info.data.get("decision")
        if decision == "edited" and not value:
            msg = "edited_value is required when decision is edited"
            raise ValueError(msg)
        return value
