"""fix_remote_server_column_name

Revision ID: b7c75e7ad4e6
Revises: 1bef6b591f0f
Create Date: 2025-06-14 11:46:01.332286

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7c75e7ad4e6'
down_revision: Union[str, None] = '1bef6b591f0f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
