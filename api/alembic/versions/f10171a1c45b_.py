"""empty message

Revision ID: f10171a1c45b
Revises: b64db3c1a268
Create Date: 2026-01-11 19:06:44.320590

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f10171a1c45b'
down_revision: Union[str, Sequence[str], None] = 'b64db3c1a268'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('trade_signals', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True), schema='common')
    op.add_column('trade_signals', sa.Column('score', sa.Float(), nullable=True), schema='common')
    op.add_column('trade_signals', sa.Column('is_favorite', sa.Boolean(), server_default='false', nullable=True), schema='common')
    op.add_column('trade_signals', sa.Column('is_archived', sa.Boolean(), server_default='false', nullable=True), schema='common')

def downgrade() -> None:
    op.drop_column('trade_signals', 'is_archived', schema='common')
    op.drop_column('trade_signals', 'is_favorite', schema='common')
    op.drop_column('trade_signals', 'score', schema='common')
    op.drop_column('trade_signals', 'updated_at', schema='common')
