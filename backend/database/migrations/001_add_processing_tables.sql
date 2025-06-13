-- Migration: Add processing task tables
-- Date: 2024-01-01
-- Description: Add processing_tasks, processing_events, and processing_errors tables for enhanced task tracking

BEGIN;

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

COMMIT; 