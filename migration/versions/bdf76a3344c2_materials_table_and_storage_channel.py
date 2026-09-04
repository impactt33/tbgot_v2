"""materials table and storage channel

Revision ID: bdf76a3344c2
Revises: 49f8db4f9968
Create Date: 2026-09-04 21:41:02.900819

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bdf76a3344c2'
down_revision: Union[str, Sequence[str], None] = '49f8db4f9968'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('materials',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('channel_id', sa.BigInteger(), nullable=False),
    sa.Column('file_unique_id', sa.String(length=127), nullable=False),
    sa.Column('source_chat_id', sa.BigInteger(), nullable=True),
    sa.Column('source_username', sa.String(length=63), nullable=True),
    sa.Column('source_message_id', sa.BigInteger(), nullable=True),
    sa.Column('storage_chat_id', sa.BigInteger(), nullable=False),
    sa.Column('storage_message_id', sa.BigInteger(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('used_in_post', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['channel_id'], ['channels.channel_id'], name=op.f('fk_materials_channel_id_channels'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['used_in_post'], ['posts.id'], name=op.f('fk_materials_used_in_post_posts'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_materials')),
    sa.UniqueConstraint('channel_id', 'file_unique_id', name='uq_channel_material_file')
    )
    op.create_index('ix_materials_unused', 'materials', ['channel_id'], unique=False, postgresql_where=sa.text('used_in_post IS NULL'))
    # Nullable, and no foreign key: a storage channel is not a posting target
    # and has no row in channels. A news channel keeps it NULL.
    op.add_column('channels', sa.Column('storage_channel_id', sa.BigInteger(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('channels', 'storage_channel_id')
    op.drop_index('ix_materials_unused', table_name='materials', postgresql_where=sa.text('used_in_post IS NULL'))
    op.drop_table('materials')
