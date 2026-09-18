"""create users table

Revision ID: 0001_create_users
Revises:
Create Date: 2026-09-18

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_create_users"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), sa.Identity(start=1, increment=1), nullable=False),
        sa.Column("external_id", sa.Unicode(length=255), nullable=True),
        sa.Column("email", sa.Unicode(length=255), nullable=False),
        sa.Column("first_name", sa.Unicode(length=100), nullable=True),
        sa.Column("last_name", sa.Unicode(length=100), nullable=True),
        sa.Column("role", sa.Unicode(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.sysutcdatetime(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.sysutcdatetime(),
            nullable=False,
        ),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index(
        "uq_users_external_id",
        "users",
        ["external_id"],
        unique=True,
        mssql_where=sa.text("[external_id] IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_users_external_id", table_name="users")
    op.drop_table("users")
