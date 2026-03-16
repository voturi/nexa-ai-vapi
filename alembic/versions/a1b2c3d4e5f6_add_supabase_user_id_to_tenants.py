"""Add supabase_user_id to tenants

Revision ID: a1b2c3d4e5f6
Revises: dafb89cb3602
Create Date: 2026-03-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'dafb89cb3602'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('tenants', sa.Column('supabase_user_id', sa.String(length=255), nullable=True))
    op.create_unique_constraint('uq_tenants_supabase_user_id', 'tenants', ['supabase_user_id'])


def downgrade() -> None:
    op.drop_constraint('uq_tenants_supabase_user_id', 'tenants', type_='unique')
    op.drop_column('tenants', 'supabase_user_id')
