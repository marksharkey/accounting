"""Replace billing_type enum with authnet_recurring boolean

Revision ID: d7f2e1c5a6b9
Revises: c9d8e2f3a1b4
Create Date: 2026-04-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd7f2e1c5a6b9'
down_revision: Union[str, None] = 'c9d8e2f3a1b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add the new authnet_recurring column (default False)
    op.add_column('clients', sa.Column('authnet_recurring', sa.Boolean(), nullable=False, server_default='0'))

    # Backfill: set to True where billing_type was 'authnet_recurring'
    op.execute("UPDATE clients SET authnet_recurring = TRUE WHERE billing_type = 'authnet_recurring'")

    # Drop the old billing_type column
    op.drop_column('clients', 'billing_type')


def downgrade() -> None:
    # Add back the billing_type column
    op.add_column('clients', sa.Column('billing_type', sa.Enum('authnet_recurring', 'fixed_recurring', 'mixed', 'one_off', name='billingtype'), nullable=False, server_default='fixed_recurring'))

    # Backfill from authnet_recurring
    op.execute("UPDATE clients SET billing_type = 'authnet_recurring' WHERE authnet_recurring = TRUE")
    op.execute("UPDATE clients SET billing_type = 'fixed_recurring' WHERE authnet_recurring = FALSE")

    # Drop the authnet_recurring column
    op.drop_column('clients', 'authnet_recurring')
