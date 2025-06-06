-- 檔案管理表
CREATE TABLE IF NOT EXISTS files (
    file_id TEXT PRIMARY KEY,
    original_filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    file_hash TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'uploaded',
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    grobid_result TEXT, -- JSON
    processing_summary TEXT, -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 建立檔案 hash 索引用於去重
CREATE INDEX IF NOT EXISTS idx_files_hash ON files(file_hash);
CREATE INDEX IF NOT EXISTS idx_files_status ON files(status);

-- 佇列任務表
CREATE TABLE IF NOT EXISTS queue_tasks (
    task_id TEXT PRIMARY KEY,
    task_data TEXT NOT NULL, -- JSON，包含完整的 QueueTask 數據
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 佇列任務索引
CREATE INDEX IF NOT EXISTS idx_queue_tasks_status ON queue_tasks(JSON_EXTRACT(task_data, '$.status'));
CREATE INDEX IF NOT EXISTS idx_queue_tasks_priority ON queue_tasks(JSON_EXTRACT(task_data, '$.priority'));
CREATE INDEX IF NOT EXISTS idx_queue_tasks_file_id ON queue_tasks(JSON_EXTRACT(task_data, '$.file_id'));
CREATE INDEX IF NOT EXISTS idx_queue_tasks_user_id ON queue_tasks(JSON_EXTRACT(task_data, '$.user_id'));

-- 論文章節表
CREATE TABLE IF NOT EXISTS paper_sections (
    section_id TEXT,
    file_id TEXT,
    title TEXT,
    content TEXT,
    section_type TEXT,
    word_count INTEGER,
    section_order INTEGER,
    analysis_data TEXT, -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (file_id, section_id),
    FOREIGN KEY (file_id) REFERENCES files(file_id) ON DELETE CASCADE
);

-- 章節索引
CREATE INDEX IF NOT EXISTS idx_sections_file_id ON paper_sections(file_id);
CREATE INDEX IF NOT EXISTS idx_sections_type ON paper_sections(section_type);
CREATE INDEX IF NOT EXISTS idx_sections_order ON paper_sections(section_order);

-- 論文句子表
CREATE TABLE IF NOT EXISTS paper_sentences (
    sentence_id TEXT,
    file_id TEXT,
    text TEXT NOT NULL,
    section_id TEXT,
    is_od_cd BOOLEAN DEFAULT FALSE,
    od_cd_confidence REAL DEFAULT 0.0,
    od_cd_type TEXT,
    position_in_section INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (file_id, sentence_id),
    FOREIGN KEY (file_id) REFERENCES files(file_id) ON DELETE CASCADE,
    FOREIGN KEY (file_id, section_id) REFERENCES paper_sections(file_id, section_id) ON DELETE CASCADE
);

-- 句子索引
CREATE INDEX IF NOT EXISTS idx_sentences_file_id ON paper_sentences(file_id);
CREATE INDEX IF NOT EXISTS idx_sentences_section_id ON paper_sentences(section_id);
CREATE INDEX IF NOT EXISTS idx_sentences_od_cd ON paper_sentences(is_od_cd);
CREATE INDEX IF NOT EXISTS idx_sentences_confidence ON paper_sentences(od_cd_confidence);

-- 論文關鍵詞表
CREATE TABLE IF NOT EXISTS paper_keywords (
    file_id TEXT,
    section_id TEXT,
    keyword TEXT,
    extraction_confidence REAL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (file_id, section_id, keyword),
    FOREIGN KEY (file_id) REFERENCES files(file_id) ON DELETE CASCADE,
    FOREIGN KEY (file_id, section_id) REFERENCES paper_sections(file_id, section_id) ON DELETE CASCADE
);

-- 關鍵詞索引
CREATE INDEX IF NOT EXISTS idx_keywords_file_id ON paper_keywords(file_id);
CREATE INDEX IF NOT EXISTS idx_keywords_section_id ON paper_keywords(section_id);
CREATE INDEX IF NOT EXISTS idx_keywords_keyword ON paper_keywords(keyword);

-- 處理統計表
CREATE TABLE IF NOT EXISTS processing_stats (
    stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id TEXT,
    processing_duration INTEGER, -- 處理時間（秒）
    grobid_duration INTEGER, -- Grobid 處理時間
    analysis_duration INTEGER, -- 分析處理時間
    total_sentences INTEGER,
    od_cd_sentences INTEGER,
    total_keywords INTEGER,
    errors_count INTEGER,
    processing_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (file_id) REFERENCES files(file_id) ON DELETE CASCADE
);

-- 統計索引
CREATE INDEX IF NOT EXISTS idx_stats_file_id ON processing_stats(file_id);
CREATE INDEX IF NOT EXISTS idx_stats_date ON processing_stats(processing_date);

-- 觸發器：自動更新 updated_at
CREATE TRIGGER IF NOT EXISTS update_files_timestamp 
    AFTER UPDATE ON files
    BEGIN
        UPDATE files SET updated_at = CURRENT_TIMESTAMP WHERE file_id = NEW.file_id;
    END;

CREATE TRIGGER IF NOT EXISTS update_queue_tasks_timestamp 
    AFTER UPDATE ON queue_tasks
    BEGIN
        UPDATE queue_tasks SET updated_at = CURRENT_TIMESTAMP WHERE task_id = NEW.task_id;
    END; 
CREATE TABLE IF NOT EXISTS files (
    file_id TEXT PRIMARY KEY,
    original_filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    file_hash TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'uploaded',
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    grobid_result TEXT, -- JSON
    processing_summary TEXT, -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 建立檔案 hash 索引用於去重
CREATE INDEX IF NOT EXISTS idx_files_hash ON files(file_hash);
CREATE INDEX IF NOT EXISTS idx_files_status ON files(status);

-- 佇列任務表
CREATE TABLE IF NOT EXISTS queue_tasks (
    task_id TEXT PRIMARY KEY,
    task_data TEXT NOT NULL, -- JSON，包含完整的 QueueTask 數據
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 佇列任務索引
CREATE INDEX IF NOT EXISTS idx_queue_tasks_status ON queue_tasks(JSON_EXTRACT(task_data, '$.status'));
CREATE INDEX IF NOT EXISTS idx_queue_tasks_priority ON queue_tasks(JSON_EXTRACT(task_data, '$.priority'));
CREATE INDEX IF NOT EXISTS idx_queue_tasks_file_id ON queue_tasks(JSON_EXTRACT(task_data, '$.file_id'));
CREATE INDEX IF NOT EXISTS idx_queue_tasks_user_id ON queue_tasks(JSON_EXTRACT(task_data, '$.user_id'));

-- 論文章節表
CREATE TABLE IF NOT EXISTS paper_sections (
    section_id TEXT,
    file_id TEXT,
    title TEXT,
    content TEXT,
    section_type TEXT,
    word_count INTEGER,
    section_order INTEGER,
    analysis_data TEXT, -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (file_id, section_id),
    FOREIGN KEY (file_id) REFERENCES files(file_id) ON DELETE CASCADE
);

-- 章節索引
CREATE INDEX IF NOT EXISTS idx_sections_file_id ON paper_sections(file_id);
CREATE INDEX IF NOT EXISTS idx_sections_type ON paper_sections(section_type);
CREATE INDEX IF NOT EXISTS idx_sections_order ON paper_sections(section_order);

-- 論文句子表
CREATE TABLE IF NOT EXISTS paper_sentences (
    sentence_id TEXT,
    file_id TEXT,
    text TEXT NOT NULL,
    section_id TEXT,
    is_od_cd BOOLEAN DEFAULT FALSE,
    od_cd_confidence REAL DEFAULT 0.0,
    od_cd_type TEXT,
    position_in_section INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (file_id, sentence_id),
    FOREIGN KEY (file_id) REFERENCES files(file_id) ON DELETE CASCADE,
    FOREIGN KEY (file_id, section_id) REFERENCES paper_sections(file_id, section_id) ON DELETE CASCADE
);

-- 句子索引
CREATE INDEX IF NOT EXISTS idx_sentences_file_id ON paper_sentences(file_id);
CREATE INDEX IF NOT EXISTS idx_sentences_section_id ON paper_sentences(section_id);
CREATE INDEX IF NOT EXISTS idx_sentences_od_cd ON paper_sentences(is_od_cd);
CREATE INDEX IF NOT EXISTS idx_sentences_confidence ON paper_sentences(od_cd_confidence);

-- 論文關鍵詞表
CREATE TABLE IF NOT EXISTS paper_keywords (
    file_id TEXT,
    section_id TEXT,
    keyword TEXT,
    extraction_confidence REAL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (file_id, section_id, keyword),
    FOREIGN KEY (file_id) REFERENCES files(file_id) ON DELETE CASCADE,
    FOREIGN KEY (file_id, section_id) REFERENCES paper_sections(file_id, section_id) ON DELETE CASCADE
);

-- 關鍵詞索引
CREATE INDEX IF NOT EXISTS idx_keywords_file_id ON paper_keywords(file_id);
CREATE INDEX IF NOT EXISTS idx_keywords_section_id ON paper_keywords(section_id);
CREATE INDEX IF NOT EXISTS idx_keywords_keyword ON paper_keywords(keyword);

-- 處理統計表
CREATE TABLE IF NOT EXISTS processing_stats (
    stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id TEXT,
    processing_duration INTEGER, -- 處理時間（秒）
    grobid_duration INTEGER, -- Grobid 處理時間
    analysis_duration INTEGER, -- 分析處理時間
    total_sentences INTEGER,
    od_cd_sentences INTEGER,
    total_keywords INTEGER,
    errors_count INTEGER,
    processing_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (file_id) REFERENCES files(file_id) ON DELETE CASCADE
);

-- 統計索引
CREATE INDEX IF NOT EXISTS idx_stats_file_id ON processing_stats(file_id);
CREATE INDEX IF NOT EXISTS idx_stats_date ON processing_stats(processing_date);

-- 觸發器：自動更新 updated_at
CREATE TRIGGER IF NOT EXISTS update_files_timestamp 
    AFTER UPDATE ON files
    BEGIN
        UPDATE files SET updated_at = CURRENT_TIMESTAMP WHERE file_id = NEW.file_id;
    END;

CREATE TRIGGER IF NOT EXISTS update_queue_tasks_timestamp 
    AFTER UPDATE ON queue_tasks
    BEGIN
        UPDATE queue_tasks SET updated_at = CURRENT_TIMESTAMP WHERE task_id = NEW.task_id;
    END; 