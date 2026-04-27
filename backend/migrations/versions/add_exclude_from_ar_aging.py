"""Add exclude_from_ar_aging flag to invoices

Revision ID: add_exclude_from_ar_aging
Revises: r3m4n5o6p7q8
Create Date: 2026-04-26 19:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_exclude_from_ar_aging'
down_revision: Union[str, None] = 'r3m4n5o6p7q8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('invoices', sa.Column('exclude_from_ar_aging', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column('invoices', 'exclude_from_ar_aging')
