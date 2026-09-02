"""CUSTOM post type added

Revision ID: 49f8db4f9968
Revises: be6bc6812118
Create Date: 2026-09-02 11:32:43.398869

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '49f8db4f9968'
down_revision: Union[str, Sequence[str], None] = 'be6bc6812118'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
CONSTRAINT = "posttype"

def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint(CONSTRAINT, "posts", type_="check")
    op.create_check_constraint(
        CONSTRAINT, "posts",
        "post_type IN ('QUIZ', 'MATERIAL', 'SOURCES', 'CUSTOM')",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(CONSTRAINT, "posts", type_="check")
    op.create_check_constraint(
        CONSTRAINT, "posts",
        "post_type IN ('QUIZ', 'MATERIAL', 'SOURCES')",
    )