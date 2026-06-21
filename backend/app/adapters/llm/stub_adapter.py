import re

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

_DENIAL_PATTERN = re.compile(
    r"\b(no|not|none|never|without|pas de|pas d'|non|aucun|ne\s+\w+\s+pas|لا)\b",
    re.IGNORECASE,
)
_DURATION_PATTERN = re.compile(
    r"(?:"
    r"\d+\s*(?:minute|minutes|hour|hours|day|days|week|weeks|month|months|year|years)"
    r"|(?:one|two|three|four|five|six|seven|eight|nine|ten|\d+)\s+"
    r"(?:minute|minutes|hour|hours|day|days|week|weeks|month|months|year|years)"
    r"|since yesterday|since last night|this morning|ten minutes ago|45 minutes ago|two hours ago|today"
    r"|ten days ago|three hours|two minutes|ce matin|deux minutes|شهرين"
    r"|depuis (?:une semaine|hier|\d+)"
    r"|depuis une semaine|depuis hier"
    r"|منذ (?:أسبوع|يوم|أمس|\d+)"
    r")",
    re.IGNORECASE,
)
_MEDICATION_PATTERN = re.compile(
    r"\b(metformin|lisinopril|warfarin|aspirin|amoxicillin|methylphenidate|tiotropium|"
    r"inhaler|metformine|penicillin|ibuprofen|sleeping pill)\b",
    re.IGNORECASE,
)
_ALLERGY_PATTERN = re.compile(
    r"\b(allerg(y|ies)|penicillin|rash|anaphylaxis|peanut|peanuts|hives)\b",
    re.IGNORECASE,
)
_VITAL_PATTERN = re.compile(r"\b(blood pressure|bp|160|140/\d+|hypertension|glycémies|sugar)\b", re.IGNORECASE)
_EXAM_PATTERN = re.compile(
    r"\b(swollen|swelling|rash|blister|blisters|red|tender|wheez|drooped|slurred|scaly|plaques|"
    r"mole|knuckles|bruising|petechiae|tick)\b",
    re.IGNORECASE,
)
_HISTORY_PATTERN = re.compile(r"\b(last visit|prior|history|discussed|follow-up|follow up)\b", re.IGNORECASE)


class StubLlmAdapter(LlmPort):
    """Deterministic transcript-aware synthetic outputs for dev, demo, and CI eval gates."""

    def extract_clinical_information(
        self,
        *,
        transcript: list[TranscriptInput],
        locale: str = "en",
    ) -> LlmExtractionResult:
        if not transcript:
            msg = "transcript must not be empty"
            raise ValueError(msg)

        patient_segments = [segment for segment in transcript if segment.speaker == "patient"]
        primary_patient = patient_segments[0] if patient_segments else transcript[0]
        combined_patient = " ".join(segment.text for segment in patient_segments).strip()
        combined_all = " ".join(segment.text for segment in transcript).strip()

        facts: list[ExtractedFactResult] = []
        fact_index = 0

        def add_fact(fact_type: str, value: str, segment: TranscriptInput, confidence: float = 0.85) -> None:
            nonlocal fact_index
            fact_index += 1
            facts.append(
                ExtractedFactResult(
                    fact_key=f"{fact_type}_{fact_index}",
                    fact_type=fact_type,  # type: ignore[arg-type]
                    value=value[:500],
                    source_segment_ref=segment.segment_id,
                    confidence=ConfidenceResult(level="high" if confidence >= 0.8 else "moderate", score=confidence),
                )
            )

        add_fact("chief_complaint", primary_patient.text, primary_patient, 0.92)
        add_fact("symptom", primary_patient.text, primary_patient, 0.9)

        duration_match = _DURATION_PATTERN.search(combined_all)
        if duration_match:
            add_fact("onset_duration", duration_match.group(0).strip(), primary_patient, 0.82)
        elif re.search(r"\b(for|depuis|منذ)\b", combined_all, re.IGNORECASE):
            add_fact("onset_duration", "Duration referenced in patient narrative", primary_patient, 0.7)

        if _MEDICATION_PATTERN.search(combined_all):
            med_match = _MEDICATION_PATTERN.search(combined_all)
            assert med_match is not None
            add_fact("medication", med_match.group(0), primary_patient, 0.88)

        if _ALLERGY_PATTERN.search(combined_all):
            allergy_match = _ALLERGY_PATTERN.search(combined_all)
            assert allergy_match is not None
            add_fact("allergy", allergy_match.group(0), primary_patient, 0.9)

        if _VITAL_PATTERN.search(combined_all):
            vital_match = _VITAL_PATTERN.search(combined_all)
            assert vital_match is not None
            add_fact("vital_sign", vital_match.group(0), primary_patient, 0.8)

        if _EXAM_PATTERN.search(combined_all):
            exam_match = _EXAM_PATTERN.search(combined_all)
            assert exam_match is not None
            add_fact("exam_finding", exam_match.group(0), primary_patient, 0.78)

        for doctor_segment in (segment for segment in transcript if segment.speaker == "doctor"):
            if _HISTORY_PATTERN.search(doctor_segment.text) and patient_segments:
                add_fact("medical_history", doctor_segment.text[:200], doctor_segment, 0.75)
                break

        for index, segment in enumerate(transcript):
            if segment.speaker != "doctor" or "?" not in segment.text:
                continue
            next_segments = transcript[index + 1 : index + 3]
            responder = next((item for item in next_segments if item.speaker in {"patient", "family"}), None)
            if responder is None:
                continue
            if _DENIAL_PATTERN.search(responder.text):
                add_fact(
                    "relevant_negative",
                    f"No concerning feature reported when asked: {segment.text[:120]}",
                    responder,
                    0.76,
                )

        if not any(fact.fact_type == "relevant_negative" for fact in facts):
            doctor_segment = next((segment for segment in transcript if segment.speaker == "doctor"), transcript[-1])
            add_fact(
                "relevant_negative",
                "Screening questions documented; no acute negatives explicitly captured in transcript.",
                doctor_segment,
                0.65,
            )

        summary = (
            f"Patient presentation summarized from transcript ({len(transcript)} segments). "
            "AI-generated summary for clinician review — not a confirmed diagnosis."
        )
        draft_note = DraftNoteResult(
            subjective=combined_patient[:400] or primary_patient.text,
            objective="Vitals and exam findings to be confirmed by clinician (synthetic demo).",
            assessment="Preliminary AI draft differential — requires clinician confirmation.",
            plan="Complete history, targeted exam, and return precautions as clinically indicated.",
        )

        fact_refs = [
            SupportingFactRef(
                fact_key=fact.fact_key,
                text=fact.value,
                source_segment_ref=fact.source_segment_ref,
            )
            for fact in facts[:2]
        ]
        suggestions = [
            SuggestionResult(
                suggestion_type="missing_question",
                concept=ConceptResult(label="Any additional red-flag symptoms not yet discussed?"),
                supporting_facts=fact_refs[:1],
                missing_information=["Red-flag symptom review"],
                confidence=ConfidenceResult(level="moderate", score=0.68),
                uncertainty_notes="AI suggestion only — clinician must confirm.",
            ),
            SuggestionResult(
                suggestion_type="differential_diagnosis",
                concept=ConceptResult(label="Broad differential based on presenting complaint"),
                supporting_facts=fact_refs,
                confidence=ConfidenceResult(level="moderate", score=0.71),
                uncertainty_notes="AI suggestion only — clinician must confirm diagnosis.",
            ),
            SuggestionResult(
                suggestion_type="recommended_exam",
                concept=ConceptResult(label="Targeted physical examination"),
                supporting_facts=fact_refs[:1],
                confidence=ConfidenceResult(level="moderate", score=0.65),
            ),
            SuggestionResult(
                suggestion_type="red_flag",
                concept=ConceptResult(label="Emergent symptoms requiring immediate clinician judgment"),
                supporting_facts=[],
                red_flag_warnings=[
                    "Consider emergent evaluation if sudden severe symptoms, neurological deficit, "
                    "or hemodynamic instability are present."
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
            model_id="stub-clinical-v2",
            provider="stub",
            prompt_version="stub-extraction-v2",
            parameters={"locale": locale, "temperature": 0.0, "transcript_segments": len(transcript)},
        )
