-- ================================================
-- 論文分析系統資料庫完整建置 SQL
-- PostgreSQL 15.13
-- 建立日期: 2025-06-14
-- ================================================

-- 1. 清空現有資料庫 (小心使用!)
-- ================================================

-- 停用所有外鍵約束以避免刪除順序問題
SET session_replication_role = replica;

-- 刪除所有現有表格 (如果存在)
DROP TABLE IF EXISTS processing_queue CASCADE;
DROP TABLE IF EXISTS paper_selections CASCADE;
DROP TABLE IF EXISTS sentences CASCADE;
DROP TABLE IF EXISTS paper_sections CASCADE;
DROP TABLE IF EXISTS papers CASCADE;

-- 刪除所有函數 (如果存在)
DROP FUNCTION IF EXISTS update_papers_updated_at() CASCADE;
DROP FUNCTION IF EXISTS update_sentences_updated_at() CASCADE;

-- 重新啟用外鍵約束
SET session_replication_role = DEFAULT;

-- 2. 建立必要的擴展
-- ================================================

-- 建立 UUID 擴展 (如果不存在)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 3. 建立所有表格
-- ================================================

-- 3.1 papers (論文主表)
CREATE TABLE papers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    file_name VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255),
    upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processing_status VARCHAR(20) DEFAULT 'pending',
    file_size BIGINT,
    file_hash VARCHAR(64) UNIQUE,
    
    -- 處理狀態標記
    grobid_processed BOOLEAN DEFAULT FALSE,
    sentences_processed BOOLEAN DEFAULT FALSE,
    od_cd_processed BOOLEAN DEFAULT FALSE,
    pdf_deleted BOOLEAN DEFAULT FALSE,
    
    -- 錯誤處理
    error_message TEXT,
    
    -- TEI XML 資料
    tei_xml TEXT,
    tei_metadata JSONB,
    
    -- 時間戳
    processing_completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3.2 paper_sections (論文章節表)
CREATE TABLE paper_sections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    paper_id UUID REFERENCES papers(id) ON DELETE CASCADE,
    section_type VARCHAR(50) NOT NULL,
    page_num INTEGER,
    content TEXT,
    section_order INTEGER,
    tei_coordinates TEXT,
    word_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3.3 sentences (句子表)
CREATE TABLE sentences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    paper_id UUID REFERENCES papers(id) ON DELETE CASCADE,
    section_id UUID REFERENCES paper_sections(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    sentence_order INTEGER,
    word_count INTEGER,
    char_count INTEGER,
    
    -- 檢測結果欄位
    has_objective BOOLEAN DEFAULT NULL,
    has_dataset BOOLEAN DEFAULT NULL,
    has_contribution BOOLEAN DEFAULT NULL,
    detection_status VARCHAR(20) DEFAULT 'unknown',
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    explanation TEXT,
    
    -- 時間戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3.4 paper_selections (論文選擇表)
CREATE TABLE paper_selections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    paper_id UUID REFERENCES papers(id) ON DELETE CASCADE,
    is_selected BOOLEAN DEFAULT TRUE,
    selected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(paper_id)
);

-- 3.5 processing_queue (處理佇列表)
CREATE TABLE processing_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    paper_id UUID REFERENCES papers(id) ON DELETE CASCADE,
    task_id VARCHAR(255) UNIQUE,
    processing_stage VARCHAR(50),
    status VARCHAR(20) DEFAULT 'pending',
    priority INTEGER DEFAULT 5,
    error_message TEXT,
    processing_details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- 4. 建立檢查約束
-- ================================================

-- papers 表約束
ALTER TABLE papers 
ADD CONSTRAINT chk_papers_processing_status 
CHECK (processing_status IN ('pending', 'processing', 'completed', 'error'));

ALTER TABLE papers 
ADD CONSTRAINT chk_papers_file_size 
CHECK (file_size >= 0);

-- sentences 表約束
ALTER TABLE sentences 
ADD CONSTRAINT chk_sentences_detection_status 
CHECK (detection_status IN ('unknown', 'processing', 'success', 'error'));

ALTER TABLE sentences 
ADD CONSTRAINT chk_sentences_retry_count 
CHECK (retry_count >= 0 AND retry_count <= 10);

ALTER TABLE sentences 
ADD CONSTRAINT chk_sentences_word_count 
CHECK (word_count >= 0);

-- processing_queue 表約束
ALTER TABLE processing_queue 
ADD CONSTRAINT chk_queue_status 
CHECK (status IN ('pending', 'processing', 'completed', 'failed'));

ALTER TABLE processing_queue 
ADD CONSTRAINT chk_queue_priority 
CHECK (priority >= 1 AND priority <= 10);

-- 5. 建立索引
-- ================================================

-- papers 表索引
CREATE INDEX idx_papers_status ON papers(processing_status);
CREATE INDEX idx_papers_hash ON papers(file_hash);
CREATE INDEX idx_papers_created_at ON papers(created_at);
CREATE INDEX idx_papers_filename ON papers(file_name);

-- paper_sections 表索引
CREATE INDEX idx_sections_paper_id ON paper_sections(paper_id);
CREATE INDEX idx_sections_type ON paper_sections(section_type);
CREATE INDEX idx_sections_order ON paper_sections(paper_id, section_order);

-- sentences 表索引
CREATE INDEX idx_sentences_paper_id ON sentences(paper_id);
CREATE INDEX idx_sentences_section_id ON sentences(section_id);
CREATE INDEX idx_sentences_detection_status ON sentences(detection_status);
CREATE INDEX idx_sentences_paper_section ON sentences(paper_id, section_id);
CREATE INDEX idx_sentences_retry_count ON sentences(retry_count);
CREATE INDEX idx_sentences_has_objective ON sentences(has_objective);
CREATE INDEX idx_sentences_has_dataset ON sentences(has_dataset);
CREATE INDEX idx_sentences_has_contribution ON sentences(has_contribution);

-- 全文搜索索引
CREATE INDEX idx_sentences_text_search ON sentences USING gin(to_tsvector('english', content));

-- paper_selections 表索引
CREATE INDEX idx_selections_paper_id ON paper_selections(paper_id);
CREATE INDEX idx_selections_is_selected ON paper_selections(is_selected);

-- processing_queue 表索引
CREATE INDEX idx_queue_paper_id ON processing_queue(paper_id);
CREATE INDEX idx_queue_task_id ON processing_queue(task_id);
CREATE INDEX idx_queue_status ON processing_queue(status);
CREATE INDEX idx_queue_priority ON processing_queue(priority, created_at);

-- 6. 建立觸發器函數
-- ================================================

-- 更新 papers 表的 updated_at 欄位
CREATE OR REPLACE FUNCTION update_papers_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 更新 sentences 表的 updated_at 欄位
CREATE OR REPLACE FUNCTION update_sentences_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 7. 建立觸發器
-- ================================================

-- papers 表觸發器
CREATE TRIGGER trigger_update_papers_updated_at
    BEFORE UPDATE ON papers
    FOR EACH ROW
    EXECUTE FUNCTION update_papers_updated_at();

-- sentences 表觸發器
CREATE TRIGGER trigger_update_sentences_updated_at
    BEFORE UPDATE ON sentences
    FOR EACH ROW
    EXECUTE FUNCTION update_sentences_updated_at();

-- 8. 驗證資料庫結構
-- ================================================

-- 檢查所有表格是否建立成功
SELECT 
    tablename,
    schemaname,
    hasindexes,
    hasrules,
    hastriggers
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY tablename;

-- 檢查所有索引
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;

-- 檢查所有外鍵約束
SELECT
    tc.table_name,
    tc.constraint_name,
    tc.constraint_type,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc 
    JOIN information_schema.key_column_usage AS kcu
        ON tc.constraint_name = kcu.constraint_name
        AND tc.table_schema = kcu.table_schema
    JOIN information_schema.constraint_column_usage AS ccu
        ON ccu.constraint_name = tc.constraint_name
        AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY' 
    AND tc.table_schema = 'public'
ORDER BY tc.table_name;

-- 檢查所有檢查約束
SELECT
    tc.table_name,
    tc.constraint_name,
    cc.check_clause
FROM information_schema.table_constraints AS tc
    JOIN information_schema.check_constraints AS cc
        ON tc.constraint_name = cc.constraint_name
WHERE tc.constraint_type = 'CHECK' 
    AND tc.table_schema = 'public'
ORDER BY tc.table_name;

-- ================================================
-- 資料庫建置完成!
-- ================================================

-- 輸出建置摘要
SELECT 
    'Database schema setup completed successfully!' AS status,
    NOW() AS completed_at;