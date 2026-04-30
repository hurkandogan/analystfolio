"""empty message

Revision ID: b64db3c1a268
Revises: bab8258584e0
Create Date: 2026-01-10 22:31:18.215685

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b64db3c1a268'
down_revision: Union[str, Sequence[str], None] = 'bab8258584e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('bot_states', sa.Column('is_auto_run', sa.Boolean(), nullable=True), schema='common')
    op.add_column('bot_states', sa.Column('run_interval_mins', sa.Integer(), nullable=True), schema='common')


def downgrade() -> None:
    op.drop_column('bot_states', 'run_interval_mins', schema='common')
    op.drop_column('bot_states', 'is_auto_run', schema='common')
