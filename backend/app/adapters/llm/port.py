from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import UUID


ConfidenceLevel = Literal["low", "moderate", "high"]
SuggestionType = Literal[
    "differential_diagnosis",
    "missing_question",
    "recommended_exam",
    "next_step",
    "red_flag",
]
FactType = Literal[
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
]


@dataclass(frozen=True)
class TranscriptInput:
    segment_id: UUID
    speaker: str
    text: str


@dataclass(frozen=True)
class ConfidenceResult:
    level: ConfidenceLevel
    score: float


@dataclass(frozen=True)
class SupportingFactRef:
    fact_key: str
    text: str
    source_segment_ref: UUID


@dataclass(frozen=True)
class ConceptResult:
    label: str
    code_system: str | None = None
    code: str | None = None


@dataclass(frozen=True)
class ExtractedFactResult:
    fact_type: FactType
    value: str
    source_segment_ref: UUID
    confidence: ConfidenceResult
    fact_key: str


@dataclass(frozen=True)
class SuggestionResult:
    suggestion_type: SuggestionType
    concept: ConceptResult
    supporting_facts: list[SupportingFactRef]
    missing_information: list[str] = field(default_factory=list)
    conflicting_information: list[str] = field(default_factory=list)
    confidence: ConfidenceResult = field(default_factory=lambda: ConfidenceResult(level="moderate", score=0.7))
    red_flag_warnings: list[str] = field(default_factory=list)
    source_references: list[dict[str, Any]] = field(default_factory=list)
    uncertainty_notes: str = ""


@dataclass(frozen=True)
class DraftNoteResult:
    subjective: str
    objective: str
    assessment: str
    plan: str


@dataclass(frozen=True)
class LlmExtractionResult:
    facts: list[ExtractedFactResult]
    summary: str
    draft_note: DraftNoteResult
    suggestions: list[SuggestionResult]
    model_id: str
    provider: Literal["self_hosted", "cloud", "stub"]
    prompt_version: str
    parameters: dict[str, Any]


class LlmPort:
    def extract_clinical_information(
        self,
        *,
        transcript: list[TranscriptInput],
        locale: str = "en",
    ) -> LlmExtractionResult:
        raise NotImplementedError
