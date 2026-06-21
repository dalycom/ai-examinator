"""Seed system permissions and roles."""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa

from alembic import op
from app.modules.rbac.constants import SYSTEM_PERMISSIONS, SYSTEM_ROLES

revision: str = "0002_seed_rbac"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    permission_ids: dict[str, str] = {}

    for key, description in SYSTEM_PERMISSIONS:
        permission_id = str(uuid4())
        permission_ids[key] = permission_id
        connection.execute(
            sa.text(
                """
                INSERT INTO permission (id, key, description, created_at, updated_at)
                VALUES (:id, :key, :description, now(), now())
                """
            ),
            {"id": permission_id, "key": key, "description": description},
        )

    for role_key, permission_keys in SYSTEM_ROLES.items():
        role_id = str(uuid4())
        connection.execute(
            sa.text(
                """
                INSERT INTO role (id, organization_id, key, name, is_system, created_at, updated_at)
                VALUES (:id, NULL, :key, :name, true, now(), now())
                """
            ),
            {"id": role_id, "key": role_key, "name": role_key.replace("_", " ").title()},
        )
        for permission_key in permission_keys:
            connection.execute(
                sa.text(
                    """
                    INSERT INTO role_permission (role_id, permission_id)
                    VALUES (:role_id, :permission_id)
                    """
                ),
                {"role_id": role_id, "permission_id": permission_ids[permission_key]},
            )


def downgrade() -> None:
    op.execute("DELETE FROM role_permission")
    op.execute("DELETE FROM role")
    op.execute("DELETE FROM permission")
