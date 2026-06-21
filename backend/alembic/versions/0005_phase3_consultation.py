"""Phase 3 consultation workspace schema with tenant RLS."""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0005_phase3_consultation"
down_revision: str | None = "0004_phase2_clinical"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "ai_examinator_app"

TENANT_TABLES = [
    "consent_record",
    "consultation_session",
    "session_recording",
    "transcript_segment",
    "clinical_note",
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
        "consent_record",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patient.id"), nullable=False),
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("encounter.id"), nullable=True),
        sa.Column("scopes", postgresql.JSONB(), nullable=False),
        sa.Column("method", sa.String(length=32), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
        *_tenant_columns(),
    )
    op.create_index("ix_consent_record_organization_id", "consent_record", ["organization_id"])
    op.create_index("ix_consent_record_patient_id", "consent_record", ["patient_id"])

    op.create_table(
        "consultation_session",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("encounter.id"), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patient.id"), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clinic.id"), nullable=False),
        sa.Column("clinician_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="draft", nullable=False),
        sa.Column("recovery_checkpoint", postgresql.JSONB(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        *_tenant_columns(),
    )
    op.create_index("ix_consultation_session_organization_id", "consultation_session", ["organization_id"])
    op.create_index("ix_consultation_session_encounter_id", "consultation_session", ["encounter_id"])

    op.create_table(
        "session_recording",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("consultation_session.id"),
            nullable=False,
        ),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("checksum", sa.String(length=128), nullable=True),
        sa.Column("last_seq", sa.Integer(), server_default="0", nullable=False),
        *_tenant_columns(),
    )
    op.create_index("ix_session_recording_session_id", "session_recording", ["session_id"])

    op.create_table(
        "transcript_segment",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("consultation_session.id"),
            nullable=False,
        ),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("speaker", sa.String(length=32), nullable=False),
        sa.Column("language", sa.String(length=8), server_default="en", nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("corrected_text", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("start_ms", sa.Integer(), nullable=False),
        sa.Column("end_ms", sa.Integer(), nullable=False),
        sa.Column("is_corrected", sa.Boolean(), server_default="false", nullable=False),
        *_tenant_columns(),
    )
    op.create_index("ix_transcript_segment_session_id", "transcript_segment", ["session_id"])
    op.create_index("ix_transcript_segment_session_seq", "transcript_segment", ["session_id", "seq"], unique=True)

    op.create_table(
        "clinical_note",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("consultation_session.id"),
            nullable=False,
        ),
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("encounter.id"), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("patient.id"), nullable=False),
        sa.Column("addendum_of_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clinical_note.id"), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="draft", nullable=False),
        sa.Column("content", postgresql.JSONB(), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=True),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("signed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("user.id"), nullable=True),
        *_tenant_columns(),
    )
    op.create_index("ix_clinical_note_session_id", "clinical_note", ["session_id"])

    for table in TENANT_TABLES:
        _enable_tenant_rls(table)
        _grant_app_role(table)


def downgrade() -> None:
    for table in TENANT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table}")
        op.execute(f"REVOKE ALL PRIVILEGES ON {table} FROM {APP_ROLE}")

    op.drop_table("clinical_note")
    op.drop_table("transcript_segment")
    op.drop_table("session_recording")
    op.drop_table("consultation_session")
    op.drop_table("consent_record")
