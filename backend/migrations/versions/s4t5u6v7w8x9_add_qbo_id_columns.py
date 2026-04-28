"""add qbo_id columns to clients, invoices, payments, expenses, credit_memos

Revision ID: s4t5u6v7w8x9
Revises: r3m4n5o6p7q8
Create Date: 2026-04-27
"""
from alembic import op
import sqlalchemy as sa

revision = 's4t5u6v7w8x9'
down_revision = 'add_exclude_from_ar_aging'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('clients', sa.Column('qbo_id', sa.String(20), nullable=True, unique=True))
    op.add_column('invoices', sa.Column('qbo_id', sa.String(20), nullable=True, unique=True))
    op.add_column('payments', sa.Column('qbo_id', sa.String(20), nullable=True, unique=True))
    op.add_column('expenses', sa.Column('qbo_id', sa.String(30), nullable=True, unique=True))
    op.add_column('credit_memos', sa.Column('qbo_id', sa.String(20), nullable=True, unique=True))
    op.add_column('chart_of_accounts', sa.Column('qbo_id', sa.String(20), nullable=True, unique=True))


def downgrade():
    op.drop_column('chart_of_accounts', 'qbo_id')
    op.drop_column('credit_memos', 'qbo_id')
    op.drop_column('expenses', 'qbo_id')
    op.drop_column('payments', 'qbo_id')
    op.drop_column('invoices', 'qbo_id')
    op.drop_column('clients', 'qbo_id')
