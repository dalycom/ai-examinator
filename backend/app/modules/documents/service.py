from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.adapters.storage.s3_adapter import build_document_storage_key, get_object_storage_adapter
from app.core.database import tenant_session
from app.core.enums import DataClassification
from app.core.errors import AppError
from app.core.tenant import Principal
from app.modules.audit.service import AuditService
from app.modules.clinical.models import Document, Patient


class DocumentUploadRequest(BaseModel):
    kind: str = Field(max_length=64)
    filename: str
    mime_type: str
    encounter_id: UUID | None = None


class DocumentUploadResponse(BaseModel):
    document_id: UUID
    upload_url: str
    storage_key: str


class DocumentResponse(BaseModel):
    id: UUID
    patient_id: UUID
    encounter_id: UUID | None
    kind: str
    mime_type: str
    size_bytes: int | None
    download_url: str


class DocumentFinalizeRequest(BaseModel):
    size_bytes: int | None = None
    checksum: str | None = None


class DocumentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.audit = AuditService(db)
        self.storage = get_object_storage_adapter()

    def create_upload(
        self, principal: Principal, patient_id: UUID, payload: DocumentUploadRequest
    ) -> DocumentUploadResponse:
        with tenant_session(self.db, principal.organization_id):
            patient = self.db.get(Patient, patient_id)
            if patient is None or patient.organization_id != principal.organization_id:
                raise AppError(code="NOT_FOUND", message_key="errors.http_error", status_code=404)
            storage_key = build_document_storage_key(
                organization_id=str(principal.organization_id),
                patient_id=str(patient_id),
                filename=payload.filename,
            )
            document = Document(
                organization_id=principal.organization_id,
                patient_id=patient_id,
                encounter_id=payload.encounter_id,
                kind=payload.kind,
                storage_key=storage_key,
                mime_type=payload.mime_type,
                data_classification=DataClassification.PHI.value,
                created_by=principal.user_id,
                updated_by=principal.user_id,
            )
            self.db.add(document)
            self.db.flush()
            upload_url = self.storage.create_upload_url(
                key=storage_key,
                content_type=payload.mime_type,
            )
            return DocumentUploadResponse(
                document_id=document.id,
                upload_url=upload_url,
                storage_key=storage_key,
            )

    def finalize(
        self, principal: Principal, document_id: UUID, payload: DocumentFinalizeRequest
    ) -> DocumentResponse:
        with tenant_session(self.db, principal.organization_id):
            document = self.db.get(Document, document_id)
            if document is None or document.organization_id != principal.organization_id:
                raise AppError(code="NOT_FOUND", message_key="errors.http_error", status_code=404)
            document.size_bytes = payload.size_bytes
            document.checksum = payload.checksum
            document.updated_by = principal.user_id
            self.db.flush()
            self.audit.record(
                action="document.finalize",
                organization_id=principal.organization_id,
                actor_user_id=principal.user_id,
                resource_type="document",
                resource_id=document.id,
            )
            return self._to_response(document)

    def list_documents(self, principal: Principal, patient_id: UUID) -> list[DocumentResponse]:
        with tenant_session(self.db, principal.organization_id):
            rows = (
                self.db.query(Document)
                .filter(
                    Document.organization_id == principal.organization_id,
                    Document.patient_id == patient_id,
                    Document.deleted_at.is_(None),
                )
                .all()
            )
            return [self._to_response(row) for row in rows]

    def _to_response(self, document: Document) -> DocumentResponse:
        return DocumentResponse(
            id=document.id,
            patient_id=document.patient_id,
            encounter_id=document.encounter_id,
            kind=document.kind,
            mime_type=document.mime_type,
            size_bytes=document.size_bytes,
            download_url=self.storage.create_download_url(key=document.storage_key),
        )
