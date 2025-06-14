"""fix_paper_selections_column_name

Revision ID: 1bef6b591f0f
Revises: 6a67a812f326
Create Date: 2025-06-14 19:39:53.078834

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '1bef6b591f0f'
down_revision: Union[str, None] = '6a67a812f326'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename selected_at column to selected_timestamp in paper_selections table"""
    
    # Check if column exists before renaming
    connection = op.get_bind()
    result = connection.execute(text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'paper_selections' 
        AND column_name = 'selected_at'
    """))
    
    if result.fetchone():
        # Rename selected_at to selected_timestamp
        op.execute('ALTER TABLE paper_selections RENAME COLUMN selected_at TO selected_timestamp')
        print("✅ 已將 paper_selections.selected_at 重命名為 selected_timestamp")
    else:
        print("ℹ️  paper_selections 表中已經存在正確的欄位名稱")


def downgrade() -> None:
    """Rename selected_timestamp column back to selected_at in paper_selections table"""
    
    # Check if column exists before renaming
    connection = op.get_bind()
    result = connection.execute(text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'paper_selections' 
        AND column_name = 'selected_timestamp'
    """))
    
    if result.fetchone():
        # Rename selected_timestamp back to selected_at
        op.execute('ALTER TABLE paper_selections RENAME COLUMN selected_timestamp TO selected_at')
        print("⏪ 已將 paper_selections.selected_timestamp 重命名回 selected_at")
    else:
        print("ℹ️  paper_selections 表中沒有 selected_timestamp 欄位")
