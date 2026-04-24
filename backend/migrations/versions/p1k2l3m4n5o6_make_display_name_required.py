"""Make display_name required (NOT NULL)

Revision ID: p1k2l3m4n5o6
Revises: o0j1k2l3m4n5
Create Date: 2026-04-23 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'p1k2l3m4n5o6'
down_revision: Union[str, None] = 'o0j1k2l3m4n5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('clients', 'display_name',
               existing_type=sa.String(150),
               nullable=False)


def downgrade() -> None:
    op.alter_column('clients', 'display_name',
               existing_type=sa.String(150),
               nullable=True)
