"""associate_papers_with_workspaces

Revision ID: 002_papers_workspaces
Revises: 001_users_workspaces_chat
Create Date: 2025-01-12 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_papers_workspaces'
down_revision: Union[str, None] = '001_users_workspaces_chat'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add workspace_id to papers and adjust unique constraints"""
    
    # Add workspace_id column to papers table
    op.add_column('papers', sa.Column('workspace_id', sa.UUID(), nullable=True))
    
    # Add foreign key constraint to workspaces
    op.create_foreign_key(
        'papers_workspace_id_fkey',
        'papers', 'workspaces',
        ['workspace_id'], ['id'],
        ondelete='CASCADE'
    )
    
    # Note: Data migration to populate workspace_id values will be handled in DB-06
    
    # Drop the existing unique constraint on file_hash
    op.drop_constraint('papers_file_hash_key', 'papers', type_='unique')
    
    # Create new composite unique constraint on (workspace_id, file_hash)
    op.create_unique_constraint(
        'papers_workspace_file_hash_key',
        'papers',
        ['workspace_id', 'file_hash']
    )
    
    # Create index for performance
    op.create_index('idx_papers_workspace_id', 'papers', ['workspace_id'])


def downgrade() -> None:
    """Remove workspace_id from papers and restore original constraints"""
    
    # Drop the composite unique constraint
    op.drop_constraint('papers_workspace_file_hash_key', 'papers', type_='unique')
    
    # Drop the workspace index
    op.drop_index('idx_papers_workspace_id')
    
    # Drop the foreign key constraint
    op.drop_constraint('papers_workspace_id_fkey', 'papers', type_='foreignkey')
    
    # Drop the workspace_id column
    op.drop_column('papers', 'workspace_id')
    
    # Restore the original unique constraint on file_hash
    op.create_unique_constraint('papers_file_hash_key', 'papers', ['file_hash']) 