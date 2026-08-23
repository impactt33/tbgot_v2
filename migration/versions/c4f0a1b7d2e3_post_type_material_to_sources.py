"""post type: MATERIAL -> SOURCES

Revision ID: c4f0a1b7d2e3
Revises: 0ae6ee00b92b
Create Date: 2026-08-23 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = 'c4f0a1b7d2e3'
down_revision: Union[str, Sequence[str], None] = '0ae6ee00b92b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Widen the constraint first: rows still hold MATERIAL while we rewrite them.
    op.drop_constraint("posttype", "posts", type_="check")
    op.execute("UPDATE posts SET post_type = 'SOURCES' WHERE post_type = 'MATERIAL'")
    op.create_check_constraint(
        "posttype",
        "posts",
        "post_type IN ('QUIZ', 'SOURCES')",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("posttype", "posts", type_="check")
    op.execute("UPDATE posts SET post_type = 'MATERIAL' WHERE post_type = 'SOURCES'")
    op.create_check_constraint(
        "posttype",
        "posts",
        "post_type IN ('QUIZ', 'MATERIAL', 'SOURCES')",
    )