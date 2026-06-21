"""Synthetic seed data for local development (no real PHI)."""

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.enums import Locale
from app.core.models import Organization, Role
from app.core.tenant import Principal
from app.modules.auth.service import AuthService, RegisterOrganizationRequest
from app.modules.identity.service import ClinicCreateRequest, IdentityService, UserCreateRequest
from app.modules.rbac.service import PermissionService


def main() -> None:
    db: Session = SessionLocal()
    try:
        existing = db.query(Organization).filter(Organization.slug == "synthetic-demo").first()
        if existing:
            print("Synthetic seed already exists; skipping.")
            return

        auth = AuthService(db)
        admin, organization, _ = auth.register_organization(
            RegisterOrganizationRequest(
                organization_name="Synthetic Demo Clinic Group",
                organization_slug="synthetic-demo",
                admin_email="admin@synthetic-demo.example.com",
                admin_full_name="Dr Synthetic Admin",
                admin_password="SyntheticDemo123!",
                default_locale=Locale.EN,
            )
        )

        principal = Principal(
            user_id=admin.id,
            organization_id=organization.id,
            permissions=frozenset(
                PermissionService(db).get_user_permissions(user_id=admin.id, organization_id=organization.id)
            ),
            locale=Locale.EN,
            email=admin.email,
            full_name=admin.full_name,
        )

        identity = IdentityService(db)
        clinic = identity.create_clinic(
            principal,
            ClinicCreateRequest(name="Synthetic Main Clinic", timezone="Asia/Dubai"),
        )
        doctor = identity.create_user(
            principal,
            UserCreateRequest(
                email="doctor@synthetic-demo.example.com",
                full_name="Dr Synthetic Example",
                password="SyntheticDoctor123!",
                preferred_locale="ar",
            ),
        )
        doctor_role = db.query(Role).filter(Role.key == "doctor", Role.organization_id.is_(None)).one()
        PermissionService(db).assign_role(
            user_id=doctor.id,
            role_id=doctor_role.id,
            organization_id=organization.id,
            clinic_id=clinic.id,
            created_by=admin.id,
        )
        identity.add_clinic_membership(principal, clinic_id=clinic.id, user_id=doctor.id, is_primary=True)

        db.commit()
        print("Synthetic seed completed.")
        print(f"  Organization: {organization.slug}")
        print("  Admin: admin@synthetic-demo.example.com / SyntheticDemo123!")
        print("  Doctor: doctor@synthetic-demo.example.com / SyntheticDoctor123!")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
