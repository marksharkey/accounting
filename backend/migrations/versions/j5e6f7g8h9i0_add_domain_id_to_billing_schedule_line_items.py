"""Add domain_id to billing_schedule_line_items

Revision ID: j5e6f7g8h9i0
Revises: i4d5e6f7g8h9
Create Date: 2026-04-17 22:54:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'j5e6f7g8h9i0'
down_revision: Union[str, None] = 'i4d5e6f7g8h9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('billing_schedule_line_items', sa.Column('domain_id', sa.Integer(), nullable=True))
    op.create_foreign_key('billing_schedule_line_items_ibfk_domain', 'billing_schedule_line_items', 'domains', ['domain_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint('billing_schedule_line_items_ibfk_domain', 'billing_schedule_line_items', type_='foreignkey')
    op.drop_column('billing_schedule_line_items', 'domain_id')
