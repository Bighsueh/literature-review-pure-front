# 資料庫 Schema 文檔

## 概述

本文檔描述論文分析系統的完整資料庫結構（**2025-06-22** 版），內容來源於目前執行中的 PostgreSQL。

## 資料庫資訊

- **資料庫類型**: PostgreSQL 15.x
- **字符編碼**: UTF-8
- **時區**: UTC
- **擴展**: uuid-ossp (用於 UUID 生成)

## 🏗️ 架構變更概述

### 重大變更 (2025-01-12)
1. **新增用戶管理系統** - 支援 Google OAuth 登入
2. **多工作區支援** - 實現真正的多租戶資料隔離
3. **對話歷史功能** - 按工作區的聊天記錄管理
4. **約束調整** - 從全域唯一改為工作區級別唯一
5. **索引優化** - 針對工作區查詢的效能最佳化

## 表格結構

### 1. users (用戶表) 🆕

用戶身分認證和基本資訊管理。

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    google_id VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    picture_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**欄位說明**:
- `google_id`: Google OAuth 提供的唯一識別碼
- `email`: 用戶電子郵件地址，必須唯一
- `picture_url`: 用戶頭像 URL

**索引**:
```sql
CREATE UNIQUE INDEX idx_users_google_id ON users(google_id);
CREATE UNIQUE INDEX idx_users_email ON users(email);
```

### 2. workspaces (工作區表) 🆕

用戶的工作區管理，支援多專案隔離。

```sql
CREATE TABLE workspaces (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**欄位說明**:
- `user_id`: 工作區所屬用戶
- `name`: 工作區名稱，可自定義

**索引**:
```sql
CREATE INDEX idx_workspaces_user_id ON workspaces(user_id);
```

### 3. chat_histories (對話歷史表) 🆕

按工作區的聊天對話記錄。

```sql
CREATE TABLE chat_histories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    message_metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**欄位說明**:
- `role`: 訊息角色，只能是 'user' 或 'assistant'
- `message_metadata`: 訊息的額外中繼資料（JSON 格式）

**索引**:
```sql
CREATE INDEX idx_chat_histories_workspace_id ON chat_histories(workspace_id);
CREATE INDEX idx_chat_histories_workspace_created_at ON chat_histories(workspace_id, created_at);
```

### 4. papers (論文主表) ✏️ 已更新

論文的基本資訊和處理狀態，已加入工作區支援。

```sql
CREATE TABLE papers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    file_name VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255),
    upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processing_status VARCHAR(50) DEFAULT 'uploading',
    file_size BIGINT,
    file_hash VARCHAR(64), -- 注意：不再有全域唯一約束
    
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
    
    -- 新約束：同一工作區內檔案 hash 唯一
    CONSTRAINT papers_workspace_file_hash_key UNIQUE (workspace_id, file_hash)
);
```

**重要變更**:
- ✅ 新增 `workspace_id` 欄位（必填）
- ❌ 移除 `file_hash` 的全域唯一約束
- ✅ 新增 `(workspace_id, file_hash)` 複合唯一約束

**索引**:
```sql
CREATE INDEX idx_papers_workspace_id ON papers(workspace_id);
CREATE INDEX idx_papers_workspace_processing_status ON papers(workspace_id, processing_status);
CREATE INDEX idx_papers_workspace_created_at ON papers(workspace_id, created_at);
```

### 5. paper_sections (論文章節表) ✏️ 已更新

論文的章節資訊和內容，已加入工作區支援。

```sql
CREATE TABLE paper_sections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    paper_id UUID NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    section_type VARCHAR(50) NOT NULL,
    page_num INTEGER,
    content TEXT NOT NULL,
    section_order INTEGER,
    tei_coordinates JSONB,
    word_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**重要變更**:
- ✅ 新增 `workspace_id` 欄位（必填）

**索引**:
```sql
CREATE INDEX idx_paper_sections_workspace_id ON paper_sections(workspace_id);
CREATE INDEX idx_paper_sections_workspace_section_type ON paper_sections(workspace_id, section_type);
```

### 6. sentences (句子表) ✏️ 再次更新（2025-06-22）

從論文章節中提取的句子及其分析結果，已加入工作區支援。

```sql
CREATE TABLE sentences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    paper_id UUID NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    section_id UUID NOT NULL REFERENCES paper_sections(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    sentence_order INTEGER,
    word_count INTEGER,
    char_count INTEGER,
    
    -- 檢測結果欄位
    has_objective BOOLEAN,
    has_dataset BOOLEAN,
    has_contribution BOOLEAN,
    detection_status VARCHAR(20) DEFAULT 'unknown',
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    explanation TEXT,
    
    -- 新增欄位
    defining_type VARCHAR(20) DEFAULT 'UNKNOWN', -- 可能值: 'OD', 'CD', 'UNKNOWN'
    page_num INTEGER,
    
    -- 時間戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**重要變更**:
- ✅ 新增 `workspace_id` 欄位（必填）

**索引**:
```sql
CREATE INDEX idx_sentences_workspace_id ON sentences(workspace_id);
CREATE INDEX idx_sentences_paper_section ON sentences(paper_id, section_id);
CREATE INDEX idx_sentences_detection_status ON sentences(detection_status);
CREATE INDEX idx_sentences_defining_type ON sentences(defining_type);
CREATE INDEX idx_sentences_page_num ON sentences(page_num);
CREATE INDEX idx_sentences_text_search ON sentences USING GIN (to_tsvector('english', content));
```

### 7. paper_selections (論文選擇表) ✏️ 已更新

記錄使用者在特定工作區選擇的論文，支援多工作區獨立選擇。

```sql
CREATE TABLE paper_selections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    paper_id UUID NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    is_selected BOOLEAN DEFAULT TRUE,
    selected_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 新約束：同一工作區內同一論文只能有一個選擇記錄
    CONSTRAINT paper_selections_workspace_paper_key UNIQUE (workspace_id, paper_id)
);
```

**重要變更**:
- ✅ 新增 `workspace_id` 欄位（必填）
- ❌ 移除 `paper_id` 的全域唯一約束
- ✅ 新增 `(workspace_id, paper_id)` 複合唯一約束

**索引**:
```sql
CREATE INDEX idx_paper_selections_workspace_id ON paper_selections(workspace_id);
```

### 8. processing_queue (處理佇列表) ✏️ 已更新

記錄檔案處理任務的佇列狀態，已加入工作區支援。

```sql
CREATE TABLE processing_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    paper_id UUID NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    processing_stage VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    priority INTEGER DEFAULT 0,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    error_message TEXT,
    processing_details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);
```

**重要變更**:
- ✅ 新增 `workspace_id` 欄位（必填）

**索引**:
```sql
CREATE INDEX idx_processing_queue_workspace_id ON processing_queue(workspace_id);
CREATE INDEX idx_processing_queue_workspace_status ON processing_queue(workspace_id, status);
CREATE INDEX idx_processing_queue_workspace_created_at ON processing_queue(workspace_id, created_at);
```

### 9. processing_tasks (詳細處理任務表) ✏️ 已更新

更細粒度的處理任務追蹤，已加入工作區支援。

```sql
CREATE TABLE processing_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    paper_id UUID REFERENCES papers(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    task_id VARCHAR(64) UNIQUE NOT NULL,
    task_type VARCHAR(50) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    priority SMALLINT DEFAULT 2,
    retries SMALLINT DEFAULT 0,
    max_retries SMALLINT DEFAULT 3,
    timeout_seconds INTEGER DEFAULT 1800,
    data JSONB,
    result JSONB,
    error_message TEXT,
    user_id VARCHAR(50), -- 標記為棄用，使用 workspace_id 代替
    parent_task_id UUID REFERENCES processing_tasks(id),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 為棄用欄位添加註解
COMMENT ON COLUMN processing_tasks.user_id IS 'DEPRECATED: Use workspace_id instead. Will be removed in future version.';
```

**重要變更**:
- ✅ 新增 `workspace_id` 欄位（必填）
- ⚠️ `user_id` 欄位標記為棄用

**索引**:
```sql
CREATE INDEX idx_processing_tasks_workspace_id ON processing_tasks(workspace_id);
CREATE INDEX idx_processing_tasks_workspace_status ON processing_tasks(workspace_id, status);
```

### 10. processing_errors (處理錯誤記錄表) ✏️ 已更新

記錄處理任務中發生的詳細錯誤，已加入工作區支援。

```sql
CREATE TABLE processing_errors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID REFERENCES processing_tasks(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    error_type VARCHAR(50) NOT NULL,
    error_code VARCHAR(20),
    error_message TEXT NOT NULL,
    stack_trace TEXT,
    context_data JSONB,
    severity VARCHAR(20) DEFAULT 'error',
    is_recoverable BOOLEAN DEFAULT FALSE,
    recovery_suggestion TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
```

**重要變更**:
- ✅ 新增 `workspace_id` 欄位（必填）

**索引**:
```sql
CREATE INDEX idx_processing_errors_workspace_id ON processing_errors(workspace_id);
CREATE INDEX idx_processing_errors_workspace_created_at ON processing_errors(workspace_id, created_at);
```

### 11. processing_events (處理進度事件表) ✏️ 已更新

記錄處理任務的詳細進度事件，已加入工作區支援。

```sql
CREATE TABLE processing_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID REFERENCES processing_tasks(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    event_name VARCHAR(100),
    message TEXT,
    step_number INTEGER,
    total_steps INTEGER,
    percentage NUMERIC(5, 2),
    details JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
```

**重要變更**:
- ✅ 新增 `workspace_id` 欄位（必填）

**索引**:
```sql
CREATE INDEX idx_processing_events_workspace_id ON processing_events(workspace_id);
CREATE INDEX idx_processing_events_workspace_event_type ON processing_events(workspace_id, event_type);
```

### 12. system_settings (系統設定表) ⭕ 未變更

系統全域設定，不受工作區架構影響。

```sql
CREATE TABLE system_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    setting_key VARCHAR(100) UNIQUE NOT NULL,
    setting_value JSONB,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 🚀 遷移策略

### 遺留資料處理
所有遷移前的資料都被自動歸檔到特殊的「遺留工作區」：

1. **系統用戶**: `google_id = 'system_legacy_user'`
2. **遺留工作區**: `Legacy Data Workspace`
3. **資料歸檔**: 所有無主資料自動關聯到此工作區

### 遷移腳本順序
1. **002_papers_workspaces**: 為 papers 添加 workspace_id 和調整約束
2. **003_isolate_core_entities**: 為核心資料實體添加 workspace_id
3. **004_isolate_processing_entities**: 為處理相關實體添加 workspace_id
4. **005_legacy_data_migration**: 執行遺留資料遷移
5. **006_workspace_indexes**: 建立效能優化索引

## 📊 約束和索引摘要

### 唯一約束變更
| 表格 | 舊約束 | 新約束 |
|-----|--------|--------|
| papers | `file_hash` UNIQUE | `(workspace_id, file_hash)` UNIQUE |
| paper_selections | `paper_id` UNIQUE | `(workspace_id, paper_id)` UNIQUE |

### 外鍵約束
所有 `workspace_id` 欄位都設定 `ON DELETE CASCADE`，確保工作區刪除時清理所有相關資料。

### 效能索引
針對工作區查詢建立了豐富的複合索引，包括：
- 基礎工作區索引：所有表格的 `workspace_id`
- 複合查詢索引：`(workspace_id, status)`, `(workspace_id, created_at)` 等

## 🔒 資料安全與隔離

### 多租戶隔離
- 所有查詢都必須包含 `workspace_id` 過濾條件
- 應用層需要確保用戶只能訪問自己工作區的資料
- 前端需要實現工作區上下文管理

### 資料完整性
- 實施了自動化驗證框架
- 支援遷移前後的資料完整性檢查
- 驗證工作區一致性和外鍵關聯正確性

---

**最後更新**: 2025-01-12  
**版本**: 多工作區架構 v1.0  
**狀態**: 已完成遷移並通過驗證 