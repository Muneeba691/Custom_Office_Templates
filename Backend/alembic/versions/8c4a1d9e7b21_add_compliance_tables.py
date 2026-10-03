"""add compliance tables

Revision ID: 8c4a1d9e7b21
Revises: 217f3522ba45
Create Date: 2026-09-30 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '8c4a1d9e7b21'
down_revision: Union[str, None] = '217f3522ba45'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'compliance_rules',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('country', sa.String(length=2), nullable=False),
        sa.Column('rule_key', sa.String(length=100), nullable=False),
        sa.Column('rule_value', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'country', 'rule_key', name='uq_compliance_rules_tenant_country_key'),
    )
    op.create_index(op.f('ix_compliance_rules_country'), 'compliance_rules', ['country'], unique=False)
    op.create_index(op.f('ix_compliance_rules_tenant_id'), 'compliance_rules', ['tenant_id'], unique=False)

    op.create_table(
        'compliance_cases',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('worker_id', sa.UUID(), nullable=False),
        sa.Column('rule_id', sa.UUID(), nullable=True),
        sa.Column('rule_key', sa.String(length=100), nullable=False),
        sa.Column(
            'evaluation_status',
            sa.Enum('KNOWN', 'REVIEW_REQUIRED', 'UNKNOWN', name='compliance_evaluation_status'),
            nullable=False,
        ),
        sa.Column(
            'status',
            sa.Enum('OPEN', 'UNDER_REVIEW', 'RESOLVED', name='compliance_case_status'),
            nullable=False,
        ),
        sa.Column('notes', sa.String(length=2000), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['rule_id'], ['compliance_rules.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['worker_id'], ['workers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_compliance_cases_rule_id'), 'compliance_cases', ['rule_id'], unique=False)
    op.create_index(op.f('ix_compliance_cases_tenant_id'), 'compliance_cases', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_compliance_cases_worker_id'), 'compliance_cases', ['worker_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_compliance_cases_worker_id'), table_name='compliance_cases')
    op.drop_index(op.f('ix_compliance_cases_tenant_id'), table_name='compliance_cases')
    op.drop_index(op.f('ix_compliance_cases_rule_id'), table_name='compliance_cases')
    op.drop_table('compliance_cases')
    op.drop_index(op.f('ix_compliance_rules_tenant_id'), table_name='compliance_rules')
    op.drop_index(op.f('ix_compliance_rules_country'), table_name='compliance_rules')
    op.drop_table('compliance_rules')
    sa.Enum(name='compliance_evaluation_status').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='compliance_case_status').drop(op.get_bind(), checkfirst=True)
