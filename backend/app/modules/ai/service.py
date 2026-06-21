import hashlib
import json
import time
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.adapters.llm.port import TranscriptInput
from app.adapters.llm import get_llm_adapter
from app.core.config import get_settings
from app.core.database import tenant_session
from app.core.enums import DataClassification
from app.core.errors import AppError
from app.core.tenant import Principal
from app.modules.ai.governance import GovernanceService
from app.modules.ai.models import (
    AIExtractionRun,
    AIProvenance,
    AISuggestion,
    ExtractedFact,
)
from app.modules.ai.schemas import (
    ConfidenceBlock,
    ConceptBlock,
    ExtractedFactResponse,
    ExtractionRunResponse,
    FactsListResponse,
    ProvenanceBlock,
    SuggestionDecisionRequest,
    SuggestionResponse,
    SuggestionsListResponse,
    SummaryResponse,
    SupportingFactBlock,
)
from app.modules.audit.service import AuditService
from app.modules.consent.service import ConsentService
from app.modules.consultation.models import ClinicalNote, ConsultationSession, TranscriptSegment


class AIService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.audit = AuditService(db)
        self.consent = ConsentService(db)
        self.governance = GovernanceService(db)
        self.llm = get_llm_adapter()
        self.settings = get_settings()

    def enqueue_extraction(self, principal: Principal, session_id: UUID) -> ExtractionRunResponse:
        self.governance.ensure_default_flags(principal)
        if not self.governance.is_enabled(principal, "ai_extraction"):
            raise AppError(
                code="AI_DISABLED",
                message_key="errors.ai_feature_disabled",
                status_code=403,
                details={"feature": "ai_extraction"},
            )

        with tenant_session(self.db, principal.organization_id):
            session = self._get_session(principal, session_id)
            self.consent.require_scope(principal, session.patient_id, ConsentService.REQUIRED_AI_SCOPE)

            existing = self._latest_run(session_id, principal.organization_id)
            if existing is not None and existing.status in {"completed", "running", "pending"}:
                return self._run_to_response(existing)

            segments = self._load_segments(session_id, principal.organization_id)
            if not segments:
                raise AppError(
                    code="TRANSCRIPT_REQUIRED",
                    message_key="errors.transcript_required",
                    status_code=400,
                )

            run = AIExtractionRun(
                organization_id=principal.organization_id,
                session_id=session_id,
                status="pending",
                data_classification=DataClassification.PHI.value,
                created_by=principal.user_id,
                updated_by=principal.user_id,
            )
            self.db.add(run)
            self.db.flush()

        if self.settings.ai_use_celery_extraction:
            from app.workers.tasks.ai_tasks import run_ai_extraction

            run_ai_extraction.delay(str(run.id), str(principal.organization_id), str(principal.user_id))
            return self._run_to_response(run)

        self.execute_extraction_run(run.id, principal)
        refreshed = self.db.get(AIExtractionRun, run.id)
        assert refreshed is not None
        return self._run_to_response(refreshed)

    def execute_extraction_run(self, run_id: UUID, principal: Principal) -> ExtractionRunResponse:
        started = time.perf_counter()
        with tenant_session(self.db, principal.organization_id):
            run = self.db.get(AIExtractionRun, run_id)
            if run is None or run.organization_id != principal.organization_id:
                raise AppError(code="NOT_FOUND", message_key="errors.http_error", status_code=404)
            if run.status == "completed":
                return self._run_to_response(run)
            if run.status == "failed":
                raise AppError(
                    code="AI_EXTRACTION_FAILED",
                    message_key="errors.ai_extraction_failed",
                    status_code=409,
                    details={"error": run.error_message},
                )

            session = self._get_session(principal, run.session_id)
            self.consent.require_scope(principal, session.patient_id, ConsentService.REQUIRED_AI_SCOPE)
            run.status = "running"
            run.updated_by = principal.user_id
            self.db.flush()

            segments = self._load_segments(run.session_id, principal.organization_id)
            if not segments:
                run.status = "failed"
                run.error_message = "Transcript required before AI extraction"
                run.completed_at = datetime.now(UTC)
                raise AppError(
                    code="TRANSCRIPT_REQUIRED",
                    message_key="errors.transcript_required",
                    status_code=400,
                )

            return self._complete_extraction_run(
                run=run,
                session=session,
                segments=segments,
                principal=principal,
                started=started,
            )

    def mark_extraction_failed(self, run_id: UUID, organization_id: UUID, error_message: str) -> None:
        with tenant_session(self.db, organization_id):
            run = self.db.get(AIExtractionRun, run_id)
            if run is None:
                return
            run.status = "failed"
            run.error_message = error_message[:2000]
            run.completed_at = datetime.now(UTC)
            self.db.flush()

    def run_extraction(self, principal: Principal, session_id: UUID) -> ExtractionRunResponse:
        return self.enqueue_extraction(principal, session_id)

    def _complete_extraction_run(
        self,
        *,
        run: AIExtractionRun,
        session: ConsultationSession,
        segments: list[TranscriptSegment],
        principal: Principal,
        started: float,
    ) -> ExtractionRunResponse:
        session_id = run.session_id
        transcript_input = [
            TranscriptInput(
                segment_id=segment.id,
                speaker=segment.speaker,
                text=segment.corrected_text or segment.text,
            )
            for segment in segments
        ]
        input_hash = self._hash_transcript(transcript_input)
        result = self.llm.extract_clinical_information(transcript=transcript_input, locale="en")
        if result.provider == "cloud" and not self.settings.ai_allow_external_phi:
            raise AppError(
                code="AI_CLOUD_BLOCKED",
                message_key="errors.ai_cloud_blocked",
                status_code=403,
            )

        latency_ms = int((time.perf_counter() - started) * 1000)
        provenance = AIProvenance(
            organization_id=principal.organization_id,
            model_id=result.model_id,
            provider=result.provider,
            prompt_version=result.prompt_version,
            input_hash=input_hash,
            parameters=result.parameters,
            latency_ms=latency_ms,
            data_classification=DataClassification.INTERNAL.value,
            created_by=principal.user_id,
            updated_by=principal.user_id,
        )
        self.db.add(provenance)
        self.db.flush()

        segment_ids = {segment.id for segment in segments}
        fact_id_by_key: dict[str, UUID] = {}
        for fact in result.facts:
            if fact.source_segment_ref not in segment_ids:
                continue
            row = ExtractedFact(
                organization_id=principal.organization_id,
                session_id=session_id,
                extraction_run_id=run.id,
                fact_type=fact.fact_type,
                value=fact.value,
                source_segment_ref=fact.source_segment_ref,
                confidence_level=fact.confidence.level,
                confidence_score=fact.confidence.score,
                status="pending",
                provenance_id=provenance.id,
                data_classification=DataClassification.SENSITIVE_PHI.value,
                created_by=principal.user_id,
                updated_by=principal.user_id,
            )
            self.db.add(row)
            self.db.flush()
            fact_id_by_key[fact.fact_key] = row.id

        suggestions: list[AISuggestion] = []
        for suggestion in result.suggestions:
            if self.governance.is_enabled(principal, "ai_red_flags") is False and suggestion.suggestion_type == "red_flag":
                continue
            if self.governance.is_enabled(principal, "ai_suggestions") is False and suggestion.suggestion_type != "red_flag":
                continue
            grounded_support = [
                {
                    "fact_id": str(fact_id_by_key.get(item.fact_key)) if item.fact_key in fact_id_by_key else None,
                    "text": item.text,
                    "source_segment_ref": str(item.source_segment_ref),
                }
                for item in suggestion.supporting_facts
                if item.source_segment_ref in segment_ids
            ]
            if suggestion.supporting_facts and not grounded_support:
                continue
            row = AISuggestion(
                organization_id=principal.organization_id,
                session_id=session_id,
                extraction_run_id=run.id,
                suggestion_type=suggestion.suggestion_type,
                concept={
                    "label": suggestion.concept.label,
                    "code_system": suggestion.concept.code_system,
                    "code": suggestion.concept.code,
                },
                supporting_facts=grounded_support,
                missing_information=suggestion.missing_information,
                conflicting_information=suggestion.conflicting_information,
                confidence_level=suggestion.confidence.level,
                confidence_score=suggestion.confidence.score,
                red_flag_warnings=suggestion.red_flag_warnings,
                source_references=suggestion.source_references,
                uncertainty_notes=suggestion.uncertainty_notes,
                decision_status="pending",
                provenance_id=provenance.id,
                data_classification=DataClassification.PHI.value,
                created_by=principal.user_id,
                updated_by=principal.user_id,
            )
            self.db.add(row)
            suggestions.append(row)

        run.summary = result.summary
        if self.governance.is_enabled(principal, "ai_draft_note"):
            run.draft_note = {
                "subjective": result.draft_note.subjective,
                "objective": result.draft_note.objective,
                "assessment": result.draft_note.assessment,
                "plan": result.draft_note.plan,
            }
            self._apply_draft_note_suggestion(
                session,
                {
                    "subjective": result.draft_note.subjective,
                    "objective": result.draft_note.objective,
                    "assessment": result.draft_note.assessment,
                    "plan": result.draft_note.plan,
                },
                principal,
            )
        run.status = "completed"
        run.provenance_id = provenance.id
        run.completed_at = datetime.now(UTC)
        run.updated_by = principal.user_id
        self.db.flush()

        self.audit.record(
            action="ai.extract",
            organization_id=principal.organization_id,
            actor_user_id=principal.user_id,
            resource_type="consultation_session",
            resource_id=session_id,
            metadata={
                "run_id": str(run.id),
                "facts": len(result.facts),
                "suggestions": len(suggestions),
                "model_id": result.model_id,
            },
        )
        return self._run_to_response(run)

    def get_facts(self, principal: Principal, session_id: UUID) -> FactsListResponse:
        with tenant_session(self.db, principal.organization_id):
            self._get_session(principal, session_id)
            run = self._latest_run(session_id, principal.organization_id)
            if run is None:
                return FactsListResponse(run=None, facts=[])
            facts = (
                self.db.query(ExtractedFact)
                .filter(
                    ExtractedFact.extraction_run_id == run.id,
                    ExtractedFact.deleted_at.is_(None),
                )
                .order_by(ExtractedFact.created_at.asc())
                .all()
            )
            if not facts:
                return FactsListResponse(run=self._run_to_response(run), facts=[])
            provenance_rows = {
                row.id: self._provenance_to_block(row)
                for row in self.db.query(AIProvenance)
                .filter(AIProvenance.id.in_({fact.provenance_id for fact in facts}))
                .all()
            }
            return FactsListResponse(
                run=self._run_to_response(run),
                facts=[
                    self._fact_to_response(fact, provenance_rows[fact.provenance_id]) for fact in facts
                ],
            )

    def get_summary(self, principal: Principal, session_id: UUID) -> SummaryResponse:
        with tenant_session(self.db, principal.organization_id):
            self._get_session(principal, session_id)
            run = self._latest_run(session_id, principal.organization_id)
            if run is None or not run.summary:
                return SummaryResponse(summary=None, run_status=run.status if run else None)
            provenance = None
            if run.provenance_id:
                row = self.db.get(AIProvenance, run.provenance_id)
                if row is not None:
                    provenance = self._provenance_to_block(row)
            return SummaryResponse(summary=run.summary, run_status=run.status, provenance=provenance)

    def get_suggestions(self, principal: Principal, session_id: UUID) -> SuggestionsListResponse:
        with tenant_session(self.db, principal.organization_id):
            self._get_session(principal, session_id)
            run = self._latest_run(session_id, principal.organization_id)
            if run is None:
                return SuggestionsListResponse(suggestions=[])
            rows = (
                self.db.query(AISuggestion)
                .filter(
                    AISuggestion.extraction_run_id == run.id,
                    AISuggestion.deleted_at.is_(None),
                )
                .order_by(AISuggestion.created_at.asc())
                .all()
            )
            provenance_rows = {
                row.id: self._provenance_to_block(row)
                for row in self.db.query(AIProvenance)
                .filter(AIProvenance.id.in_({item.provenance_id for item in rows}))
                .all()
            }
            return SuggestionsListResponse(
                suggestions=[
                    self._suggestion_to_response(item, provenance_rows[item.provenance_id]) for item in rows
                ]
            )

    def decide_suggestion(
        self, principal: Principal, suggestion_id: UUID, payload: SuggestionDecisionRequest
    ) -> SuggestionResponse:
        with tenant_session(self.db, principal.organization_id):
            row = self.db.get(AISuggestion, suggestion_id)
            if row is None or row.organization_id != principal.organization_id:
                raise AppError(code="NOT_FOUND", message_key="errors.http_error", status_code=404)
            if row.decision_status != "pending":
                raise AppError(
                    code="DECISION_ALREADY_RECORDED",
                    message_key="errors.ai_decision_recorded",
                    status_code=409,
                )
            row.decision_status = payload.decision
            row.decided_by = principal.user_id
            row.decided_at = datetime.now(UTC)
            row.decision_reason = payload.reason
            row.edited_value = payload.edited_value
            if payload.decision == "edited" and payload.edited_value:
                concept = dict(row.concept)
                if "label" in payload.edited_value:
                    concept["label"] = str(payload.edited_value["label"])
                row.concept = concept
            row.updated_by = principal.user_id
            self.db.flush()
            provenance = self.db.get(AIProvenance, row.provenance_id)
            assert provenance is not None
            self.audit.record(
                action="ai.review",
                organization_id=principal.organization_id,
                actor_user_id=principal.user_id,
                resource_type="ai_suggestion",
                resource_id=row.id,
                metadata={"decision": payload.decision},
            )
            return self._suggestion_to_response(row, self._provenance_to_block(provenance))

    def get_provenance(self, principal: Principal, suggestion_id: UUID) -> ProvenanceBlock:
        with tenant_session(self.db, principal.organization_id):
            row = self.db.get(AISuggestion, suggestion_id)
            if row is None or row.organization_id != principal.organization_id:
                raise AppError(code="NOT_FOUND", message_key="errors.http_error", status_code=404)
            provenance = self.db.get(AIProvenance, row.provenance_id)
            if provenance is None:
                raise AppError(code="NOT_FOUND", message_key="errors.http_error", status_code=404)
            return self._provenance_to_block(provenance)

    def _apply_draft_note_suggestion(
        self, session: ConsultationSession, draft_note: dict[str, Any], principal: Principal
    ) -> None:
        note = (
            self.db.query(ClinicalNote)
            .filter(
                ClinicalNote.session_id == session.id,
                ClinicalNote.status == "draft",
                ClinicalNote.addendum_of_id.is_(None),
                ClinicalNote.deleted_at.is_(None),
            )
            .order_by(ClinicalNote.created_at.desc())
            .first()
        )
        if note is None:
            return
        note.content = draft_note
        note.updated_by = principal.user_id
        self.db.flush()

    def _get_session(self, principal: Principal, session_id: UUID) -> ConsultationSession:
        session = self.db.get(ConsultationSession, session_id)
        if session is None or session.organization_id != principal.organization_id:
            raise AppError(code="NOT_FOUND", message_key="errors.http_error", status_code=404)
        return session

    def _load_segments(self, session_id: UUID, organization_id: UUID) -> list[TranscriptSegment]:
        return (
            self.db.query(TranscriptSegment)
            .filter(
                TranscriptSegment.session_id == session_id,
                TranscriptSegment.organization_id == organization_id,
                TranscriptSegment.deleted_at.is_(None),
            )
            .order_by(TranscriptSegment.seq.asc())
            .all()
        )

    def _latest_run(self, session_id: UUID, organization_id: UUID) -> AIExtractionRun | None:
        return (
            self.db.query(AIExtractionRun)
            .filter(
                AIExtractionRun.session_id == session_id,
                AIExtractionRun.organization_id == organization_id,
                AIExtractionRun.deleted_at.is_(None),
            )
            .order_by(AIExtractionRun.created_at.desc())
            .first()
        )

    @staticmethod
    def _hash_transcript(transcript: list[TranscriptInput]) -> str:
        payload = [
            {"segment_id": str(item.segment_id), "speaker": item.speaker, "text": item.text}
            for item in transcript
        ]
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _provenance_to_block(self, row: AIProvenance) -> ProvenanceBlock:
        return ProvenanceBlock(
            model_id=row.model_id,
            provider=row.provider,
            prompt_version=row.prompt_version,
            input_hash=row.input_hash,
            generated_at=row.generation_timestamp,
            parameters=row.parameters,
            latency_ms=row.latency_ms,
        )

    def _run_to_response(self, run: AIExtractionRun) -> ExtractionRunResponse:
        return ExtractionRunResponse(
            id=run.id,
            session_id=run.session_id,
            status=run.status,
            error_message=run.error_message,
            completed_at=run.completed_at,
        )

    def _fact_to_response(self, fact: ExtractedFact, provenance: ProvenanceBlock) -> ExtractedFactResponse:
        return ExtractedFactResponse(
            id=fact.id,
            session_id=fact.session_id,
            fact_type=fact.fact_type,
            value=fact.value,
            source_segment_ref=fact.source_segment_ref,
            confidence=ConfidenceBlock(level=fact.confidence_level, score=fact.confidence_score),
            status=fact.status,
            provenance=provenance,
        )

    def _suggestion_to_response(self, row: AISuggestion, provenance: ProvenanceBlock) -> SuggestionResponse:
        return SuggestionResponse(
            id=row.id,
            session_id=row.session_id,
            suggestion_type=row.suggestion_type,
            concept=ConceptBlock.model_validate(row.concept),
            supporting_facts=[SupportingFactBlock.model_validate(item) for item in row.supporting_facts],
            missing_information=row.missing_information,
            conflicting_information=row.conflicting_information,
            confidence=ConfidenceBlock(level=row.confidence_level, score=row.confidence_score),
            red_flag_warnings=row.red_flag_warnings,
            source_references=row.source_references,
            uncertainty_notes=row.uncertainty_notes,
            provenance=provenance,
            decision={
                "status": row.decision_status,
                "by": str(row.decided_by) if row.decided_by else None,
                "at": row.decided_at.isoformat() if row.decided_at else None,
                "reason": row.decision_reason,
                "edited_value": row.edited_value,
            },
        )
