import json
from uuid import UUID

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, get_db, tenant_session
from app.core.dependencies import require_permission
from app.core.enums import Locale
from app.core.errors import AppError
from app.core.models import User
from app.core.security import decode_token
from app.core.tenant import Principal
from app.modules.consultation.service import (
    AddendumCreateRequest,
    AudioFinalizeRequest,
    AudioUploadRequest,
    AudioUploadResponse,
    ClinicalNoteResponse,
    ClinicalNoteUpdateRequest,
    ConsultationService,
    RecordingResponse,
    RecordingStartResponse,
    SessionResponse,
    TranscriptSegmentResponse,
    TranscriptSegmentUpdateRequest,
)

router = APIRouter(tags=["consultation"])


@router.post("/encounters/{encounter_id}/sessions", response_model=SessionResponse, status_code=201)
def create_session(
    encounter_id: UUID,
    principal: Principal = Depends(require_permission("consultation:start")),
    db: Session = Depends(get_db),
) -> SessionResponse:
    service = ConsultationService(db)
    result = service.create_session(principal, encounter_id)
    db.commit()
    return result


@router.get("/sessions/{session_id}", response_model=SessionResponse)
def get_session(
    session_id: UUID,
    principal: Principal = Depends(require_permission("consultation:start")),
    db: Session = Depends(get_db),
) -> SessionResponse:
    return ConsultationService(db).get_session(principal, session_id)


@router.post("/sessions/{session_id}/recording:start", response_model=RecordingStartResponse)
def start_recording(
    session_id: UUID,
    principal: Principal = Depends(require_permission("recording:write")),
    db: Session = Depends(get_db),
) -> RecordingStartResponse:
    service = ConsultationService(db)
    result = service.start_recording(principal, session_id)
    db.commit()
    return result


@router.post("/sessions/{session_id}/audio:create-upload", response_model=AudioUploadResponse)
def create_audio_upload(
    session_id: UUID,
    payload: AudioUploadRequest,
    principal: Principal = Depends(require_permission("recording:write")),
    db: Session = Depends(get_db),
) -> AudioUploadResponse:
    service = ConsultationService(db)
    result = service.create_audio_upload(principal, session_id, payload)
    db.commit()
    return result


@router.post("/sessions/{session_id}/audio:finalize", response_model=RecordingResponse)
def finalize_audio_upload(
    session_id: UUID,
    payload: AudioFinalizeRequest,
    principal: Principal = Depends(require_permission("recording:write")),
    db: Session = Depends(get_db),
) -> RecordingResponse:
    service = ConsultationService(db)
    result = service.finalize_audio_upload(principal, session_id, payload)
    db.commit()
    return result


@router.post("/sessions/{session_id}/recovery", response_model=SessionResponse)
def update_recovery_checkpoint(
    session_id: UUID,
    last_seq: int = Query(ge=0),
    principal: Principal = Depends(require_permission("recording:write")),
    db: Session = Depends(get_db),
) -> SessionResponse:
    service = ConsultationService(db)
    result = service.update_recovery_checkpoint(principal, session_id, last_seq)
    db.commit()
    return result


@router.get("/sessions/{session_id}/transcript", response_model=list[TranscriptSegmentResponse])
def get_transcript(
    session_id: UUID,
    principal: Principal = Depends(require_permission("transcript:read")),
    db: Session = Depends(get_db),
) -> list[TranscriptSegmentResponse]:
    return ConsultationService(db).get_transcript(principal, session_id)


@router.patch("/sessions/{session_id}/transcript/{segment_id}", response_model=TranscriptSegmentResponse)
def update_transcript_segment(
    session_id: UUID,
    segment_id: UUID,
    payload: TranscriptSegmentUpdateRequest,
    principal: Principal = Depends(require_permission("transcript:edit")),
    db: Session = Depends(get_db),
) -> TranscriptSegmentResponse:
    service = ConsultationService(db)
    result = service.update_transcript_segment(principal, session_id, segment_id, payload)
    db.commit()
    return result


@router.get("/sessions/{session_id}/note", response_model=ClinicalNoteResponse)
def get_note(
    session_id: UUID,
    principal: Principal = Depends(require_permission("note:read")),
    db: Session = Depends(get_db),
) -> ClinicalNoteResponse:
    return ConsultationService(db).get_note(principal, session_id)


@router.patch("/sessions/{session_id}/note", response_model=ClinicalNoteResponse)
def update_note(
    session_id: UUID,
    payload: ClinicalNoteUpdateRequest,
    principal: Principal = Depends(require_permission("note:edit")),
    db: Session = Depends(get_db),
) -> ClinicalNoteResponse:
    service = ConsultationService(db)
    result = service.update_note(principal, session_id, payload)
    db.commit()
    return result


@router.post("/sessions/{session_id}/note:sign", response_model=ClinicalNoteResponse)
def sign_note(
    session_id: UUID,
    principal: Principal = Depends(require_permission("note:sign")),
    db: Session = Depends(get_db),
) -> ClinicalNoteResponse:
    service = ConsultationService(db)
    result = service.sign_note(principal, session_id)
    db.commit()
    return result


@router.post("/sessions/{session_id}/note:addendum", response_model=ClinicalNoteResponse, status_code=201)
def create_addendum(
    session_id: UUID,
    payload: AddendumCreateRequest,
    principal: Principal = Depends(require_permission("note:edit")),
    db: Session = Depends(get_db),
) -> ClinicalNoteResponse:
    service = ConsultationService(db)
    result = service.create_addendum(principal, session_id, payload)
    db.commit()
    return result


def _principal_from_token(token: str, db: Session) -> Principal:
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise AppError(code="UNAUTHORIZED", message_key="errors.unauthorized", status_code=401)

    user_id = UUID(payload["sub"])
    organization_id = UUID(payload["org"])
    permissions = frozenset(payload.get("permissions", []))

    with tenant_session(db, organization_id):
        user = db.get(User, user_id)
        if user is None or user.status != "active" or user.organization_id != organization_id:
            raise AppError(code="UNAUTHORIZED", message_key="errors.unauthorized", status_code=401)

    return Principal(
        user_id=user_id,
        organization_id=organization_id,
        permissions=permissions,
        locale=Locale(user.preferred_locale),
        email=user.email,
        full_name=user.full_name,
    )


@router.websocket("/ws/sessions/{session_id}")
async def consultation_ws(
    websocket: WebSocket,
    session_id: UUID,
    token: str = Query(...),
) -> None:
    db = SessionLocal()
    try:
        principal = _principal_from_token(token, db)
        if "recording:write" not in principal.permissions:
            await websocket.close(code=4403)
            return

        service = ConsultationService(db)
        session = service.get_session(principal, session_id)
        await websocket.accept()
        await websocket.send_json({"type": "status", "session_status": session.status})

        while True:
            raw = await websocket.receive_text()
            message = json.loads(raw)
            message_type = message.get("type")

            if message_type == "resume":
                checkpoint = session.recovery_checkpoint or {}
                await websocket.send_json(
                    {
                        "type": "resume_ack",
                        "last_seq": checkpoint.get("last_seq", 0),
                        "session_status": session.status,
                    }
                )
                continue

            if message_type == "audio_chunk":
                seq = int(message.get("seq", 0))
                service.update_recovery_checkpoint(principal, session_id, seq)
                db.commit()
                session = service.get_session(principal, session_id)

                preview = service.stream_transcript_preview(principal, session_id, seq)
                if preview is not None:
                    await websocket.send_json(
                        {
                            "type": "transcript_segment",
                            "seq": preview.seq,
                            "speaker": preview.speaker,
                            "language": preview.language,
                            "text": preview.text,
                            "confidence": preview.confidence,
                            "start_ms": preview.start_ms,
                            "end_ms": preview.end_ms,
                        }
                    )

                await websocket.send_json({"type": "chunk_ack", "seq": seq})
                continue

            if message_type == "finish_stream":
                session = service.get_session(principal, session_id)
                await websocket.send_json(
                    {"type": "status", "session_status": session.status},
                )
                continue

            await websocket.send_json({"type": "error", "code": "UNKNOWN_MESSAGE", "detail": message_type})
    except WebSocketDisconnect:
        pass
    except AppError:
        await websocket.close(code=4401)
    finally:
        db.close()
