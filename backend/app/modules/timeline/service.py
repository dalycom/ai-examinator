from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import tenant_session
from app.core.errors import AppError
from app.core.tenant import Principal
from app.modules.clinical.models import (
    Appointment,
    Document,
    Encounter,
    MedicalHistoryEntry,
    Medication,
    Patient,
)


class TimelineEvent(BaseModel):
    occurred_at: datetime
    event_type: str
    title: str
    metadata: dict[str, Any]


class TimelineService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_patient_timeline(self, principal: Principal, patient_id: UUID) -> list[TimelineEvent]:
        with tenant_session(self.db, principal.organization_id):
            patient = self.db.get(Patient, patient_id)
            if patient is None or patient.organization_id != principal.organization_id:
                raise AppError(code="NOT_FOUND", message_key="errors.http_error", status_code=404)

            events: list[TimelineEvent] = []

            appointments = (
                self.db.query(Appointment)
                .filter(Appointment.patient_id == patient_id, Appointment.organization_id == principal.organization_id)
                .all()
            )
            for appointment in appointments:
                events.append(
                    TimelineEvent(
                        occurred_at=appointment.starts_at,
                        event_type="appointment",
                        title=f"Appointment ({appointment.status})",
                        metadata={"appointment_id": str(appointment.id), "status": appointment.status},
                    )
                )

            encounters = (
                self.db.query(Encounter)
                .filter(Encounter.patient_id == patient_id, Encounter.organization_id == principal.organization_id)
                .all()
            )
            for encounter in encounters:
                events.append(
                    TimelineEvent(
                        occurred_at=encounter.started_at,
                        event_type="encounter",
                        title=f"Encounter ({encounter.encounter_type})",
                        metadata={"encounter_id": str(encounter.id), "status": encounter.status},
                    )
                )

            history_entries = (
                self.db.query(MedicalHistoryEntry)
                .filter(
                    MedicalHistoryEntry.patient_id == patient_id,
                    MedicalHistoryEntry.organization_id == principal.organization_id,
                )
                .all()
            )
            for entry in history_entries:
                events.append(
                    TimelineEvent(
                        occurred_at=entry.created_at,
                        event_type="history",
                        title=f"{entry.category.title()} history",
                        metadata={"entry_id": str(entry.id), "description": entry.description},
                    )
                )

            medications = (
                self.db.query(Medication)
                .filter(Medication.patient_id == patient_id, Medication.organization_id == principal.organization_id)
                .all()
            )
            for medication in medications:
                events.append(
                    TimelineEvent(
                        occurred_at=medication.created_at,
                        event_type="medication",
                        title=f"Medication: {medication.drug_name}",
                        metadata={"medication_id": str(medication.id), "status": medication.status},
                    )
                )

            documents = (
                self.db.query(Document)
                .filter(Document.patient_id == patient_id, Document.organization_id == principal.organization_id)
                .all()
            )
            for document in documents:
                events.append(
                    TimelineEvent(
                        occurred_at=document.created_at,
                        event_type="document",
                        title=f"Document: {document.kind}",
                        metadata={"document_id": str(document.id), "mime_type": document.mime_type},
                    )
                )

            events.sort(key=lambda event: event.occurred_at, reverse=True)
            return events
