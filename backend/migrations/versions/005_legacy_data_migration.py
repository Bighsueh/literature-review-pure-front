"""legacy_data_migration

Revision ID: 005_legacy_data_migration
Revises: 004_isolate_processing_entities
Create Date: 2025-01-12 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '005_legacy_data_migration'
down_revision: Union[str, None] = '004_isolate_processing_entities'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Migrate legacy data to workspace-based architecture"""
    
    # Step 1: Create default user and legacy workspace
    op.execute("""
        -- Create default system user for legacy data
        INSERT INTO users (google_id, email, name, picture_url)
        VALUES (
            'system_legacy_user',
            'legacy@system.local',
            'System Legacy User',
            NULL
        )
        ON CONFLICT (google_id) DO NOTHING;
    """)
    
    op.execute("""
        -- Create legacy workspace for historical data
        INSERT INTO workspaces (user_id, name)
        SELECT 
            u.id,
            'Legacy Data Workspace'
        FROM users u 
        WHERE u.google_id = 'system_legacy_user'
        ON CONFLICT DO NOTHING;
    """)
    
    # Step 2: Get the legacy workspace ID for data migration
    op.execute("""
        -- Create a temporary function to get legacy workspace ID
        CREATE OR REPLACE FUNCTION get_legacy_workspace_id() 
        RETURNS UUID AS $$
        DECLARE
            workspace_uuid UUID;
        BEGIN
            SELECT w.id INTO workspace_uuid
            FROM workspaces w
            JOIN users u ON w.user_id = u.id
            WHERE u.google_id = 'system_legacy_user'
            LIMIT 1;
            
            IF workspace_uuid IS NULL THEN
                RAISE EXCEPTION 'Legacy workspace not found';
            END IF;
            
            RETURN workspace_uuid;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Step 3: Migrate papers table
    op.execute("""
        -- Update papers with NULL workspace_id to legacy workspace
        UPDATE papers 
        SET workspace_id = get_legacy_workspace_id()
        WHERE workspace_id IS NULL;
    """)
    
    # Step 4: Migrate paper_sections table  
    op.execute("""
        -- Update paper_sections with NULL workspace_id
        UPDATE paper_sections 
        SET workspace_id = (
            SELECT p.workspace_id 
            FROM papers p 
            WHERE p.id = paper_sections.paper_id
        )
        WHERE workspace_id IS NULL;
    """)
    
    # Step 5: Migrate sentences table
    op.execute("""
        -- Update sentences with NULL workspace_id
        UPDATE sentences 
        SET workspace_id = (
            SELECT p.workspace_id 
            FROM papers p 
            WHERE p.id = sentences.paper_id
        )
        WHERE workspace_id IS NULL;
    """)
    
    # Step 6: Migrate paper_selections table
    op.execute("""
        -- Update paper_selections with NULL workspace_id
        UPDATE paper_selections 
        SET workspace_id = (
            SELECT p.workspace_id 
            FROM papers p 
            WHERE p.id = paper_selections.paper_id
        )
        WHERE workspace_id IS NULL;
    """)
    
    # Step 7: Migrate processing_queue table
    op.execute("""
        -- Update processing_queue with NULL workspace_id
        UPDATE processing_queue 
        SET workspace_id = (
            SELECT p.workspace_id 
            FROM papers p 
            WHERE p.id = processing_queue.paper_id
        )
        WHERE workspace_id IS NULL;
    """)
    
    # Step 8: Migrate processing tables (if they exist)
    op.execute("""
        -- Update processing_tasks with NULL workspace_id (if table exists)
        DO $$
        BEGIN
            IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'processing_tasks') THEN
                UPDATE processing_tasks 
                SET workspace_id = (
                    SELECT p.workspace_id 
                    FROM papers p 
                    WHERE p.id = processing_tasks.paper_id
                )
                WHERE workspace_id IS NULL
                AND paper_id IS NOT NULL;
                
                -- For tasks without paper_id, assign to legacy workspace
                UPDATE processing_tasks 
                SET workspace_id = get_legacy_workspace_id()
                WHERE workspace_id IS NULL;
            END IF;
        END $$;
    """)
    
    op.execute("""
        -- Update processing_errors with NULL workspace_id (if table exists)
        DO $$
        BEGIN
            IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'processing_errors') THEN
                UPDATE processing_errors 
                SET workspace_id = (
                    SELECT pt.workspace_id 
                    FROM processing_tasks pt 
                    WHERE pt.id = processing_errors.task_id
                )
                WHERE workspace_id IS NULL
                AND task_id IS NOT NULL;
                
                -- For errors without task_id, assign to legacy workspace
                UPDATE processing_errors 
                SET workspace_id = get_legacy_workspace_id()
                WHERE workspace_id IS NULL;
            END IF;
        END $$;
    """)
    
    op.execute("""
        -- Update processing_events with NULL workspace_id (if table exists)
        DO $$
        BEGIN
            IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'processing_events') THEN
                UPDATE processing_events 
                SET workspace_id = (
                    SELECT pt.workspace_id 
                    FROM processing_tasks pt 
                    WHERE pt.id = processing_events.task_id
                )
                WHERE workspace_id IS NULL
                AND task_id IS NOT NULL;
                
                -- For events without task_id, assign to legacy workspace
                UPDATE processing_events 
                SET workspace_id = get_legacy_workspace_id()
                WHERE workspace_id IS NULL;
            END IF;
        END $$;
    """)
    
    # Step 9: Set workspace_id columns to NOT NULL
    op.alter_column('papers', 'workspace_id', nullable=False)
    op.alter_column('paper_sections', 'workspace_id', nullable=False)
    op.alter_column('sentences', 'workspace_id', nullable=False)
    op.alter_column('paper_selections', 'workspace_id', nullable=False)
    op.alter_column('processing_queue', 'workspace_id', nullable=False)
    
    # For optional tables, set NOT NULL only if they exist
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'processing_tasks') THEN
                ALTER TABLE processing_tasks ALTER COLUMN workspace_id SET NOT NULL;
            END IF;
            IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'processing_errors') THEN
                ALTER TABLE processing_errors ALTER COLUMN workspace_id SET NOT NULL;
            END IF;
            IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'processing_events') THEN
                ALTER TABLE processing_events ALTER COLUMN workspace_id SET NOT NULL;
            END IF;
        END $$;
    """)
    
    # Step 10: Clean up temporary function
    op.execute("DROP FUNCTION IF EXISTS get_legacy_workspace_id();")


def downgrade() -> None:
    """Revert legacy data migration"""
    
    # Step 1: Set workspace_id columns back to nullable
    op.alter_column('papers', 'workspace_id', nullable=True)
    op.alter_column('paper_sections', 'workspace_id', nullable=True)
    op.alter_column('sentences', 'workspace_id', nullable=True)
    op.alter_column('paper_selections', 'workspace_id', nullable=True)
    op.alter_column('processing_queue', 'workspace_id', nullable=True)
    
    # For optional tables
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'processing_tasks') THEN
                ALTER TABLE processing_tasks ALTER COLUMN workspace_id DROP NOT NULL;
            END IF;
            IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'processing_errors') THEN
                ALTER TABLE processing_errors ALTER COLUMN workspace_id DROP NOT NULL;
            END IF;
            IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'processing_events') THEN
                ALTER TABLE processing_events ALTER COLUMN workspace_id DROP NOT NULL;
            END IF;
        END $$;
    """)
    
    # Step 2: Clear workspace_id for legacy data
    # (In a real scenario, we might want to keep this data or have a more sophisticated rollback strategy)
    op.execute("""
        -- Clear workspace_id for data belonging to legacy workspace
        UPDATE papers 
        SET workspace_id = NULL
        WHERE workspace_id IN (
            SELECT w.id 
            FROM workspaces w 
            JOIN users u ON w.user_id = u.id 
            WHERE u.google_id = 'system_legacy_user'
        );
    """)
    
    # Similar updates for other tables would go here
    
    # Step 3: Remove legacy workspace and user (optional, might want to keep for audit)
    op.execute("""
        -- Remove legacy workspace
        DELETE FROM workspaces 
        WHERE user_id IN (
            SELECT id FROM users WHERE google_id = 'system_legacy_user'
        );
    """)
    
    op.execute("""
        -- Remove legacy user
        DELETE FROM users WHERE google_id = 'system_legacy_user';
    """) 