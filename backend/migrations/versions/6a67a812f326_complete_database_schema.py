"""complete_database_schema

Revision ID: 6a67a812f326
Revises: 
Create Date: 2025-06-13 18:28:05.527491

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '6a67a812f326'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create complete database schema"""
    
    # Enable UUID extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    
    # Create papers table if not exists
    op.execute("""
        CREATE TABLE IF NOT EXISTS papers (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            file_name VARCHAR(255) NOT NULL,
            original_filename VARCHAR(255),
            upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processing_status VARCHAR(50) DEFAULT 'uploading',
            file_size BIGINT,
            file_hash VARCHAR(64) UNIQUE,
            grobid_processed BOOLEAN DEFAULT FALSE,
            sentences_processed BOOLEAN DEFAULT FALSE,
            od_cd_processed BOOLEAN DEFAULT FALSE,
            pdf_deleted BOOLEAN DEFAULT FALSE,
            error_message TEXT,
            tei_xml TEXT,
            tei_metadata JSONB,
            processing_completed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create paper_sections table if not exists
    op.execute("""
        CREATE TABLE IF NOT EXISTS paper_sections (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            paper_id UUID NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
            section_type VARCHAR(50) NOT NULL,
            page_num INTEGER,
            content TEXT NOT NULL,
            section_order INTEGER,
            tei_coordinates JSONB,
            word_count INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create sentences table if not exists
    op.execute("""
        CREATE TABLE IF NOT EXISTS sentences (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            paper_id UUID NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
            section_id UUID NOT NULL REFERENCES paper_sections(id) ON DELETE CASCADE,
            sentence_text TEXT NOT NULL,
            page_num INTEGER,
            sentence_order INTEGER,
            defining_type VARCHAR(20) DEFAULT 'UNKNOWN',
            analysis_reason TEXT,
            word_count INTEGER,
            confidence_score DECIMAL(3,2),
            processed_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            detection_status VARCHAR(20) DEFAULT 'unknown',
            error_message TEXT,
            retry_count INTEGER DEFAULT 0,
            explanation TEXT
        )
    """)
    
    # Create paper_selections table if not exists
    op.execute("""
        CREATE TABLE IF NOT EXISTS paper_selections (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            paper_id UUID NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
            is_selected BOOLEAN DEFAULT TRUE,
            selected_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(paper_id)
        )
    """)
    
    # Create processing_queue table if not exists
    op.execute("""
        CREATE TABLE IF NOT EXISTS processing_queue (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            paper_id UUID NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
            processing_stage VARCHAR(50) NOT NULL,
            status VARCHAR(20) DEFAULT 'pending',
            priority INTEGER DEFAULT 0,
            retry_count INTEGER DEFAULT 0,
            max_retries INTEGER DEFAULT 3,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            error_message TEXT,
            processing_details JSONB
        )
    """)
    
    # Create system_settings table if not exists
    op.execute("""
        CREATE TABLE IF NOT EXISTS system_settings (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            setting_key VARCHAR(100) UNIQUE NOT NULL,
            setting_value JSONB,
            description TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create indexes if not exist
    op.execute('CREATE INDEX IF NOT EXISTS idx_papers_hash ON papers(file_hash)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_papers_status ON papers(processing_status)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_papers_created_at ON papers(created_at)')
    
    op.execute('CREATE INDEX IF NOT EXISTS idx_sections_paper_id ON paper_sections(paper_id)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_sections_type ON paper_sections(section_type)')
    
    op.execute('CREATE INDEX IF NOT EXISTS idx_sentences_defining_type ON sentences(defining_type)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_sentences_paper_section ON sentences(paper_id, section_id)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_sentences_detection_status ON sentences(detection_status)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_sentences_retry_count ON sentences(retry_count)')
    op.execute("CREATE INDEX IF NOT EXISTS idx_sentences_text_search ON sentences USING gin(to_tsvector('english', sentence_text))")
    
    op.execute('CREATE INDEX IF NOT EXISTS idx_queue_status_priority ON processing_queue(status, priority)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_queue_paper_stage ON processing_queue(paper_id, processing_stage)')
    
    op.execute('CREATE INDEX IF NOT EXISTS idx_selections_paper ON paper_selections(paper_id)')
    
    # Create trigger function for updated_at
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql'
    """)
    
    # Create trigger
    op.execute("""
        DROP TRIGGER IF EXISTS update_system_settings_updated_at ON system_settings;
        CREATE TRIGGER update_system_settings_updated_at 
            BEFORE UPDATE ON system_settings 
            FOR EACH ROW 
            EXECUTE FUNCTION update_updated_at_column()
    """)


def downgrade() -> None:
    """Drop all tables and extensions"""
    op.execute('DROP TRIGGER IF EXISTS update_system_settings_updated_at ON system_settings')
    op.execute('DROP FUNCTION IF EXISTS update_updated_at_column()')
    
    op.execute('DROP TABLE IF EXISTS system_settings CASCADE')
    op.execute('DROP TABLE IF EXISTS processing_queue CASCADE')
    op.execute('DROP TABLE IF EXISTS paper_selections CASCADE')
    op.execute('DROP TABLE IF EXISTS sentences CASCADE')
    op.execute('DROP TABLE IF EXISTS paper_sections CASCADE')
    op.execute('DROP TABLE IF EXISTS papers CASCADE')
    
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')
