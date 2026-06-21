from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.adapters.storage.s3_adapter import build_recording_storage_key, get_object_storage_adapter
from app.adapters.stt.port import TranscriptSegmentResult
from app.adapters.stt.stub_adapter import get_speech_to_text_adapter
from app.core.database import tenant_session
from app.core.dependencies import compute_record_hash
from app.core.enums import DataClassification
from app.core.errors import AppError
from app.core.tenant import Principal
from app.modules.audit.service import AuditService
from app.modules.clinical.models import Encounter
from app.modules.consent.service import ConsentService
from app.modules.consultation.models import (
    ClinicalNote,
    ConsultationSession,
    SessionRecording,
    TranscriptSegment,
)


class SessionResponse(BaseModel):
    id: UUID
    encounter_id: UUID
    patient_id: UUID
    clinic_id: UUID
    clinician_id: UUID
    status: str
    recovery_checkpoint: dict[str, Any] | None
    started_at: datetime
    ended_at: datetime | None


class RecordingStartResponse(BaseModel):
    session_id: UUID
    status: str
    recording_id: UUID


class AudioUploadRequest(BaseModel):
    filename: str
    mime_type: str = Field(default="audio/webm", max_length=128)


class AudioUploadResponse(BaseModel):
    recording_id: UUID
    upload_url: str
    storage_key: str


class AudioFinalizeRequest(BaseModel):
    size_bytes: int | None = None
    checksum: str | None = None
    duration_ms: int | None = None


class RecordingResponse(BaseModel):
    id: UUID
    session_id: UUID
    status: str
    mime_type: str
    duration_ms: int | None
    last_seq: int


class TranscriptSegmentResponse(BaseModel):
    id: UUID
    seq: int
    speaker: str
    language: str
    text: str
    corrected_text: str | None
    confidence: float | None
    start_ms: int
    end_ms: int
    is_corrected: bool


class TranscriptSegmentUpdateRequest(BaseModel):
    corrected_text: str = Field(min_length=1)


class NoteContent(BaseModel):
    subjective: str = ""
    objective: str = ""
    assessment: str = ""
    plan: str = ""


class ClinicalNoteResponse(BaseModel):
    id: UUID
    session_id: UUID
    encounter_id: UUID
    patient_id: UUID
    status: str
    content: dict[str, Any]
    content_hash: str | None
    signed_at: datetime | None
    addendum_of_id: UUID | None


class ClinicalNoteUpdateRequest(BaseModel):
    content: NoteContent


class AddendumCreateRequest(BaseModel):
    content: NoteContent


class ConsultationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.audit = AuditService(db)
        self.consent = ConsentService(db)
        self.storage = get_object_storage_adapter()
        self.stt = get_speech_to_text_adapter()

    def create_session(self, principal: Principal, encounter_id: UUID) -> SessionResponse:
        with tenant_session(self.db, principal.organization_id):
            encounter = self._get_encounter(principal, encounter_id)
            session = ConsultationSession(
                organization_id=principal.organization_id,
                encounter_id=encounter.id,
                patient_id=encounter.patient_id,
                clinic_id=encounter.clinic_id,
                clinician_id=principal.user_id,
                status="draft",
                data_classification=DataClassification.PHI.value,
                created_by=principal.user_id,
                updated_by=principal.user_id,
            )
            self.db.add(session)
            self.db.flush()

            note = ClinicalNote(
                organization_id=principal.organization_id,
                session_id=session.id,
                encounter_id=encounter.id,
                patient_id=encounter.patient_id,
                status="draft",
                content=NoteContent().model_dump(),
                data_classification=DataClassification.PHI.value,
                created_by=principal.user_id,
                updated_by=principal.user_id,
            )
            self.db.add(note)
            self.db.flush()

            self.audit.record(
                action="consultation.session.create",
                organization_id=principal.organization_id,
                actor_user_id=principal.user_id,
                resource_type="consultation_session",
                resource_id=session.id,
            )
            return self._session_response(session)

    def get_session(self, principal: Principal, session_id: UUID) -> SessionResponse:
        with tenant_session(self.db, principal.organization_id):
            session = self._get_session(principal, session_id)
            return self._session_response(session)

    def start_recording(self, principal: Principal, session_id: UUID) -> RecordingStartResponse:
        with tenant_session(self.db, principal.organization_id):
            session = self._get_session(principal, session_id)
            self.consent.require_scope(principal, session.patient_id, ConsentService.REQUIRED_RECORDING_SCOPE)

            recording = SessionRecording(
                organization_id=principal.organization_id,
                session_id=session.id,
                storage_key="",
                mime_type="audio/webm",
                status="pending",
                data_classification=DataClassification.PHI.value,
                created_by=principal.user_id,
                updated_by=principal.user_id,
            )
            self.db.add(recording)
            session.status = "recording"
            session.updated_by = principal.user_id
            self.db.flush()

            self.audit.record(
                action="consultation.recording.start",
                organization_id=principal.organization_id,
                actor_user_id=principal.user_id,
                resource_type="consultation_session",
                resource_id=session.id,
            )
            return RecordingStartResponse(
                session_id=session.id,
                status=session.status,
                recording_id=recording.id,
            )

    def create_audio_upload(
        self, principal: Principal, session_id: UUID, payload: AudioUploadRequest
    ) -> AudioUploadResponse:
        with tenant_session(self.db, principal.organization_id):
            session = self._get_session(principal, session_id)
            self.consent.require_scope(principal, session.patient_id, ConsentService.REQUIRED_RECORDING_SCOPE)

            recording = (
                self.db.query(SessionRecording)
                .filter(
                    SessionRecording.session_id == session.id,
                    SessionRecording.organization_id == principal.organization_id,
                    SessionRecording.deleted_at.is_(None),
                )
                .order_by(SessionRecording.created_at.desc())
                .first()
            )
            if recording is None:
                recording = SessionRecording(
                    organization_id=principal.organization_id,
                    session_id=session.id,
                    storage_key="",
                    mime_type=payload.mime_type,
                    status="pending",
                    data_classification=DataClassification.PHI.value,
                    created_by=principal.user_id,
                    updated_by=principal.user_id,
                )
                self.db.add(recording)
                self.db.flush()

            storage_key = build_recording_storage_key(
                organization_id=str(principal.organization_id),
                session_id=str(session.id),
                filename=payload.filename,
            )
            recording.storage_key = storage_key
            recording.mime_type = payload.mime_type
            recording.updated_by = principal.user_id
            self.db.flush()

            upload_url = self.storage.create_upload_url(key=storage_key, content_type=payload.mime_type)
            return AudioUploadResponse(
                recording_id=recording.id,
                upload_url=upload_url,
                storage_key=storage_key,
            )

    def finalize_audio_upload(
        self, principal: Principal, session_id: UUID, payload: AudioFinalizeRequest
    ) -> RecordingResponse:
        with tenant_session(self.db, principal.organization_id):
            session = self._get_session(principal, session_id)
            recording = self._latest_recording(principal, session.id)
            recording.status = "uploaded"
            recording.size_bytes = payload.size_bytes
            recording.checksum = payload.checksum
            recording.duration_ms = payload.duration_ms
            recording.updated_by = principal.user_id
            session.status = "transcribing"
            session.updated_by = principal.user_id
            self.db.flush()

            self._run_transcription(principal, session, recording)

            self.audit.record(
                action="consultation.audio.finalize",
                organization_id=principal.organization_id,
                actor_user_id=principal.user_id,
                resource_type="session_recording",
                resource_id=recording.id,
            )
            return self._recording_response(recording)

    def stream_transcript_preview(
        self, principal: Principal, session_id: UUID, seq: int
    ) -> TranscriptSegmentResult | None:
        """Emit synthetic live segments over WebSocket (every 2nd chunk). Not persisted until finalize."""
        if seq < 2 or seq % 2 != 0:
            return None

        previews = get_speech_to_text_adapter().transcribe_batch(
            storage_key=f"stream-{session_id}",
            mime_type="audio/webm",
        )
        index = min((seq // 2) - 1, len(previews) - 1)
        if index < 0:
            return None
        return previews[index]

    def update_recovery_checkpoint(
        self, principal: Principal, session_id: UUID, last_seq: int
    ) -> SessionResponse:
        with tenant_session(self.db, principal.organization_id):
            session = self._get_session(principal, session_id)
            session.recovery_checkpoint = {"last_seq": last_seq, "updated_at": datetime.now(UTC).isoformat()}
            session.updated_by = principal.user_id
            self.db.flush()
            return self._session_response(session)

    def get_transcript(self, principal: Principal, session_id: UUID) -> list[TranscriptSegmentResponse]:
        with tenant_session(self.db, principal.organization_id):
            self._get_session(principal, session_id)
            rows = (
                self.db.query(TranscriptSegment)
                .filter(
                    TranscriptSegment.session_id == session_id,
                    TranscriptSegment.organization_id == principal.organization_id,
                    TranscriptSegment.deleted_at.is_(None),
                )
                .order_by(TranscriptSegment.seq.asc())
                .all()
            )
            return [self._segment_response(row) for row in rows]

    def update_transcript_segment(
        self,
        principal: Principal,
        session_id: UUID,
        segment_id: UUID,
        payload: TranscriptSegmentUpdateRequest,
    ) -> TranscriptSegmentResponse:
        with tenant_session(self.db, principal.organization_id):
            self._get_session(principal, session_id)
            segment = self.db.get(TranscriptSegment, segment_id)
            if (
                segment is None
                or segment.organization_id != principal.organization_id
                or segment.session_id != session_id
            ):
                raise AppError(code="NOT_FOUND", message_key="errors.http_error", status_code=404)

            segment.corrected_text = payload.corrected_text
            segment.is_corrected = True
            segment.updated_by = principal.user_id
            self.db.flush()
            self.audit.record(
                action="transcript.segment.edit",
                organization_id=principal.organization_id,
                actor_user_id=principal.user_id,
                resource_type="transcript_segment",
                resource_id=segment.id,
            )
            return self._segment_response(segment)

    def get_note(self, principal: Principal, session_id: UUID) -> ClinicalNoteResponse:
        with tenant_session(self.db, principal.organization_id):
            note = self._get_draft_or_latest_note(principal, session_id)
            return self._note_response(note)

    def update_note(
        self, principal: Principal, session_id: UUID, payload: ClinicalNoteUpdateRequest
    ) -> ClinicalNoteResponse:
        with tenant_session(self.db, principal.organization_id):
            note = self._get_draft_or_latest_note(principal, session_id)
            if note.status == "signed":
                raise AppError(
                    code="NOTE_SIGNED",
                    message_key="errors.note_already_signed",
                    status_code=409,
                )
            note.content = payload.content.model_dump()
            note.updated_by = principal.user_id
            self.db.flush()
            self.audit.record(
                action="clinical_note.update",
                organization_id=principal.organization_id,
                actor_user_id=principal.user_id,
                resource_type="clinical_note",
                resource_id=note.id,
            )
            return self._note_response(note)

    def sign_note(self, principal: Principal, session_id: UUID) -> ClinicalNoteResponse:
        with tenant_session(self.db, principal.organization_id):
            note = self._get_draft_or_latest_note(principal, session_id)
            if note.status == "signed":
                return self._note_response(note)

            content_hash = compute_record_hash(None, note.content)
            note.status = "signed"
            note.content_hash = content_hash
            note.signed_at = datetime.now(UTC)
            note.signed_by = principal.user_id
            note.updated_by = principal.user_id

            session = self._get_session(principal, session_id)
            session.status = "completed"
            session.ended_at = datetime.now(UTC)
            session.updated_by = principal.user_id
            self.db.flush()

            self.audit.record(
                action="clinical_note.sign",
                organization_id=principal.organization_id,
                actor_user_id=principal.user_id,
                resource_type="clinical_note",
                resource_id=note.id,
                metadata={"content_hash": content_hash},
            )
            return self._note_response(note)

    def create_addendum(
        self, principal: Principal, session_id: UUID, payload: AddendumCreateRequest
    ) -> ClinicalNoteResponse:
        with tenant_session(self.db, principal.organization_id):
            signed_note = self._get_draft_or_latest_note(principal, session_id)
            if signed_note.status != "signed":
                raise AppError(code="VALIDATION_ERROR", message_key="errors.http_error", status_code=400)

            addendum = ClinicalNote(
                organization_id=principal.organization_id,
                session_id=session_id,
                encounter_id=signed_note.encounter_id,
                patient_id=signed_note.patient_id,
                addendum_of_id=signed_note.id,
                status="draft",
                content=payload.content.model_dump(),
                data_classification=DataClassification.PHI.value,
                created_by=principal.user_id,
                updated_by=principal.user_id,
            )
            self.db.add(addendum)
            self.db.flush()
            self.audit.record(
                action="clinical_note.addendum.create",
                organization_id=principal.organization_id,
                actor_user_id=principal.user_id,
                resource_type="clinical_note",
                resource_id=addendum.id,
            )
            return self._note_response(addendum)

    def _run_transcription(
        self, principal: Principal, session: ConsultationSession, recording: SessionRecording
    ) -> None:
        existing = (
            self.db.query(TranscriptSegment)
            .filter(
                TranscriptSegment.session_id == session.id,
                TranscriptSegment.organization_id == principal.organization_id,
            )
            .count()
        )
        if existing > 0:
            session.status = "transcribed"
            recording.status = "transcribed"
            return

        patient_locale = "en"
        segments = self.stt.transcribe_batch(
            storage_key=recording.storage_key,
            mime_type=recording.mime_type,
            language_hint=patient_locale,
        )
        for item in segments:
            segment = TranscriptSegment(
                organization_id=principal.organization_id,
                session_id=session.id,
                seq=item.seq,
                speaker=item.speaker,
                language=item.language,
                text=item.text,
                confidence=item.confidence,
                start_ms=item.start_ms,
                end_ms=item.end_ms,
                data_classification=DataClassification.PHI.value,
                created_by=principal.user_id,
                updated_by=principal.user_id,
            )
            self.db.add(segment)

        session.status = "transcribed"
        recording.status = "transcribed"
        self.db.flush()

    def _get_encounter(self, principal: Principal, encounter_id: UUID) -> Encounter:
        encounter = self.db.get(Encounter, encounter_id)
        if encounter is None or encounter.organization_id != principal.organization_id:
            raise AppError(code="NOT_FOUND", message_key="errors.http_error", status_code=404)
        return encounter

    def _get_session(self, principal: Principal, session_id: UUID) -> ConsultationSession:
        session = self.db.get(ConsultationSession, session_id)
        if session is None or session.organization_id != principal.organization_id:
            raise AppError(code="NOT_FOUND", message_key="errors.http_error", status_code=404)
        return session

    def _latest_recording(self, principal: Principal, session_id: UUID) -> SessionRecording:
        recording = (
            self.db.query(SessionRecording)
            .filter(
                SessionRecording.session_id == session_id,
                SessionRecording.organization_id == principal.organization_id,
                SessionRecording.deleted_at.is_(None),
            )
            .order_by(SessionRecording.created_at.desc())
            .first()
        )
        if recording is None:
            raise AppError(code="NOT_FOUND", message_key="errors.http_error", status_code=404)
        return recording

    def _get_draft_or_latest_note(self, principal: Principal, session_id: UUID) -> ClinicalNote:
        self._get_session(principal, session_id)
        draft = (
            self.db.query(ClinicalNote)
            .filter(
                ClinicalNote.session_id == session_id,
                ClinicalNote.organization_id == principal.organization_id,
                ClinicalNote.status == "draft",
                ClinicalNote.deleted_at.is_(None),
            )
            .order_by(ClinicalNote.created_at.desc())
            .first()
        )
        if draft is not None:
            return draft

        latest = (
            self.db.query(ClinicalNote)
            .filter(
                ClinicalNote.session_id == session_id,
                ClinicalNote.organization_id == principal.organization_id,
                ClinicalNote.deleted_at.is_(None),
            )
            .order_by(ClinicalNote.created_at.desc())
            .first()
        )
        if latest is None:
            raise AppError(code="NOT_FOUND", message_key="errors.http_error", status_code=404)
        return latest

    @staticmethod
    def _session_response(session: ConsultationSession) -> SessionResponse:
        return SessionResponse(
            id=session.id,
            encounter_id=session.encounter_id,
            patient_id=session.patient_id,
            clinic_id=session.clinic_id,
            clinician_id=session.clinician_id,
            status=session.status,
            recovery_checkpoint=session.recovery_checkpoint,
            started_at=session.started_at,
            ended_at=session.ended_at,
        )

    @staticmethod
    def _recording_response(recording: SessionRecording) -> RecordingResponse:
        return RecordingResponse(
            id=recording.id,
            session_id=recording.session_id,
            status=recording.status,
            mime_type=recording.mime_type,
            duration_ms=recording.duration_ms,
            last_seq=recording.last_seq,
        )

    @staticmethod
    def _segment_response(segment: TranscriptSegment) -> TranscriptSegmentResponse:
        return TranscriptSegmentResponse(
            id=segment.id,
            seq=segment.seq,
            speaker=segment.speaker,
            language=segment.language,
            text=segment.text,
            corrected_text=segment.corrected_text,
            confidence=segment.confidence,
            start_ms=segment.start_ms,
            end_ms=segment.end_ms,
            is_corrected=segment.is_corrected,
        )

    @staticmethod
    def _note_response(note: ClinicalNote) -> ClinicalNoteResponse:
        return ClinicalNoteResponse(
            id=note.id,
            session_id=note.session_id,
            encounter_id=note.encounter_id,
            patient_id=note.patient_id,
            status=note.status,
            content=note.content,
            content_hash=note.content_hash,
            signed_at=note.signed_at,
            addendum_of_id=note.addendum_of_id,
        )
