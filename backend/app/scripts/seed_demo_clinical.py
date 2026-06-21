"""Add synthetic patients and clinical demo data for dashboard UIs (no real PHI)."""

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.database import SessionLocal, bypass_tenant_rls_session, tenant_session
from app.core.enums import Locale
from app.core.models import Organization
from app.core.tenant import Principal
from app.modules.appointments.service import AppointmentCreateRequest, AppointmentService
from app.modules.clinical.models import Patient
from app.modules.identity.service import IdentityService
from app.modules.patients.service import (
    AllergyCreateRequest,
    PatientCreateRequest,
    PatientService,
    ProblemCreateRequest,
    VitalCreateRequest,
)
from app.modules.rbac.service import PermissionService


DEMO_PATIENTS: list[dict[str, str]] = [
    {"given_name": "Layla", "family_name": "Hassan", "sex": "female", "locale": "ar"},
    {"given_name": "Jean", "family_name": "Dupont", "sex": "male", "locale": "fr"},
    {"given_name": "Emma", "family_name": "Clark", "sex": "female", "locale": "en"},
]


def _principal_for_org(db: Session, organization_id) -> Principal:
    from app.core.models import User

    with bypass_tenant_rls_session(db):
        admin = (
            db.query(User)
            .filter(User.organization_id == organization_id)
            .order_by(User.created_at.asc())
            .first()
        )
    if admin is None:
        raise RuntimeError("No user found for synthetic-demo organization")

    return Principal(
        user_id=admin.id,
        organization_id=organization_id,
        permissions=frozenset(
            PermissionService(db).get_user_permissions(user_id=admin.id, organization_id=organization_id)
        ),
        locale=Locale.EN,
        email=admin.email,
        full_name=admin.full_name,
    )


def seed_demo_clinical(db: Session) -> int:
    org = db.query(Organization).filter(Organization.slug == "synthetic-demo").one_or_none()
    if org is None:
        print("Run seed_synthetic first (organization synthetic-demo not found).")
        return 0

    existing = (
        db.query(Patient)
        .filter(Patient.organization_id == org.id, Patient.deleted_at.is_(None))
        .count()
    )
    if existing >= len(DEMO_PATIENTS):
        print(f"Demo clinical data already present ({existing} patients); skipping.")
        return existing

    principal = _principal_for_org(db, org.id)
    identity = IdentityService(db)
    clinics = identity.list_clinics(principal)
    if not clinics:
        raise RuntimeError("No clinic found for synthetic-demo")
    clinic_id = clinics[0].id

    patients = PatientService(db)
    appointments = AppointmentService(db)
    created = 0

    with tenant_session(db, org.id):
        for spec in DEMO_PATIENTS:
            patient = patients.create_patient(
                principal,
                PatientCreateRequest(
                    clinic_id=clinic_id,
                    given_name=spec["given_name"],
                    family_name=spec["family_name"],
                    sex=spec["sex"],
                    preferred_locale=spec["locale"],
                ),
            )
            patients.add_allergy(
                principal,
                patient.id,
                AllergyCreateRequest(substance_name="Penicillin", reaction="Rash", severity="moderate"),
            )
            patients.add_problem(
                principal,
                patient.id,
                ProblemCreateRequest(description="Tension-type headache", icd10_code="G44.2"),
            )
            patients.add_vital(
                principal,
                patient.id,
                VitalCreateRequest(vital_type="Blood pressure", value="118/76", unit="mmHg"),
            )
            starts = datetime.now(tz=UTC) + timedelta(days=created + 1, hours=10)
            appointments.create_appointment(
                principal,
                AppointmentCreateRequest(
                    patient_id=patient.id,
                    clinic_id=clinic_id,
                    clinician_id=principal.user_id,
                    starts_at=starts,
                    ends_at=starts + timedelta(minutes=30),
                    notes="Synthetic follow-up",
                ),
            )
            created += 1

    db.commit()
    print(f"Demo clinical seed completed: {created} patients with allergies, problems, vitals, appointments.")
    return created


def main() -> None:
    db = SessionLocal()
    try:
        seed_demo_clinical(db)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
