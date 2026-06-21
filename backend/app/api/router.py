from fastapi import APIRouter

from app.modules.appointments.router import router as appointments_router
from app.modules.audit.router import router as audit_router
from app.modules.auth.router import router as auth_router
from app.modules.consent.router import router as consent_router
from app.modules.consultation.router import router as consultation_router
from app.modules.documents.router import router as documents_router
from app.modules.identity.router import router as identity_router
from app.modules.patients.router import router as patients_router
from app.modules.terminology.router import router as terminology_router
from app.modules.timeline.router import router as timeline_router
from app.modules.ai.router import router as ai_router
from app.modules.integrations.router import router as integrations_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(identity_router)
api_router.include_router(audit_router)
api_router.include_router(patients_router)
api_router.include_router(consent_router)
api_router.include_router(consultation_router)
api_router.include_router(appointments_router)
api_router.include_router(documents_router)
api_router.include_router(timeline_router)
api_router.include_router(terminology_router)
api_router.include_router(ai_router)
api_router.include_router(integrations_router)
