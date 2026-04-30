"""convert_to_hypertable

Revision ID: 74b3a9e85818
Revises: 107d9b8f614b
Create Date: 2026-01-08 20:48:33.279767

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '74b3a9e85818'
down_revision: Union[str, Sequence[str], None] = '107d9b8f614b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
