"""post_status_bugfix

Revision ID: be6bc6812118
Revises: e91b3c5a7f04
Create Date: 2026-08-25 00:10:23.706268

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'be6bc6812118'
down_revision: Union[str, Sequence[str], None] = 'e91b3c5a7f04'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint("poststatus", "posts", type_="check")
    op.create_check_constraint(
        "poststatus",
        "posts",
        "status IN ('DRAFT', 'SCHEDULED', 'PUBLISHING', 'PUBLISHED', 'FAILED')"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("poststatus", "posts", type_="check")
    op.create_check_constraint(
        "poststatus",
        "posts",
        "status IN ('DRAFT', 'PUBLISHED', 'FAILED')"
    )
