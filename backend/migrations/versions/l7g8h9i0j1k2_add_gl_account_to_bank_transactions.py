"""Add gl_account field to bank_transactions.

Revision ID: l7g8h9i0j1k2
Revises: k6f7g8h9i0j1
Create Date: 2026-04-18

"""
from alembic import op
import sqlalchemy as sa


revision = 'l7g8h9i0j1k2'
down_revision = 'k6f7g8h9i0j1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('bank_transactions', sa.Column('gl_account', sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column('bank_transactions', 'gl_account')
