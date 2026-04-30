"""convert_to_hypertable

Revision ID: 107d9b8f614b
Revises: 9a057eeb5700
Create Date: 2026-01-08 20:44:15.386907

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '107d9b8f614b'
down_revision: Union[str, Sequence[str], None] = '9a057eeb5700'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE")

    op.execute("""
        SELECT create_hypertable(
            'common.market_data_cache', 
            'timestamp', 
            if_not_exists => TRUE,
            migrate_data => TRUE
        );
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_symbol_time 
        ON common.market_data_cache (instrument_id, timestamp DESC);
    """)


def downgrade() -> None:
    """Downgrade schema."""
    pass
