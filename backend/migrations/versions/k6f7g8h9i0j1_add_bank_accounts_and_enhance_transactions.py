"""Add bank accounts and enhance transactions.

Revision ID: k6f7g8h9i0j1
Revises: j5e6f7g8h9i0
Create Date: 2026-04-17

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'k6f7g8h9i0j1'
down_revision = 'j5e6f7g8h9i0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create bank_accounts table
    op.create_table(
        'bank_accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_name', sa.String(length=100), nullable=False),
        sa.Column('account_number', sa.String(length=20), nullable=True),
        sa.Column('account_type', sa.String(length=50), nullable=False),
        sa.Column('opening_balance', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_bank_accounts_id'), 'bank_accounts', ['id'])

    # Alter bank_transactions table
    op.add_column('bank_transactions', sa.Column('bank_account_id', sa.Integer(), nullable=True))
    op.add_column('bank_transactions', sa.Column('transaction_type', sa.String(), nullable=True))
    op.add_column('bank_transactions', sa.Column('transaction_number', sa.String(length=50), nullable=True))
    op.add_column('bank_transactions', sa.Column('balance', sa.Numeric(precision=12, scale=2), nullable=True))
    op.add_column('bank_transactions', sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False))
    op.add_column('bank_transactions', sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False))

    # Add foreign key to bank_accounts
    op.create_foreign_key('fk_bank_transactions_bank_account_id', 'bank_transactions', 'bank_accounts', ['bank_account_id'], ['id'])

    # Create bank_reconciliations table
    op.create_table(
        'bank_reconciliations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('bank_account_id', sa.Integer(), nullable=False),
        sa.Column('reconciliation_date', sa.Date(), nullable=False),
        sa.Column('statement_balance', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('cleared_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('difference', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('is_complete', sa.Boolean(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['bank_account_id'], ['bank_accounts.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_bank_reconciliations_id'), 'bank_reconciliations', ['id'])


def downgrade() -> None:
    op.drop_index(op.f('ix_bank_reconciliations_id'), table_name='bank_reconciliations')
    op.drop_table('bank_reconciliations')
    op.drop_constraint('fk_bank_transactions_bank_account_id', 'bank_transactions', type_='foreignkey')
    op.drop_column('bank_transactions', 'updated_at')
    op.drop_column('bank_transactions', 'created_at')
    op.drop_column('bank_transactions', 'balance')
    op.drop_column('bank_transactions', 'transaction_number')
    op.drop_column('bank_transactions', 'transaction_type')
    op.drop_column('bank_transactions', 'bank_account_id')
    op.drop_index(op.f('ix_bank_accounts_id'), table_name='bank_accounts')
    op.drop_table('bank_accounts')
