-- 論文分析系統資料庫 Schema
-- PostgreSQL 14+

-- 建立UUID擴展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 論文管理表 (加入TEI XML儲存，簡化使用者管理)
CREATE TABLE papers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    file_name VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255),
    upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processing_status VARCHAR(50) DEFAULT 'uploading',
    file_size BIGINT,
    file_hash VARCHAR(64) UNIQUE, -- 用於檔案去重
    grobid_processed BOOLEAN DEFAULT FALSE,
    sentences_processed BOOLEAN DEFAULT FALSE,
    pdf_deleted BOOLEAN DEFAULT FALSE, -- 標記PDF是否已刪除
    error_message TEXT,
    -- TEI XML 儲存 (新增)
    tei_xml TEXT, -- 儲存完整的Grobid TEI XML
    tei_metadata JSONB, -- 儲存解析後的metadata (作者、標題等)
    processing_completed_at TIMESTAMP, -- 處理完成時間
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 論文分區表
CREATE TABLE paper_sections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    paper_id UUID REFERENCES papers(id) ON DELETE CASCADE,
    section_type VARCHAR(50) NOT NULL, -- introduction, abstract, method, etc.
    page_num INTEGER,
    content TEXT NOT NULL,
    section_order INTEGER,
    -- 新增TEI相關欄位
    tei_coordinates JSONB, -- 儲存TEI座標資訊
    word_count INTEGER, -- 章節字數
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 句子資料表  
CREATE TABLE sentences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    paper_id UUID REFERENCES papers(id) ON DELETE CASCADE,
    section_id UUID REFERENCES paper_sections(id) ON DELETE CASCADE,
    sentence_text TEXT NOT NULL,
    page_num INTEGER,
    sentence_order INTEGER,
    defining_type VARCHAR(20) DEFAULT 'UNKNOWN', -- OD, CD, OTHER, UNKNOWN
    analysis_reason TEXT,
    -- 新增欄位
    word_count INTEGER, -- 句子字數
    confidence_score DECIMAL(3,2), -- OD/CD分析信心度
    processed_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 全域論文選擇狀態表 (簡化為單一使用者模式)
CREATE TABLE paper_selections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    paper_id UUID REFERENCES papers(id) ON DELETE CASCADE,
    is_selected BOOLEAN DEFAULT TRUE,
    selected_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(paper_id)
);

-- 處理佇列表 (用於FastAPI後端批次處理)
CREATE TABLE processing_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    paper_id UUID REFERENCES papers(id) ON DELETE CASCADE,
    processing_stage VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending', -- pending, processing, completed, failed
    priority INTEGER DEFAULT 0,
    retry_count INTEGER DEFAULT 0, -- 重試次數
    max_retries INTEGER DEFAULT 3, -- 最大重試次數
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    processing_details JSONB -- 儲存處理過程的詳細資訊
);

-- 系統設定表 (用於存放全域設定)
CREATE TABLE system_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    setting_key VARCHAR(100) UNIQUE NOT NULL,
    setting_value JSONB,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 建立索引以提升查詢效能
CREATE INDEX idx_papers_hash ON papers(file_hash);
CREATE INDEX idx_papers_status ON papers(processing_status);
CREATE INDEX idx_papers_created_at ON papers(created_at);

CREATE INDEX idx_sections_paper_id ON paper_sections(paper_id);
CREATE INDEX idx_sections_type ON paper_sections(section_type);

CREATE INDEX idx_sentences_defining_type ON sentences(defining_type);
CREATE INDEX idx_sentences_paper_section ON sentences(paper_id, section_id);
CREATE INDEX idx_sentences_text_search ON sentences USING gin(to_tsvector('english', sentence_text));

CREATE INDEX idx_queue_status_priority ON processing_queue(status, priority);
CREATE INDEX idx_queue_paper_stage ON processing_queue(paper_id, processing_stage);

CREATE INDEX idx_selections_paper ON paper_selections(paper_id);

-- 插入初始系統設定
INSERT INTO system_settings (setting_key, setting_value, description) VALUES
('system_version', '"1.0.0"', '系統版本'),
('max_file_size_mb', '50', '最大上傳檔案大小(MB)'),
('batch_processing_size', '10', '批次處理句子數量'),
('auto_cleanup_hours', '24', '自動清理暫存檔案時間(小時)')
ON CONFLICT (setting_key) DO NOTHING;

-- 建立觸發器：自動更新 updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_system_settings_updated_at 
    BEFORE UPDATE ON system_settings 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column(); 