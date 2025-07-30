"""refactor

Revision ID: 61eb8e8ff78c
Revises: 5f40f7c312a6
Create Date: 2025-07-29 14:15:41.696323

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '61eb8e8ff78c'
down_revision: Union[str, None] = '5f40f7c312a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_table('top_lots')
    


def downgrade() -> None:
    """Downgrade schema."""
    pass
