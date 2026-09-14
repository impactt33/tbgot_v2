"""material reminders table

Revision ID: e00d4ce51236
Revises: a3f1c9d20e57
Create Date: 2026-09-14 13:11:49.843173

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e00d4ce51236'
down_revision: Union[str, Sequence[str], None] = 'a3f1c9d20e57'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('material_reminders',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('channel_id', sa.BigInteger(), nullable=False),
    sa.Column('enabled', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('interval_hours', sa.Integer(), nullable=False),
    sa.Column('work_start', sa.SmallInteger(), nullable=True),
    sa.Column('work_end', sa.SmallInteger(), nullable=True),
    sa.Column('next_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('message_id', sa.BigInteger(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('(work_start IS NULL) = (work_end IS NULL)', name=op.f('ck_material_reminders_working_hours_pair')),
    sa.CheckConstraint('interval_hours BETWEEN 1 AND 168', name=op.f('ck_material_reminders_interval_hours_range')),
    sa.CheckConstraint('work_start >= 0 AND work_start < 1440 AND work_end >= 0 AND work_end < 1440 AND work_start <> work_end', name=op.f('ck_material_reminders_working_hours_range')),
    sa.ForeignKeyConstraint(['channel_id'], ['channels.channel_id'], name=op.f('fk_material_reminders_channel_id_channels'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_material_reminders_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_material_reminders')),
    sa.UniqueConstraint('user_id', 'channel_id', name='uq_material_reminders_user_id_channel_id')
    )
    op.create_index('ix_material_reminders_due', 'material_reminders', ['next_at'], unique=False, postgresql_where=sa.text('enabled'))


def downgrade() -> None:
    """Downgrade schema."""
    # The three CHECKs go with the table. They are in upgrade() despite
    # include_object in env.py: that filter only hides CHECK drift on tables
    # that already exist, and a new table is rendered whole.
    op.drop_index('ix_material_reminders_due', table_name='material_reminders', postgresql_where=sa.text('enabled'))
    op.drop_table('material_reminders')
