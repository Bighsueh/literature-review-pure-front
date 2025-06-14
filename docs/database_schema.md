# 資料庫 Schema 文檔

## 概述

本文檔描述論文分析系統的完整資料庫結構，包含所有表格、欄位、關係、索引和約束的詳細說明。

## 資料庫資訊

- **資料庫類型**: PostgreSQL 15.13
- **字符編碼**: UTF-8
- **時區**: UTC
- **擴展**: uuid-ossp (用於 UUID 生成)

## 表格結構

### 1. papers (論文主表)

論文的基本資訊和處理狀態。

```sql
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
```

**欄位說明**:
- `id`: 論文唯一識別碼 (UUID)
- `file_name`: 系統內部檔案名稱
- `original_filename`: 使用者上傳時的原始檔案名稱
- `processing_status`: 處理狀態 (`pending`, `processing`, `completed`, `error`)
- `file_hash`: 檔案 SHA-256 雜湊值，用於重複檢測
- `grobid_processed`: Grobid TEI 解析是否完成
- `sentences_processed`: 句子提取和處理是否完成
- `od_cd_processed`: OD/CD 檢測是否完成
- `tei_xml`: Grobid 產生的 TEI XML 內容
- `tei_metadata`: 從 TEI 提取的元資料 (JSON 格式)

### 2. paper_sections (論文章節表)

論文的章節資訊和內容。

```sql
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
```

**欄位說明**:
- `paper_id`: 關聯的論文 ID (外鍵)
- `section_type`: 章節類型 (`introduction`, `methodology`, `results`, `conclusion`, `abstract`, `references`, `other`)
- `page_num`: 章節所在頁碼
- `content`: 章節完整內容
- `section_order`: 章節在論文中的順序
- `tei_coordinates`: TEI XML 中的座標資訊
- `word_count`: 章節字數統計

### 3. sentences (句子表)

從論文章節中提取的句子及其分析結果。

```sql
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
```

**欄位說明**:
- `paper_id`: 關聯的論文 ID (外鍵)
- `section_id`: 關聯的章節 ID (外鍵)
- `content`: 句子內容
- `sentence_order`: 句子在章節中的順序
- `has_objective`: 是否包含研究目標定義
- `has_dataset`: 是否包含資料集定義
- `has_contribution`: 是否包含貢獻定義
- `detection_status`: 檢測狀態 (`unknown`, `processing`, `success`, `error`)
- `explanation`: AI 分析的解釋說明
- `retry_count`: 檢測重試次數

### 4. paper_selections (論文選擇表)

記錄使用者選擇的論文，用於查詢分析。

```sql
CREATE TABLE paper_selections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    paper_id UUID REFERENCES papers(id) ON DELETE CASCADE,
    is_selected BOOLEAN DEFAULT TRUE,
    selected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(paper_id)
);
```

**欄位說明**:
- `paper_id`: 關聯的論文 ID (外鍵)
- `is_selected`: 是否被選中
- `selected_at`: 選擇時間

### 5. processing_queue (處理佇列表)

記錄檔案處理任務的佇列狀態。

```sql
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
```

**欄位說明**:
- `paper_id`: 關聯的論文 ID (外鍵)
- `task_id`: 任務唯一識別碼
- `processing_stage`: 處理階段 (`grobid`, `sections`, `sentences`, `od_cd`)
- `status`: 任務狀態 (`pending`, `processing`, `completed`, `failed`)
- `priority`: 任務優先級 (1-10, 數字越小優先級越高)
- `processing_details`: 處理詳細資訊 (JSON 格式)

## 索引

### 主要索引

```sql
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
```

## 觸發器

### 自動更新時間戳

```sql
-- 更新 papers 表的 updated_at 欄位
CREATE OR REPLACE FUNCTION update_papers_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_papers_updated_at
    BEFORE UPDATE ON papers
    FOR EACH ROW
    EXECUTE FUNCTION update_papers_updated_at();

-- 更新 sentences 表的 updated_at 欄位
CREATE OR REPLACE FUNCTION update_sentences_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_sentences_updated_at
    BEFORE UPDATE ON sentences
    FOR EACH ROW
    EXECUTE FUNCTION update_sentences_updated_at();
```

## 外鍵約束

```sql
-- paper_sections 外鍵
ALTER TABLE paper_sections 
ADD CONSTRAINT fk_paper_sections_paper_id 
FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE;

-- sentences 外鍵
ALTER TABLE sentences 
ADD CONSTRAINT fk_sentences_paper_id 
FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE;

ALTER TABLE sentences 
ADD CONSTRAINT fk_sentences_section_id 
FOREIGN KEY (section_id) REFERENCES paper_sections(id) ON DELETE CASCADE;

-- paper_selections 外鍵
ALTER TABLE paper_selections 
ADD CONSTRAINT fk_paper_selections_paper_id 
FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE;

-- processing_queue 外鍵
ALTER TABLE processing_queue 
ADD CONSTRAINT fk_processing_queue_paper_id 
FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE;
```

## 檢查約束

```sql
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
```

## 資料關係圖

```
papers (1) ──────┐
                 │
                 ├─── paper_sections (N)
                 │           │
                 │           └─── sentences (N)
                 │
                 ├─── paper_selections (1)
                 │
                 └─── processing_queue (N)
```

## 典型查詢模式

### 1. 獲取論文及其統計資訊

```sql
SELECT 
    p.id,
    p.file_name,
    p.processing_status,
    COUNT(DISTINCT ps.id) AS section_count,
    COUNT(DISTINCT s.id) AS sentence_count,
    COUNT(DISTINCT CASE WHEN s.has_objective = true THEN s.id END) AS objective_count,
    COUNT(DISTINCT CASE WHEN s.has_dataset = true THEN s.id END) AS dataset_count,
    COUNT(DISTINCT CASE WHEN s.has_contribution = true THEN s.id END) AS contribution_count
FROM papers p
LEFT JOIN paper_sections ps ON p.id = ps.paper_id
LEFT JOIN sentences s ON p.id = s.paper_id
GROUP BY p.id, p.file_name, p.processing_status
ORDER BY p.created_at DESC;
```

### 2. 搜尋包含特定關鍵詞的句子

```sql
SELECT 
    s.content,
    s.has_objective,
    s.has_dataset,
    s.has_contribution,
    ps.section_type,
    p.file_name
FROM sentences s
JOIN paper_sections ps ON s.section_id = ps.id
JOIN papers p ON s.paper_id = p.id
WHERE to_tsvector('english', s.content) @@ plainto_tsquery('english', '關鍵詞')
AND p.processing_status = 'completed'
ORDER BY ts_rank(to_tsvector('english', s.content), plainto_tsquery('english', '關鍵詞')) DESC;
```

### 3. 獲取選中論文的章節摘要

```sql
SELECT 
    p.file_name,
    ps.section_type,
    ps.word_count,
    COUNT(s.id) AS sentence_count,
    COUNT(CASE WHEN s.has_objective = true THEN 1 END) AS od_count,
    COUNT(CASE WHEN s.has_dataset = true THEN 1 END) AS cd_count
FROM papers p
JOIN paper_selections psel ON p.id = psel.paper_id
JOIN paper_sections ps ON p.id = ps.paper_id
LEFT JOIN sentences s ON ps.id = s.section_id
WHERE psel.is_selected = true
AND p.processing_status = 'completed'
GROUP BY p.file_name, ps.section_type, ps.word_count
ORDER BY p.file_name, ps.section_order;
```

## 維護建議

### 1. 定期清理

```sql
-- 清理超過 30 天的錯誤處理記錄
DELETE FROM processing_queue 
WHERE status = 'failed' 
AND created_at < NOW() - INTERVAL '30 days';

-- 清理未完成的處理任務 (超過 24 小時)
UPDATE processing_queue 
SET status = 'failed', 
    error_message = 'Task timeout'
WHERE status = 'processing' 
AND started_at < NOW() - INTERVAL '24 hours';
```

### 2. 效能監控

```sql
-- 檢查索引使用情況
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;

-- 檢查表格大小
SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size(tablename::regclass)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(tablename::regclass) DESC;
```

### 3. 備份策略

- **每日備份**: 完整資料庫備份
- **增量備份**: WAL 檔案連續備份
- **測試還原**: 定期測試備份還原程序

## 版本歷史

| 版本 | 日期 | 變更說明 |
|------|------|----------|
| 1.0 | 2025-06-14 | 初始版本，包含完整的表格結構和關係 |

## 注意事項

1. **UUID 使用**: 所有主鍵都使用 UUID，確保分散式環境下的唯一性
2. **級聯刪除**: 刪除論文時會自動清理相關的章節、句子和選擇記錄
3. **軟刪除**: 目前使用硬刪除，如需軟刪除可添加 `deleted_at` 欄位
4. **JSON 欄位**: `tei_metadata` 和 `processing_details` 使用 JSONB 格式，支援高效查詢
5. **全文搜索**: 句子內容支援 PostgreSQL 全文搜索功能 