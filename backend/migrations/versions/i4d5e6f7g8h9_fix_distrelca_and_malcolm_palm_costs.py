"""Fix Distrelca and Malcolm Palm renewal costs

Revision ID: i4d5e6f7g8h9
Revises: h3c4d5e6f7g8
Create Date: 2026-04-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'i4d5e6f7g8h9'
down_revision: Union[str, None] = 'h3c4d5e6f7g8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Distrelca - private domain registration at $30/year
    op.execute(
        "UPDATE domains SET renewal_cost = 30.00 WHERE client_id = 74"
    )

    # Malcolm Palm - all domains at $36/year
    op.execute(
        "UPDATE domains SET renewal_cost = 36.00 WHERE client_id = 112"
    )


def downgrade() -> None:
    pass
