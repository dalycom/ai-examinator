"""Phase 4 AI clinical assistant schema with tenant RLS."""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0006_phase4_ai"
down_revision: str | None = "0005_phase3_consultation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "ai_examinator_app"

TENANT_TABLES = [
    "ai_provenance",
    "ai_extraction_run",
    "extracted_fact",
    "ai_suggestion",
    "feature_flag",
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
        "prompt_version",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("template_ref", sa.String(length=128), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_prompt_version_key_version", "prompt_version", ["key", "version"], unique=True)

    op.create_table(
        "ai_provenance",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("model_id", sa.String(length=128), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("input_hash", sa.String(length=128), nullable=False),
        sa.Column("parameters", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("generation_timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        *_tenant_columns(data_classification_default="internal"),
    )
    op.create_index("ix_ai_provenance_organization_id", "ai_provenance", ["organization_id"])

    op.create_table(
        "ai_extraction_run",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("consultation_session.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("draft_note", postgresql.JSONB(), nullable=True),
        sa.Column("provenance_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_provenance.id"), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *_tenant_columns(data_classification_default="phi"),
    )
    op.create_index("ix_ai_extraction_run_session_id", "ai_extraction_run", ["session_id"])

    op.create_table(
        "extracted_fact",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("consultation_session.id"),
            nullable=False,
        ),
        sa.Column(
            "extraction_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ai_extraction_run.id"),
            nullable=False,
        ),
        sa.Column("fact_type", sa.String(length=64), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column(
            "source_segment_ref",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("transcript_segment.id"),
            nullable=False,
        ),
        sa.Column("confidence_level", sa.String(length=16), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("provenance_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_provenance.id"), nullable=False),
        *_tenant_columns(data_classification_default="sensitive_phi"),
    )
    op.create_index("ix_extracted_fact_session_id", "extracted_fact", ["session_id"])

    op.create_table(
        "ai_suggestion",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("consultation_session.id"),
            nullable=False,
        ),
        sa.Column(
            "extraction_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ai_extraction_run.id"),
            nullable=False,
        ),
        sa.Column("suggestion_type", sa.String(length=64), nullable=False),
        sa.Column("concept", postgresql.JSONB(), nullable=False),
        sa.Column("supporting_facts", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("missing_information", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("conflicting_information", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("confidence_level", sa.String(length=16), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("red_flag_warnings", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("source_references", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("uncertainty_notes", sa.Text(), nullable=True),
        sa.Column("decision_status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("decided_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("user.id"), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("edited_value", postgresql.JSONB(), nullable=True),
        sa.Column("provenance_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_provenance.id"), nullable=False),
        *_tenant_columns(data_classification_default="phi"),
    )
    op.create_index("ix_ai_suggestion_session_id", "ai_suggestion", ["session_id"])

    op.create_table(
        "feature_flag",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("description", sa.String(length=256), nullable=True),
        *_tenant_columns(data_classification_default="internal"),
    )
    op.create_index("ix_feature_flag_org_key", "feature_flag", ["organization_id", "key"], unique=True)

    op.create_table(
        "eval_dataset",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("items", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("is_synthetic", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "eval_run",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("eval_dataset.id"), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("metrics", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("passed_gates", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.execute(
        """
        INSERT INTO prompt_version (id, key, version, template_ref, is_active, created_at, updated_at)
        VALUES (
            gen_random_uuid(),
            'clinical_extraction',
            'stub-extraction-v1',
            'prompts/stub-extraction-v1.txt',
            true,
            now(),
            now()
        )
        """
    )

    for table in TENANT_TABLES:
        _enable_tenant_rls(table)
        _grant_app_role(table)

    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON prompt_version TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON eval_dataset TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON eval_run TO {APP_ROLE}")


def downgrade() -> None:
    for table in TENANT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table}")
        op.execute(f"REVOKE ALL PRIVILEGES ON {table} FROM {APP_ROLE}")

    op.execute(f"REVOKE ALL PRIVILEGES ON eval_run FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL PRIVILEGES ON eval_dataset FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL PRIVILEGES ON prompt_version FROM {APP_ROLE}")

    op.drop_table("eval_run")
    op.drop_table("eval_dataset")
    op.drop_table("feature_flag")
    op.drop_table("ai_suggestion")
    op.drop_table("extracted_fact")
    op.drop_table("ai_extraction_run")
    op.drop_table("ai_provenance")
    op.drop_table("prompt_version")
