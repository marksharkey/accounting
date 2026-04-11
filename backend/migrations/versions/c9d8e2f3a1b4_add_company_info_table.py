"""Add company_info table

Revision ID: c9d8e2f3a1b4
Revises: b382e5c4a4a8
Create Date: 2026-04-11 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9d8e2f3a1b4'
down_revision: Union[str, None] = 'b382e5c4a4a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'company_info',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_name', sa.String(150), nullable=False),
        sa.Column('address_line1', sa.String(150), nullable=True),
        sa.Column('address_line2', sa.String(150), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('state', sa.String(50), nullable=True),
        sa.Column('zip_code', sa.String(20), nullable=True),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('email', sa.String(150), nullable=True),
        sa.Column('website_url', sa.String(255), nullable=True),
        sa.Column('logo_filename', sa.String(255), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('company_info')
