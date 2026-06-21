from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.core.tenant import Principal
from app.modules.documents.service import (
    DocumentFinalizeRequest,
    DocumentResponse,
    DocumentService,
    DocumentUploadRequest,
    DocumentUploadResponse,
)

router = APIRouter(tags=["documents"])


@router.post("/patients/{patient_id}/documents:create-upload", response_model=DocumentUploadResponse)
def create_document_upload(
    patient_id: UUID,
    payload: DocumentUploadRequest,
    principal: Principal = Depends(require_permission("document:upload")),
    db: Session = Depends(get_db),
) -> DocumentUploadResponse:
    service = DocumentService(db)
    result = service.create_upload(principal, patient_id, payload)
    db.commit()
    return result


@router.post("/documents/{document_id}:finalize", response_model=DocumentResponse)
def finalize_document(
    document_id: UUID,
    payload: DocumentFinalizeRequest,
    principal: Principal = Depends(require_permission("document:upload")),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    service = DocumentService(db)
    result = service.finalize(principal, document_id, payload)
    db.commit()
    return result


@router.get("/patients/{patient_id}/documents", response_model=list[DocumentResponse])
def list_documents(
    patient_id: UUID,
    principal: Principal = Depends(require_permission("document:read")),
    db: Session = Depends(get_db),
) -> list[DocumentResponse]:
    return DocumentService(db).list_documents(principal, patient_id)
