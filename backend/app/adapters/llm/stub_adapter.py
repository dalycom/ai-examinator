from app.adapters.llm.port import (
    ConceptResult,
    ConfidenceResult,
    DraftNoteResult,
    ExtractedFactResult,
    LlmExtractionResult,
    LlmPort,
    SuggestionResult,
    SupportingFactRef,
    TranscriptInput,
)


class StubLlmAdapter(LlmPort):
    """Deterministic synthetic AI outputs grounded in transcript segments (dev/demo only)."""

    def extract_clinical_information(
        self,
        *,
        transcript: list[TranscriptInput],
        locale: str = "en",
    ) -> LlmExtractionResult:
        if not transcript:
            msg = "transcript must not be empty"
            raise ValueError(msg)

        patient_segment = next((segment for segment in transcript if segment.speaker == "patient"), transcript[0])
        doctor_segment = next((segment for segment in transcript if segment.speaker == "doctor"), transcript[-1])

        facts = [
            ExtractedFactResult(
                fact_key="cc_headache",
                fact_type="chief_complaint",
                value="Headache for two days",
                source_segment_ref=patient_segment.segment_id,
                confidence=ConfidenceResult(level="high", score=0.92),
            ),
            ExtractedFactResult(
                fact_key="symptom_headache",
                fact_type="symptom",
                value="Headache",
                source_segment_ref=patient_segment.segment_id,
                confidence=ConfidenceResult(level="high", score=0.9),
            ),
            ExtractedFactResult(
                fact_key="neg_fever",
                fact_type="relevant_negative",
                value="No fever reported when asked",
                source_segment_ref=doctor_segment.segment_id,
                confidence=ConfidenceResult(level="moderate", score=0.75),
            ),
        ]

        summary = (
            "Patient reports a two-day headache. Doctor screened for red flags including fever, "
            "vision changes, and neck stiffness. This is an AI-generated summary for clinician review."
        )

        draft_note = DraftNoteResult(
            subjective="Two-day headache. No fever reported when asked.",
            objective="Alert and oriented on exam (synthetic demo).",
            assessment="Tension-type headache likely — AI draft for review.",
            plan="Hydration, rest, return if worsening or new neurological symptoms.",
        )

        suggestions = [
            SuggestionResult(
                suggestion_type="missing_question",
                concept=ConceptResult(label="Vision changes or photophobia?"),
                supporting_facts=[
                    SupportingFactRef(
                        fact_key="symptom_headache",
                        text="Headache",
                        source_segment_ref=patient_segment.segment_id,
                    )
                ],
                missing_information=["Vision changes", "Photophobia"],
                confidence=ConfidenceResult(level="moderate", score=0.68),
                uncertainty_notes="Headache red-flag screening incomplete in transcript.",
            ),
            SuggestionResult(
                suggestion_type="differential_diagnosis",
                concept=ConceptResult(label="Tension-type headache", code_system="ICD-10", code="G44.209"),
                supporting_facts=[
                    SupportingFactRef(
                        fact_key="cc_headache",
                        text="Headache for two days",
                        source_segment_ref=patient_segment.segment_id,
                    )
                ],
                confidence=ConfidenceResult(level="moderate", score=0.71),
                uncertainty_notes="AI suggestion only — clinician must confirm diagnosis.",
            ),
            SuggestionResult(
                suggestion_type="recommended_exam",
                concept=ConceptResult(label="Blood pressure measurement"),
                supporting_facts=[
                    SupportingFactRef(
                        fact_key="symptom_headache",
                        text="Headache",
                        source_segment_ref=patient_segment.segment_id,
                    )
                ],
                confidence=ConfidenceResult(level="moderate", score=0.65),
            ),
            SuggestionResult(
                suggestion_type="red_flag",
                concept=ConceptResult(label="Sudden severe headache or neurological deficit"),
                supporting_facts=[],
                red_flag_warnings=[
                    "Consider emergent evaluation if sudden onset, focal deficit, or altered mental status."
                ],
                confidence=ConfidenceResult(level="high", score=0.85),
                uncertainty_notes="High-sensitivity red-flag reminder for clinician review.",
            ),
        ]

        return LlmExtractionResult(
            facts=facts,
            summary=summary,
            draft_note=draft_note,
            suggestions=suggestions,
            model_id="stub-clinical-v1",
            provider="stub",
            prompt_version="stub-extraction-v1",
            parameters={"locale": locale, "temperature": 0.0},
        )
