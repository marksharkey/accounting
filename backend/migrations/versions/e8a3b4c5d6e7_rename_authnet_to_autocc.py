"""Rename auth.net references to AutoCC

Revision ID: e8a3b4c5d6e7
Revises: d7f2e1c5a6b9
Create Date: 2026-04-15 10:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e8a3b4c5d6e7'
down_revision: Union[str, None] = 'd7f2e1c5a6b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename columns in clients table
    op.execute("ALTER TABLE clients RENAME COLUMN authnet_recurring TO autocc_recurring")
    op.execute("ALTER TABLE clients RENAME COLUMN authnet_customer_id TO autocc_customer_id")

    # Rename columns in billing_schedules table
    op.execute("ALTER TABLE billing_schedules RENAME COLUMN authnet_recurring TO autocc_recurring")

    # Rename columns in invoices table
    op.execute("ALTER TABLE invoices RENAME COLUMN authnet_verified TO autocc_verified")
    op.execute("ALTER TABLE invoices RENAME COLUMN authnet_transaction_id TO autocc_transaction_id")

    # Update payment method enum: authnet -> autocc
    # First, update any existing payment records
    op.execute("UPDATE payments SET method = 'autocc' WHERE method = 'authnet'")


def downgrade() -> None:
    # Rename columns back in clients table
    op.execute("ALTER TABLE clients RENAME COLUMN autocc_recurring TO authnet_recurring")
    op.execute("ALTER TABLE clients RENAME COLUMN autocc_customer_id TO authnet_customer_id")

    # Rename columns back in billing_schedules table
    op.execute("ALTER TABLE billing_schedules RENAME COLUMN autocc_recurring TO authnet_recurring")

    # Rename columns back in invoices table
    op.execute("ALTER TABLE invoices RENAME COLUMN autocc_verified TO authnet_verified")
    op.execute("ALTER TABLE invoices RENAME COLUMN autocc_transaction_id TO authnet_transaction_id")

    # Revert payment method enum: autocc -> authnet
    op.execute("UPDATE payments SET method = 'authnet' WHERE method = 'autocc'")
