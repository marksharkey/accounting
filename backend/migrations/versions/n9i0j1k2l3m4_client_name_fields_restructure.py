"""Restructure client name fields to match QBO: add display_name, first_name, last_name; remove contact_name

Revision ID: n9i0j1k2l3m4
Revises: m8h9i0j1k2l3
Create Date: 2026-04-23 17:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'n9i0j1k2l3m4'
down_revision: Union[str, None] = 'm8h9i0j1k2l3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('clients', sa.Column('display_name', sa.String(150), nullable=True))
    op.add_column('clients', sa.Column('first_name', sa.String(75), nullable=True))
    op.add_column('clients', sa.Column('last_name', sa.String(75), nullable=True))
    op.drop_column('clients', 'contact_name')


def downgrade() -> None:
    op.add_column('clients', sa.Column('contact_name', sa.String(100), nullable=True))
    op.drop_column('clients', 'last_name')
    op.drop_column('clients', 'first_name')
    op.drop_column('clients', 'display_name')
