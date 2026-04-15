"""Add email_templates table

Revision ID: f1a2b3c4d5e6
Revises: e8a3b4c5d6e7
Create Date: 2026-04-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = 'e8a3b4c5d6e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum type
    email_template_type = sa.Enum(
        'new_invoice',
        'reminder_invoice',
        'invoice_past_due',
        'suspension_invoice',
        'cancellation_invoice',
        'paid_invoice',
        'credit_memo_issued',
        'payment_failed',
        'default',
        name='emailtemplatetype'
    )
    email_template_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'email_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('template_type', email_template_type, nullable=False),
        sa.Column('subject', sa.String(255), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('template_type', name='uq_email_templates_template_type')
    )


def downgrade() -> None:
    op.drop_table('email_templates')

    email_template_type = sa.Enum(
        'new_invoice',
        'reminder_invoice',
        'invoice_past_due',
        'suspension_invoice',
        'cancellation_invoice',
        'paid_invoice',
        'credit_memo_issued',
        'payment_failed',
        'default',
        name='emailtemplatetype'
    )
    email_template_type.drop(op.get_bind(), checkfirst=True)
