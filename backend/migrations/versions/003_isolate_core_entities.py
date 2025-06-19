"""isolate_core_entities

Revision ID: 003_isolate_core_entities
Revises: 002_papers_workspaces
Create Date: 2025-01-12 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003_isolate_core_entities'
down_revision: Union[str, None] = '002_papers_workspaces'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add workspace_id to core data entities"""
    
    # 1. Add workspace_id to paper_sections
    op.add_column('paper_sections', sa.Column('workspace_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'paper_sections_workspace_id_fkey',
        'paper_sections', 'workspaces',
        ['workspace_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_index('idx_paper_sections_workspace_id', 'paper_sections', ['workspace_id'])
    
    # 2. Add workspace_id to sentences
    op.add_column('sentences', sa.Column('workspace_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'sentences_workspace_id_fkey',
        'sentences', 'workspaces',
        ['workspace_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_index('idx_sentences_workspace_id', 'sentences', ['workspace_id'])
    
    # 3. Update paper_selections
    op.add_column('paper_selections', sa.Column('workspace_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'paper_selections_workspace_id_fkey',
        'paper_selections', 'workspaces',
        ['workspace_id'], ['id'],
        ondelete='CASCADE'
    )
    
    # Drop the existing unique constraint on paper_id
    op.drop_constraint('paper_selections_paper_id_key', 'paper_selections', type_='unique')
    
    # Create new composite unique constraint on (workspace_id, paper_id)
    op.create_unique_constraint(
        'paper_selections_workspace_paper_key',
        'paper_selections',
        ['workspace_id', 'paper_id']
    )
    
    # Create index for performance
    op.create_index('idx_paper_selections_workspace_id', 'paper_selections', ['workspace_id'])
    
    # Note: Data migration to populate workspace_id values will be handled in DB-06


def downgrade() -> None:
    """Remove workspace_id from core data entities"""
    
    # 1. Revert paper_selections changes
    op.drop_constraint('paper_selections_workspace_paper_key', 'paper_selections', type_='unique')
    op.drop_index('idx_paper_selections_workspace_id')
    op.drop_constraint('paper_selections_workspace_id_fkey', 'paper_selections', type_='foreignkey')
    op.drop_column('paper_selections', 'workspace_id')
    
    # Restore original unique constraint on paper_id
    op.create_unique_constraint('paper_selections_paper_id_key', 'paper_selections', ['paper_id'])
    
    # 2. Revert sentences changes
    op.drop_index('idx_sentences_workspace_id')
    op.drop_constraint('sentences_workspace_id_fkey', 'sentences', type_='foreignkey')
    op.drop_column('sentences', 'workspace_id')
    
    # 3. Revert paper_sections changes
    op.drop_index('idx_paper_sections_workspace_id')
    op.drop_constraint('paper_sections_workspace_id_fkey', 'paper_sections', type_='foreignkey')
    op.drop_column('paper_sections', 'workspace_id') 