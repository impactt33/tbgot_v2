"""post templates table

Revision ID: a3f1c9d20e57
Revises: bdf76a3344c2
Create Date: 2026-09-08 11:20:14.508312

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a3f1c9d20e57'
down_revision: Union[str, Sequence[str], None] = 'bdf76a3344c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('post_templates',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('channel_id', sa.BigInteger(), nullable=False),
    sa.Column('post_type', sa.Enum('QUIZ', 'MATERIAL', 'SOURCES', 'CUSTOM', name='posttype', native_enum=False, create_constraint=True, length=16), nullable=False),
    sa.Column('examples', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('instruction', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['channel_id'], ['channels.channel_id'], name=op.f('fk_post_templates_channel_id_channels'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_post_templates')),
    sa.UniqueConstraint('channel_id', 'post_type', name='uq_post_templates_channel_id_post_type')
    )


def downgrade() -> None:
    """Downgrade schema."""
    # The CHECK is named after the enum type, not the column, and drops with the
    # table. Nothing to undo by hand: ck_post_templates_posttype goes with it.
    op.drop_table('post_templates')
