"""create tenants and users

Revision ID: 0001_tenants_users
Revises:
Create Date: 2026-08-20

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_tenants_users"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    tenant_status = postgresql.ENUM("ACTIVE", "SUSPENDED", "ARCHIVED", name="tenant_status")
    user_role = postgresql.ENUM(
        "OWNER",
        "ADMIN",
        "HR",
        "LEGAL",
        "COMPLIANCE",
        "FINANCE",
        "MANAGER",
        "EXECUTIVE",
        "AUDITOR",
        "WORKER",
        "EXTERNAL",
        name="user_role",
    )
    tenant_status.create(op.get_bind(), checkfirst=True)
    user_role.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM("ACTIVE", "SUSPENDED", "ARCHIVED", name="tenant_status", create_type=False),
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"], unique=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM(
                "OWNER",
                "ADMIN",
                "HR",
                "LEGAL",
                "COMPLIANCE",
                "FINANCE",
                "MANAGER",
                "EXECUTIVE",
                "AUDITOR",
                "WORKER",
                "EXTERNAL",
                name="user_role",
                create_type=False,
            ),
            nullable=False,
            server_default="WORKER",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
    )
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])
    op.create_index("ix_users_email", "users", ["email"])


def downgrade() -> None:
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_tenant_id", table_name="users")
    op.drop_table("users")
    op.drop_index("ix_tenants_slug", table_name="tenants")
    op.drop_table("tenants")
    postgresql.ENUM(name="user_role").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="tenant_status").drop(op.get_bind(), checkfirst=True)
