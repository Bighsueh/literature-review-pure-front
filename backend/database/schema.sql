-- 論文分析系統資料庫 Schema
-- PostgreSQL 14+

-- 建立UUID擴展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 論文管理表 (加入TEI XML儲存，簡化使用者管理)
CREATE TABLE IF NOT EXISTS papers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    file_name VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255),
    upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processing_status VARCHAR(50) DEFAULT 'uploading',
    file_size BIGINT,
    file_hash VARCHAR(64) UNIQUE, -- 用於檔案去重
    grobid_processed BOOLEAN DEFAULT FALSE,
    sentences_processed BOOLEAN DEFAULT FALSE,
    od_cd_processed BOOLEAN DEFAULT FALSE, -- 新增缺失的欄位
    pdf_deleted BOOLEAN DEFAULT FALSE, -- 標記PDF是否已刪除
    error_message TEXT,
    -- TEI XML 儲存 (新增)
    tei_xml TEXT, -- 儲存完整的Grobid TEI XML
    tei_metadata JSONB, -- 儲存解析後的metadata (作者、標題等)
    processing_completed_at TIMESTAMP, -- 處理完成時間
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 論文分區表
CREATE TABLE IF NOT EXISTS paper_sections (
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
CREATE TABLE IF NOT EXISTS sentences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    paper_id UUID REFERENCES papers(id) ON DELETE CASCADE,
    section_id UUID REFERENCES paper_sections(id) ON DELETE CASCADE,
    content TEXT NOT NULL, -- 改為 content
    sentence_order INTEGER,
    word_count INTEGER, -- 句子字數
    char_count INTEGER, -- 字符數
    -- 檢測結果欄位
    has_objective BOOLEAN DEFAULT NULL,
    has_dataset BOOLEAN DEFAULT NULL,
    has_contribution BOOLEAN DEFAULT NULL,
    detection_status VARCHAR(20) DEFAULT 'unknown',
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    explanation TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 全域論文選擇狀態表 (簡化為單一使用者模式)
CREATE TABLE IF NOT EXISTS paper_selections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    paper_id UUID REFERENCES papers(id) ON DELETE CASCADE,
    is_selected BOOLEAN DEFAULT TRUE,
    selected_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(paper_id)
);

-- 處理佇列表 (用於FastAPI後端批次處理)
CREATE TABLE IF NOT EXISTS processing_queue (
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
CREATE TABLE IF NOT EXISTS system_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    setting_key VARCHAR(100) UNIQUE NOT NULL,
    setting_value JSONB,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 處理任務表 (新增 - 用於追蹤所有處理任務)
CREATE TABLE IF NOT EXISTS processing_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    paper_id UUID REFERENCES papers(id) ON DELETE CASCADE,
    task_id VARCHAR(64) NOT NULL UNIQUE,
    task_type VARCHAR(50) NOT NULL, -- file_processing, batch_sentence_analysis, etc.
    priority SMALLINT DEFAULT 2,
    retries SMALLINT DEFAULT 0,
    max_retries SMALLINT DEFAULT 3,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    timeout_seconds INTEGER DEFAULT 1800,
    data JSONB, -- 任務配置和資料
    result JSONB, -- 任務結果
    error_message TEXT,
    user_id VARCHAR(50),
    parent_task_id UUID REFERENCES processing_tasks(id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 處理事件表 (新增 - 用於追蹤處理過程中的事件)
CREATE TABLE IF NOT EXISTS processing_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID REFERENCES processing_tasks(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL, -- progress_update, step_completed, error, warning
    event_name VARCHAR(100),
    message TEXT,
    step_number INTEGER,
    total_steps INTEGER,
    percentage DECIMAL(5,2),
    details JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 處理錯誤表 (新增 - 用於詳細記錄錯誤資訊)
CREATE TABLE IF NOT EXISTS processing_errors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID REFERENCES processing_tasks(id) ON DELETE CASCADE,
    error_type VARCHAR(50) NOT NULL, -- validation_error, grobid_error, n8n_error, db_error
    error_code VARCHAR(20),
    error_message TEXT NOT NULL,
    stack_trace TEXT,
    context_data JSONB, -- 錯誤發生時的上下文資料
    severity VARCHAR(20) DEFAULT 'error', -- info, warning, error, critical
    is_recoverable BOOLEAN DEFAULT FALSE,
    recovery_suggestion TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 建立索引以提升查詢效能
CREATE INDEX IF NOT EXISTS idx_papers_hash ON papers(file_hash);
CREATE INDEX IF NOT EXISTS idx_papers_status ON papers(processing_status);
CREATE INDEX IF NOT EXISTS idx_papers_created_at ON papers(created_at);

CREATE INDEX IF NOT EXISTS idx_sections_paper_id ON paper_sections(paper_id);
CREATE INDEX IF NOT EXISTS idx_sections_type ON paper_sections(section_type);

CREATE INDEX IF NOT EXISTS idx_sentences_detection_status ON sentences(detection_status);
CREATE INDEX IF NOT EXISTS idx_sentences_paper_section ON sentences(paper_id, section_id);
CREATE INDEX IF NOT EXISTS idx_sentences_text_search ON sentences USING gin(to_tsvector('english', content));
CREATE INDEX IF NOT EXISTS idx_sentences_retry_count ON sentences(retry_count);
CREATE INDEX IF NOT EXISTS idx_sentences_has_objective ON sentences(has_objective);
CREATE INDEX IF NOT EXISTS idx_sentences_has_dataset ON sentences(has_dataset);
CREATE INDEX IF NOT EXISTS idx_sentences_has_contribution ON sentences(has_contribution);

CREATE INDEX IF NOT EXISTS idx_queue_status_priority ON processing_queue(status, priority);
CREATE INDEX IF NOT EXISTS idx_queue_paper_stage ON processing_queue(paper_id, processing_stage);

CREATE INDEX IF NOT EXISTS idx_selections_paper ON paper_selections(paper_id);

-- 新表的索引
CREATE INDEX IF NOT EXISTS idx_processing_tasks_paper_id ON processing_tasks(paper_id);
CREATE INDEX IF NOT EXISTS idx_processing_tasks_task_id ON processing_tasks(task_id);
CREATE INDEX IF NOT EXISTS idx_processing_tasks_status ON processing_tasks(status);
CREATE INDEX IF NOT EXISTS idx_processing_tasks_created_at ON processing_tasks(created_at);
CREATE INDEX IF NOT EXISTS idx_processing_tasks_parent ON processing_tasks(parent_task_id);

CREATE INDEX IF NOT EXISTS idx_processing_events_task_id ON processing_events(task_id);
CREATE INDEX IF NOT EXISTS idx_processing_events_type ON processing_events(event_type);
CREATE INDEX IF NOT EXISTS idx_processing_events_created_at ON processing_events(created_at);

CREATE INDEX IF NOT EXISTS idx_processing_errors_task_id ON processing_errors(task_id);
CREATE INDEX IF NOT EXISTS idx_processing_errors_type ON processing_errors(error_type);
CREATE INDEX IF NOT EXISTS idx_processing_errors_created_at ON processing_errors(created_at);
CREATE INDEX IF NOT EXISTS idx_processing_errors_severity ON processing_errors(severity);

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