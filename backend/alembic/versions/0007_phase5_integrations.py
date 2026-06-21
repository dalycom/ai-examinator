"""Phase 5 integrations & reporting schema with tenant RLS."""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0007_phase5_integrations"
down_revision: str | None = "0006_phase4_ai"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "ai_examinator_app"

TENANT_TABLES = [
    "lab_imaging_result",
    "clinical_report",
    "export_job",
    "erasure_request",
    "notification",
    "retention_policy",
]


def _tenant_columns(*, data_classification_default: str = "phi") -> list[sa.Column]:
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
        "lab_imaging_result",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patient.id"), nullable=False),
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("encounter.id"), nullable=True),
        sa.Column("result_type", sa.String(length=16), nullable=False),
        sa.Column("loinc_code", sa.String(length=32), nullable=True),
        sa.Column("code_display", sa.String(length=255), nullable=False),
        sa.Column("value", sa.String(length=128), nullable=True),
        sa.Column("unit", sa.String(length=32), nullable=True),
        sa.Column("dicom_study_uid", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="final", nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        *_tenant_columns(),
    )
    op.create_index("ix_lab_imaging_result_patient_id", "lab_imaging_result", ["patient_id"])

    op.create_table(
        "clinical_report",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patient.id"), nullable=False),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("consultation_session.id"),
            nullable=True,
        ),
        sa.Column("locale", sa.String(length=8), server_default="en", nullable=False),
        sa.Column("format", sa.String(length=16), server_default="html", nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body_html", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}", nullable=False),
        *_tenant_columns(),
    )

    op.create_table(
        "export_job",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patient.id"), nullable=True),
        sa.Column("scope", sa.String(length=32), server_default="patient", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=True),
        sa.Column("result_summary", postgresql.JSONB(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *_tenant_columns(data_classification_default="sensitive_phi"),
    )

    op.create_table(
        "erasure_request",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patient.id"), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("user.id"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *_tenant_columns(data_classification_default="internal"),
    )

    op.create_table(
        "notification",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("channel", sa.String(length=16), server_default="in_app", nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("link_path", sa.String(length=512), nullable=True),
        sa.Column("is_read", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("email_sent", sa.Boolean(), server_default="false", nullable=False),
        *_tenant_columns(data_classification_default="internal"),
    )
    op.create_index("ix_notification_user_id", "notification", ["user_id"])

    op.create_table(
        "retention_policy",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("retention_days", sa.Integer(), nullable=False),
        sa.Column("erasure_enabled", sa.Boolean(), server_default="true", nullable=False),
        *_tenant_columns(data_classification_default="internal"),
    )
    op.create_index(
        "ix_retention_policy_org_resource",
        "retention_policy",
        ["organization_id", "resource_type"],
        unique=True,
    )

    for table in TENANT_TABLES:
        _enable_tenant_rls(table)
        _grant_app_role(table)


def downgrade() -> None:
    for table in TENANT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table}")
        op.execute(f"REVOKE ALL PRIVILEGES ON {table} FROM {APP_ROLE}")

    op.drop_table("retention_policy")
    op.drop_table("notification")
    op.drop_table("erasure_request")
    op.drop_table("export_job")
    op.drop_table("clinical_report")
    op.drop_table("lab_imaging_result")
