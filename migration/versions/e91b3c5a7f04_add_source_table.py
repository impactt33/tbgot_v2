"""add sources table

Revision ID: e91b3c5a7f04
Revises: c4f0a1b7d2e3
Create Date: 2026-08-23 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'e91b3c5a7f04'
down_revision: Union[str, Sequence[str], None] = 'c4f0a1b7d2e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'sources',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('channel_id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(length=127), nullable=True),
        sa.Column('url', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('used_in_post', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['channel_id'], ['channels.channel_id'],
                                name=op.f('fk_sources_channel_id_channels'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['used_in_post'], ['posts.id'],
                                name=op.f('fk_sources_used_in_post_posts'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_sources')),
        sa.UniqueConstraint('channel_id', 'url', name='uq_channel_source_url'),
    )
    op.create_index(
        'ix_sources_unused', 'sources', ['channel_id'], unique=False,
        postgresql_where=sa.text('used_in_post IS NULL'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_sources_unused', table_name='sources',
                  postgresql_where=sa.text('used_in_post IS NULL'))
    op.drop_table('sources')

    op.drop_constraint("poststatus", "posts", type_="check")