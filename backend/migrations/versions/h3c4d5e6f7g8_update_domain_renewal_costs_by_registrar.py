"""Update domain renewal costs by registrar and client

Revision ID: h3c4d5e6f7g8
Revises: g2b3c4d5e6f7
Create Date: 2026-04-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'h3c4d5e6f7g8'
down_revision: Union[str, None] = 'g2b3c4d5e6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Terriann Muller - 5 domains at $36/year
    op.execute(
        "UPDATE domains SET renewal_cost = 36.00 WHERE client_id = 185"
    )

    # Malcolm Palm - 3 domains at $30/year
    op.execute(
        "UPDATE domains SET renewal_cost = 30.00 WHERE client_id = 112"
    )

    # .ca domains - $36/year
    op.execute(
        "UPDATE domains SET renewal_cost = 36.00 WHERE domain_name LIKE '%.ca'"
    )

    # .net domains - $36/year
    op.execute(
        "UPDATE domains SET renewal_cost = 36.00 WHERE domain_name LIKE '%.net'"
    )

    # ravenmoonbooks.com client - all domains at $50/year
    op.execute(
        "UPDATE domains SET renewal_cost = 50.00 WHERE client_id = 143"
    )

    # Zysk Bros., Inc - $50/year
    op.execute(
        "UPDATE domains SET renewal_cost = 50.00 WHERE client_id = 202"
    )

    # DSSTITLE - $50/year
    op.execute(
        "UPDATE domains SET renewal_cost = 50.00 WHERE client_id = 58"
    )


def downgrade() -> None:
    # No downgrade - pricing updates should be permanent
    pass
