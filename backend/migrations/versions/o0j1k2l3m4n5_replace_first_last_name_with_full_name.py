"""Replace first_name and last_name with full_name column

Revision ID: o0j1k2l3m4n5
Revises: n9i0j1k2l3m4
Create Date: 2026-04-23 17:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'o0j1k2l3m4n5'
down_revision: Union[str, None] = 'n9i0j1k2l3m4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('clients', 'first_name')
    op.drop_column('clients', 'last_name')
    op.add_column('clients', sa.Column('full_name', sa.String(150), nullable=True))


def downgrade() -> None:
    op.drop_column('clients', 'full_name')
    op.add_column('clients', sa.Column('last_name', sa.String(75), nullable=True))
    op.add_column('clients', sa.Column('first_name', sa.String(75), nullable=True))
