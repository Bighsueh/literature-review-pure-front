"""isolate_processing_entities

Revision ID: 004_isolate_processing_entities
Revises: 003_isolate_core_entities
Create Date: 2025-01-12 11:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '004_isolate_processing_entities'
down_revision: Union[str, None] = '003_isolate_core_entities'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add workspace_id to processing-related entities"""
    
    # 1. Add workspace_id to processing_queue
    op.add_column('processing_queue', sa.Column('workspace_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'processing_queue_workspace_id_fkey',
        'processing_queue', 'workspaces',
        ['workspace_id'], ['id'],
        ondelete='CASCADE'
    )
    op.create_index('idx_processing_queue_workspace_id', 'processing_queue', ['workspace_id'])
    
    # 2. Add workspace_id to processing_tasks (if table exists)
    # Check if table exists first
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'processing_tasks') THEN
                ALTER TABLE processing_tasks ADD COLUMN workspace_id UUID;
                ALTER TABLE processing_tasks ADD CONSTRAINT processing_tasks_workspace_id_fkey 
                    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE;
                CREATE INDEX idx_processing_tasks_workspace_id ON processing_tasks(workspace_id);
                
                -- Mark existing user_id field as deprecated with a comment
                COMMENT ON COLUMN processing_tasks.user_id IS 'DEPRECATED: Use workspace_id instead. Will be removed in future version.';
            END IF;
        END $$;
    """)
    
    # 3. Add workspace_id to processing_errors (if table exists)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'processing_errors') THEN
                ALTER TABLE processing_errors ADD COLUMN workspace_id UUID;
                ALTER TABLE processing_errors ADD CONSTRAINT processing_errors_workspace_id_fkey 
                    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE;
                CREATE INDEX idx_processing_errors_workspace_id ON processing_errors(workspace_id);
            END IF;
        END $$;
    """)
    
    # 4. Add workspace_id to processing_events (if table exists)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'processing_events') THEN
                ALTER TABLE processing_events ADD COLUMN workspace_id UUID;
                ALTER TABLE processing_events ADD CONSTRAINT processing_events_workspace_id_fkey 
                    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE;
                CREATE INDEX idx_processing_events_workspace_id ON processing_events(workspace_id);
            END IF;
        END $$;
    """)
    
    # Note: Data migration to populate workspace_id values will be handled in DB-06


def downgrade() -> None:
    """Remove workspace_id from processing-related entities"""
    
    # 1. Revert processing_queue changes
    op.drop_index('idx_processing_queue_workspace_id')
    op.drop_constraint('processing_queue_workspace_id_fkey', 'processing_queue', type_='foreignkey')
    op.drop_column('processing_queue', 'workspace_id')
    
    # 2. Revert processing_tasks changes (if table exists)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'processing_tasks') THEN
                DROP INDEX IF EXISTS idx_processing_tasks_workspace_id;
                ALTER TABLE processing_tasks DROP CONSTRAINT IF EXISTS processing_tasks_workspace_id_fkey;
                ALTER TABLE processing_tasks DROP COLUMN IF EXISTS workspace_id;
                
                -- Remove deprecation comment
                COMMENT ON COLUMN processing_tasks.user_id IS NULL;
            END IF;
        END $$;
    """)
    
    # 3. Revert processing_errors changes (if table exists)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'processing_errors') THEN
                DROP INDEX IF EXISTS idx_processing_errors_workspace_id;
                ALTER TABLE processing_errors DROP CONSTRAINT IF EXISTS processing_errors_workspace_id_fkey;
                ALTER TABLE processing_errors DROP COLUMN IF EXISTS workspace_id;
            END IF;
        END $$;
    """)
    
    # 4. Revert processing_events changes (if table exists)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'processing_events') THEN
                DROP INDEX IF EXISTS idx_processing_events_workspace_id;
                ALTER TABLE processing_events DROP CONSTRAINT IF EXISTS processing_events_workspace_id_fkey;
                ALTER TABLE processing_events DROP COLUMN IF EXISTS workspace_id;
            END IF;
        END $$;
    """) 