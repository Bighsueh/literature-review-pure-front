-- ================================================
-- 完整資料庫重置與重建腳本
-- 解決 "relation already exists" 錯誤
-- ================================================

-- 第一步：完全清空所有相關物件
-- ================================================

-- 1.1 刪除所有觸發器
DROP TRIGGER IF EXISTS trigger_update_papers_updated_at ON papers;
DROP TRIGGER IF EXISTS trigger_update_sentences_updated_at ON sentences;

-- 1.2 刪除所有函數
DROP FUNCTION IF EXISTS update_papers_updated_at() CASCADE;
DROP FUNCTION IF EXISTS update_sentences_updated_at() CASCADE;

-- 1.3 強制刪除所有表格 (正確順序)
DROP TABLE IF EXISTS processing_queue CASCADE;
DROP TABLE IF EXISTS paper_selections CASCADE;
DROP TABLE IF EXISTS sentences CASCADE;
DROP TABLE IF EXISTS paper_sections CASCADE;
DROP TABLE IF EXISTS papers CASCADE;

-- 1.4 確認清理完成
SELECT 
    'Tables after cleanup:' as info,
    count(*) as remaining_tables
FROM pg_tables 
WHERE schemaname = 'public' 
    AND tablename IN ('papers', 'paper_sections', 'sentences', 'paper_selections', 'processing_queue');

-- 第二步：重新建立所有表格
-- ================================================

-- 2.1 papers (論文主表)
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

SELECT 'papers table created' as status;

-- 2.2 paper_sections (論文章節表)
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

SELECT 'paper_sections table created' as status;

-- 2.3 sentences (句子表)
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

SELECT 'sentences table created' as status;

-- 2.4 paper_selections (論文選擇表)
CREATE TABLE paper_selections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    paper_id UUID REFERENCES papers(id) ON DELETE CASCADE,
    is_selected BOOLEAN DEFAULT TRUE,
    selected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(paper_id)
);

SELECT 'paper_selections table created' as status;

-- 2.5 processing_queue (處理佇列表)
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

SELECT 'processing_queue table created' as status;

-- 第三步：建立所有約束
-- ================================================

-- 3.1 papers 表約束
ALTER TABLE papers 
ADD CONSTRAINT chk_papers_processing_status 
CHECK (processing_status IN ('uploading', 'pending', 'processing', 'completed', 'error'));

ALTER TABLE papers 
ADD CONSTRAINT chk_papers_file_size 
CHECK (file_size >= 0);

-- 3.2 sentences 表約束
ALTER TABLE sentences 
ADD CONSTRAINT chk_sentences_detection_status 
CHECK (detection_status IN ('unknown', 'processing', 'success', 'error'));

ALTER TABLE sentences 
ADD CONSTRAINT chk_sentences_retry_count 
CHECK (retry_count >= 0 AND retry_count <= 10);

ALTER TABLE sentences 
ADD CONSTRAINT chk_sentences_word_count 
CHECK (word_count >= 0);

-- 3.3 processing_queue 表約束
ALTER TABLE processing_queue 
ADD CONSTRAINT chk_queue_status 
CHECK (status IN ('pending', 'processing', 'completed', 'failed'));

ALTER TABLE processing_queue 
ADD CONSTRAINT chk_queue_priority 
CHECK (priority >= 1 AND priority <= 10);

SELECT 'All constraints created' as status;

-- 第四步：建立所有索引
-- ================================================

-- 4.1 papers 表索引
CREATE INDEX idx_papers_status ON papers(processing_status);
CREATE INDEX idx_papers_hash ON papers(file_hash);
CREATE INDEX idx_papers_created_at ON papers(created_at);
CREATE INDEX idx_papers_filename ON papers(file_name);

-- 4.2 paper_sections 表索引
CREATE INDEX idx_sections_paper_id ON paper_sections(paper_id);
CREATE INDEX idx_sections_type ON paper_sections(section_type);
CREATE INDEX idx_sections_order ON paper_sections(paper_id, section_order);

-- 4.3 sentences 表索引
CREATE INDEX idx_sentences_paper_id ON sentences(paper_id);
CREATE INDEX idx_sentences_section_id ON sentences(section_id);
CREATE INDEX idx_sentences_detection_status ON sentences(detection_status);
CREATE INDEX idx_sentences_paper_section ON sentences(paper_id, section_id);
CREATE INDEX idx_sentences_retry_count ON sentences(retry_count);
CREATE INDEX idx_sentences_has_objective ON sentences(has_objective);
CREATE INDEX idx_sentences_has_dataset ON sentences(has_dataset);
CREATE INDEX idx_sentences_has_contribution ON sentences(has_contribution);

-- 4.4 全文搜索索引
CREATE INDEX idx_sentences_text_search ON sentences USING gin(to_tsvector('english', content));

-- 4.5 paper_selections 表索引
CREATE INDEX idx_selections_paper_id ON paper_selections(paper_id);
CREATE INDEX idx_selections_is_selected ON paper_selections(is_selected);

-- 4.6 processing_queue 表索引
CREATE INDEX idx_queue_paper_id ON processing_queue(paper_id);
CREATE INDEX idx_queue_task_id ON processing_queue(task_id);
CREATE INDEX idx_queue_status ON processing_queue(status);
CREATE INDEX idx_queue_priority ON processing_queue(priority, created_at);

SELECT 'All indexes created' as status;

-- 第五步：建立觸發器函數和觸發器
-- ================================================

-- 5.1 更新 papers 表的 updated_at 欄位
CREATE OR REPLACE FUNCTION update_papers_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 5.2 更新 sentences 表的 updated_at 欄位
CREATE OR REPLACE FUNCTION update_sentences_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 5.3 建立觸發器
CREATE TRIGGER trigger_update_papers_updated_at
    BEFORE UPDATE ON papers
    FOR EACH ROW
    EXECUTE FUNCTION update_papers_updated_at();

CREATE TRIGGER trigger_update_sentences_updated_at
    BEFORE UPDATE ON sentences
    FOR EACH ROW
    EXECUTE FUNCTION update_sentences_updated_at();

SELECT 'All triggers created' as status;

-- 第六步：驗證建置結果
-- ================================================

-- 6.1 檢查所有表格
SELECT 
    'Final verification:' as info,
    tablename,
    schemaname
FROM pg_tables 
WHERE schemaname = 'public'
    AND tablename IN ('papers', 'paper_sections', 'sentences', 'paper_selections', 'processing_queue')
ORDER BY tablename;

-- 6.2 檢查表格數量
SELECT 
    'Total tables created:' as info,
    count(*) as count
FROM pg_tables 
WHERE schemaname = 'public'
    AND tablename IN ('papers', 'paper_sections', 'sentences', 'paper_selections', 'processing_queue');

-- 6.3 測試插入一筆資料
INSERT INTO papers (file_name, original_filename) 
VALUES ('test.pdf', 'test_original.pdf');

SELECT 
    'Test insert successful' as info,
    id,
    file_name,
    created_at
FROM papers
WHERE file_name = 'test.pdf';

-- 6.4 清理測試資料
DELETE FROM papers WHERE file_name = 'test.pdf';

SELECT 'Database setup completed successfully!' as final_status;