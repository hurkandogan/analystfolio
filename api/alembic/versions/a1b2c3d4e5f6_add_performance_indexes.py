"""add_performance_indexes

Revision ID: a1b2c3d4e5f6
Revises: f53d92dbd054
Create Date: 2026-05-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f53d92dbd054'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # FundamentalCache: queries group by instrument_id + filter/select by date
    op.create_index(
        'ix_fundamental_cache_instr_date',
        'fundamental_cache',
        ['instrument_id', 'date'],
        schema='common'
    )

    # TradeSignal: queries filter by instrument_id + bot_name + status
    op.create_index(
        'ix_trade_signals_instr_bot_status',
        'trade_signals',
        ['instrument_id', 'bot_name', 'status'],
        schema='common'
    )

    # TradeSignal: queries order by created_at and filter date ranges
    op.create_index(
        'ix_trade_signals_instr_bot_created',
        'trade_signals',
        ['instrument_id', 'bot_name', 'created_at'],
        schema='common'
    )

    # PremiumWatchlist: primary access pattern is always WHERE is_active = true
    op.create_index(
        'ix_premium_watchlist_active',
        'premium_watchlist',
        ['is_active'],
        schema='common'
    )


def downgrade() -> None:
    op.drop_index('ix_premium_watchlist_active', table_name='premium_watchlist', schema='common')
    op.drop_index('ix_trade_signals_instr_bot_created', table_name='trade_signals', schema='common')
    op.drop_index('ix_trade_signals_instr_bot_status', table_name='trade_signals', schema='common')
    op.drop_index('ix_fundamental_cache_instr_date', table_name='fundamental_cache', schema='common')
