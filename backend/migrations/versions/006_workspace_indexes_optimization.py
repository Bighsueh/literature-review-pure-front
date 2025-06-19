"""workspace_indexes_optimization

Revision ID: 006_workspace_indexes
Revises: 005_legacy_data_migration
Create Date: 2025-01-12 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '006_workspace_indexes'
down_revision: Union[str, None] = '005_legacy_data_migration'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create workspace-related indexes for performance optimization"""
    
    # Note: Some basic workspace_id indexes were already created in previous migrations
    # This migration adds additional composite indexes for common query patterns
    
    # 1. Chat histories: workspace + time-based queries
    op.create_index(
        'idx_chat_histories_workspace_created_at',
        'chat_histories',
        ['workspace_id', 'created_at'],
        postgresql_using='btree'
    )
    
    # 2. Paper selections: workspace + paper compound index (if not already exists)
    # This was already created in migration 003, but let's make sure it exists
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes 
                WHERE tablename = 'paper_selections' 
                AND indexname = 'idx_paper_selections_workspace_paper'
            ) THEN
                CREATE INDEX idx_paper_selections_workspace_paper 
                ON paper_selections (workspace_id, paper_id);
            END IF;
        END $$;
    """)
    
    # 3. Processing queue: workspace + status for task monitoring
    op.create_index(
        'idx_processing_queue_workspace_status',
        'processing_queue',
        ['workspace_id', 'status'],
        postgresql_using='btree'
    )
    
    # 4. Processing queue: workspace + created_at for chronological queries
    op.create_index(
        'idx_processing_queue_workspace_created_at',
        'processing_queue',
        ['workspace_id', 'created_at'],
        postgresql_using='btree'
    )
    
    # 5. Sentences: workspace + detection status for filtered queries
    op.create_index(
        'idx_sentences_workspace_detection_status',
        'sentences',
        ['workspace_id', 'detection_status'],
        postgresql_using='btree'
    )
    
    # 6. Paper sections: workspace + section_type for content organization
    op.create_index(
        'idx_paper_sections_workspace_section_type',
        'paper_sections',
        ['workspace_id', 'section_type'],
        postgresql_using='btree'
    )
    
    # 7. Papers: workspace + processing_status for status monitoring
    op.create_index(
        'idx_papers_workspace_processing_status',
        'papers',
        ['workspace_id', 'processing_status'],
        postgresql_using='btree'
    )
    
    # 8. Papers: workspace + created_at for chronological queries
    op.create_index(
        'idx_papers_workspace_created_at',
        'papers',
        ['workspace_id', 'created_at'],
        postgresql_using='btree'
    )
    
    # 9. For optional tables that might exist
    op.execute("""
        DO $$
        BEGIN
            -- Processing tasks: workspace + status (if table exists)
            IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'processing_tasks') THEN
                CREATE INDEX IF NOT EXISTS idx_processing_tasks_workspace_status
                ON processing_tasks (workspace_id, status);
            END IF;
            
            -- Processing errors: workspace + created_at (if table exists)
            IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'processing_errors') THEN
                CREATE INDEX IF NOT EXISTS idx_processing_errors_workspace_created_at
                ON processing_errors (workspace_id, created_at);
            END IF;
            
            -- Processing events: workspace + event_type (if table exists)
            IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'processing_events') THEN
                CREATE INDEX IF NOT EXISTS idx_processing_events_workspace_event_type
                ON processing_events (workspace_id, event_type);
            END IF;
        END $$;
    """)


def downgrade() -> None:
    """Remove workspace-related performance indexes"""
    
    # Drop all the indexes we created
    op.drop_index('idx_chat_histories_workspace_created_at')
    op.drop_index('idx_processing_queue_workspace_status')
    op.drop_index('idx_processing_queue_workspace_created_at')
    op.drop_index('idx_sentences_workspace_detection_status')
    op.drop_index('idx_paper_sections_workspace_section_type')
    op.drop_index('idx_papers_workspace_processing_status')
    op.drop_index('idx_papers_workspace_created_at')
    
    # Drop indexes for optional tables
    op.execute("""
        DROP INDEX IF EXISTS idx_paper_selections_workspace_paper;
        DROP INDEX IF EXISTS idx_processing_tasks_workspace_status;
        DROP INDEX IF EXISTS idx_processing_errors_workspace_created_at;
        DROP INDEX IF EXISTS idx_processing_events_workspace_event_type;
    """) 