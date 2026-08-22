"""user role to check constraint

Revision ID: 0ae6ee00b92b
Revises: 6aa8c7b2378b
Create Date: 2026-08-21 21:53:06.470365

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0ae6ee00b92b'
down_revision: Union[str, Sequence[str], None] = '6aa8c7b2378b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ROLES = ("ADMIN", "USER", "NONE")
_USERROLE = postgresql.ENUM(*_ROLES, name="userrole", create_type=False)


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TABLE users ALTER COLUMN role DROP DEFAULT")
    op.alter_column(
        "users",
        "role",
        existing_type=_USERROLE,
        type_=sa.String(length=16),
        existing_nullable=False,
        postgresql_using="role::text",
    )
    op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'NONE'")
    op.execute("DROP TYPE IF EXISTS userrole")
    op.create_check_constraint(
        "userrole",
        "users",
        "role IN ('ADMIN', 'USER', 'NONE')",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("userrole", "users", type_="check")
    op.execute("ALTER TABLE users ALTER COLUMN role DROP DEFAULT")
    postgresql.ENUM(*_ROLES, name="userrole").create(op.get_bind(), checkfirst=True)
    op.alter_column(
        "users",
        "role",
        existing_type=sa.String(length=16),
        type_=_USERROLE,
        existing_nullable=False,
        postgresql_using="role::userrole",
    )
    op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'NONE'")