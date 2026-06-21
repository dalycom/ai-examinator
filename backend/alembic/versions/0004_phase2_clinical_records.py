"""Phase 2 clinical records schema with tenant RLS."""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004_phase2_clinical"
down_revision: str | None = "0003_app_db_role"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "ai_examinator_app"

TENANT_TABLES = [
    "patient",
    "medical_history_entry",
    "allergy",
    "medication",
    "problem",
    "vital_sign",
    "appointment",
    "encounter",
    "document",
]


def _tenant_columns(*, data_classification_default: str = "internal") -> list[sa.Column]:
    return [
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "data_classification",
            sa.String(length=32),
            nullable=False,
            server_default=data_classification_default,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def _enable_tenant_rls(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY tenant_isolation_policy ON {table}
        USING (
            organization_id::text = current_setting('app.current_organization_id', true)
            OR current_setting('app.current_organization_id', true) = ''
        )
        WITH CHECK (
            organization_id::text = current_setting('app.current_organization_id', true)
            OR current_setting('app.current_organization_id', true) = ''
        )
        """
    )


def _grant_app_role(table: str) -> None:
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO {APP_ROLE}")


def upgrade() -> None:
    op.create_table(
        "patient",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clinic.id"), nullable=True),
        sa.Column("mrn", sa.String(length=64), nullable=False),
        sa.Column("given_name", sa.String(length=128), nullable=False),
        sa.Column("family_name", sa.String(length=128), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("sex", sa.String(length=16), nullable=True),
        sa.Column("contact", postgresql.JSONB(), nullable=True),
        sa.Column("national_id", sa.String(length=128), nullable=True),
        sa.Column("preferred_locale", sa.String(length=8), nullable=False, server_default="en"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        *_tenant_columns(),
    )
    op.create_index("ix_patient_mrn", "patient", ["mrn"])
    op.create_index("ix_patient_organization_id", "patient", ["organization_id"])

    op.create_table(
        "medical_history_entry",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patient.id"), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("onset_date", sa.Date(), nullable=True),
        *_tenant_columns(),
    )
    op.create_index("ix_medical_history_entry_organization_id", "medical_history_entry", ["organization_id"])

    op.create_table(
        "allergy",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patient.id"), nullable=False),
        sa.Column("substance_code", sa.String(length=64), nullable=True),
        sa.Column("substance_name", sa.String(length=255), nullable=False),
        sa.Column("reaction", sa.Text(), nullable=True),
        sa.Column("severity", sa.String(length=32), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        *_tenant_columns(),
    )
    op.create_index("ix_allergy_organization_id", "allergy", ["organization_id"])

    op.create_table(
        "medication",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patient.id"), nullable=False),
        sa.Column("drug_code", sa.String(length=64), nullable=True),
        sa.Column("drug_name", sa.String(length=255), nullable=False),
        sa.Column("dose", sa.String(length=128), nullable=True),
        sa.Column("route", sa.String(length=64), nullable=True),
        sa.Column("frequency", sa.String(length=128), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        *_tenant_columns(),
    )
    op.create_index("ix_medication_organization_id", "medication", ["organization_id"])

    op.create_table(
        "problem",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patient.id"), nullable=False),
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("icd10_code", sa.String(length=16), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("onset_date", sa.Date(), nullable=True),
        *_tenant_columns(),
    )
    op.create_index("ix_problem_organization_id", "problem", ["organization_id"])

    op.create_table(
        "vital_sign",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patient.id"), nullable=False),
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("loinc_code", sa.String(length=32), nullable=True),
        sa.Column("vital_type", sa.String(length=64), nullable=False),
        sa.Column("value", sa.String(length=64), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=True),
        sa.Column(
            "measured_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        *_tenant_columns(),
    )
    op.create_index("ix_vital_sign_organization_id", "vital_sign", ["organization_id"])

    op.create_table(
        "appointment",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patient.id"), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clinic.id"), nullable=False),
        sa.Column("clinician_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="scheduled"),
        sa.Column("notes", sa.Text(), nullable=True),
        *_tenant_columns(),
    )
    op.create_index("ix_appointment_organization_id", "appointment", ["organization_id"])

    op.create_table(
        "encounter",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patient.id"), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clinic.id"), nullable=False),
        sa.Column("clinician_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("user.id"), nullable=False),
        sa.Column(
            "appointment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("appointment.id"),
            nullable=True,
        ),
        sa.Column("encounter_type", sa.String(length=32), nullable=False, server_default="outpatient"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="in_progress"),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        *_tenant_columns(),
    )
    op.create_index("ix_encounter_organization_id", "encounter", ["organization_id"])

    op.create_table(
        "document",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patient.id"), nullable=False),
        sa.Column(
            "encounter_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("encounter.id"),
            nullable=True,
        ),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("checksum", sa.String(length=128), nullable=True),
        *_tenant_columns(data_classification_default="phi"),
    )
    op.create_index("ix_document_organization_id", "document", ["organization_id"])

    for table in TENANT_TABLES:
        _enable_tenant_rls(table)
        _grant_app_role(table)


def downgrade() -> None:
    for table in TENANT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table}")
        op.execute(f"REVOKE ALL PRIVILEGES ON {table} FROM {APP_ROLE}")

    op.drop_table("document")
    op.drop_table("encounter")
    op.drop_table("appointment")
    op.drop_table("vital_sign")
    op.drop_table("problem")
    op.drop_table("medication")
    op.drop_table("allergy")
    op.drop_table("medical_history_entry")
    op.drop_table("patient")
