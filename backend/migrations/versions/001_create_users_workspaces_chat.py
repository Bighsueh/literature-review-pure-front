"""create_users_workspaces_chat

Revision ID: 001_users_workspaces_chat
Revises: 6a67a812f326
Create Date: 2025-01-12 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_users_workspaces_chat'
down_revision: Union[str, None] = 'b7c75e7ad4e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add users, workspaces, and chat_histories tables"""
    
    # Create users table
    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            google_id VARCHAR(255) UNIQUE NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL,
            picture_url VARCHAR(500),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create workspaces table
    op.execute("""
        CREATE TABLE IF NOT EXISTS workspaces (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create chat_histories table
    op.execute("""
        CREATE TABLE IF NOT EXISTS chat_histories (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
            content TEXT NOT NULL,
            message_metadata JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create indexes for performance
    op.execute('CREATE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_workspaces_user_id ON workspaces(user_id)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_chat_histories_workspace_id ON chat_histories(workspace_id)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_chat_histories_created_at ON chat_histories(created_at)')
    
    # Create trigger function for updated_at if not exists
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql'
    """)
    
    # Create triggers for updated_at fields
    op.execute("""
        DROP TRIGGER IF EXISTS update_users_updated_at ON users;
        CREATE TRIGGER update_users_updated_at 
            BEFORE UPDATE ON users 
            FOR EACH ROW 
            EXECUTE FUNCTION update_updated_at_column()
    """)
    
    op.execute("""
        DROP TRIGGER IF EXISTS update_workspaces_updated_at ON workspaces;
        CREATE TRIGGER update_workspaces_updated_at 
            BEFORE UPDATE ON workspaces 
            FOR EACH ROW 
            EXECUTE FUNCTION update_updated_at_column()
    """)


def downgrade() -> None:
    """Drop users, workspaces, and chat_histories tables"""
    
    # Drop triggers first
    op.execute('DROP TRIGGER IF EXISTS update_workspaces_updated_at ON workspaces')
    op.execute('DROP TRIGGER IF EXISTS update_users_updated_at ON users')
    
    # Drop tables in reverse order due to foreign keys
    op.execute('DROP TABLE IF EXISTS chat_histories CASCADE')
    op.execute('DROP TABLE IF EXISTS workspaces CASCADE')
    op.execute('DROP TABLE IF EXISTS users CASCADE')
    
    # Note: We don't drop the trigger function as it might be used by other tables 