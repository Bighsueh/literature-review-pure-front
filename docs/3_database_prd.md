# III. 資料庫 PRD (Database PRD - PostgreSQL & MinIO)

## 1. 概述與用途 (Overview & Purpose)

### 1.1 PostgreSQL 資料庫
PostgreSQL 作為系統的主要關聯資料庫，負責儲存所有結構化資料，包括：
- 使用者帳號和認證信息
- 檔案元數據和處理狀態
- 文件中提取的句子及其分類結果
- 使用者查詢和系統回應的對話歷史
- 各種關係和引用 (如回答中引用的原文句子)

### 1.2 MinIO 物件儲存
MinIO 作為與 S3 相容的物件儲存服務，負責儲存：
- 使用者上傳的原始 PDF 檔案
- 系統產生的大型臨時檔案 (如處理中間結果)
- 分片上傳的檔案片段 (用於斷點續傳)

## 2. PostgreSQL 資料庫設計

### 2.1 資料表結構 (Table Schemas)

#### 2.1.1 使用者資料表 (users)
```sql
CREATE TABLE users (
    user_uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMPTZ
);
```
- **主要目的**: 儲存使用者帳戶信息
- **索引**: `email` (唯一索引)
- **約束**: `email` 不可為空且唯一，`password_hash` 不可為空
- **資料類型選擇理由**:
  - `UUID`: 作為主鍵，避免序列型主鍵的可預測性，提高安全性
  - `VARCHAR(255)`: 對於電子郵件和密碼雜湊的通用長度限制
  - `TIMESTAMPTZ`: 包含時區信息的時間戳，便於國際化

#### 2.1.2 檔案資料表 (files)
```sql
CREATE TABLE files (
    file_uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_uuid UUID NOT NULL REFERENCES users(user_uuid) ON DELETE CASCADE,
    original_name VARCHAR(255) NOT NULL,
    size_bytes BIGINT NOT NULL,
    minio_bucket_name VARCHAR(100) NOT NULL,
    minio_object_key VARCHAR(255) NOT NULL,
    upload_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    processing_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    error_message TEXT,
    sentence_count INTEGER DEFAULT 0,
    cd_count INTEGER DEFAULT 0,
    od_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    upload_started_at TIMESTAMPTZ,
    upload_completed_at TIMESTAMPTZ
);
```
- **主要目的**: 儲存上傳檔案的元數據和處理狀態
- **索引**: `user_uuid` (外鍵索引)、`(user_uuid, processing_status)` (複合索引)
- **約束**: `user_uuid` 參照 `users` 表的外鍵約束，CASCADE 刪除
- **資料類型選擇理由**:
  - `BIGINT` 用於 `size_bytes`，支援大檔案尺寸
  - `VARCHAR(20)` 用於狀態欄位，列舉固定的狀態值
  - `TEXT` 用於錯誤訊息，允許存儲不限長度的錯誤詳情
  - `TIMESTAMPTZ` 用於上傳開始和完成時間，支援超時監控

#### 2.1.3 句子資料表 (sentences)
```sql
CREATE TABLE sentences (
    sentence_uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_uuid UUID NOT NULL REFERENCES files(file_uuid) ON DELETE CASCADE,
    user_uuid UUID NOT NULL REFERENCES users(user_uuid) ON DELETE CASCADE,
    sentence TEXT NOT NULL,
    page INTEGER NOT NULL,
    defining_type VARCHAR(10) DEFAULT 'none',
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```
- **主要目的**: 儲存從 PDF 檔案中提取的句子及其分類結果
- **索引**:
  - `file_uuid` (外鍵索引)
  - `user_uuid` (外鍵索引)
  - `(user_uuid, file_uuid)` (複合索引，加速查詢)
  - `(user_uuid, defining_type)` (複合索引，加速按類型篩選)
  - `sentence` (全文搜尋索引，使用 GIN 索引)
- **約束**:
  - `file_uuid` 參照 `files` 表的外鍵約束，CASCADE 刪除
  - `user_uuid` 參照 `users` 表的外鍵約束，CASCADE 刪除
- **資料類型選擇理由**:
  - `TEXT` 用於句子內容，不限制長度
  - `INTEGER` 用於頁碼，足夠表示 PDF 頁數
  - `VARCHAR(10)` 用於定義類型，可能值為 'cd', 'od', 'none'

#### 2.1.4 對話資料表 (conversations)
```sql
CREATE TABLE conversations (
    conversation_uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_uuid UUID NOT NULL REFERENCES users(user_uuid) ON DELETE CASCADE,
    title VARCHAR(255) DEFAULT '新對話',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_message_at TIMESTAMPTZ
);
```
- **主要目的**: 儲存使用者的對話上下文
- **索引**: `user_uuid` (外鍵索引)、`last_message_at` (用於排序)
- **約束**: `user_uuid` 參照 `users` 表的外鍵約束，CASCADE 刪除
- **資料類型選擇理由**:
  - `VARCHAR(255)` 用於對話標題，限制合理長度
  - `TIMESTAMPTZ` 用於最後消息時間，便於排序和追踪活動

#### 2.1.5 消息資料表 (messages)
```sql
CREATE TABLE messages (
    message_uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_uuid UUID NOT NULL REFERENCES conversations(conversation_uuid) ON DELETE CASCADE,
    user_uuid UUID NOT NULL REFERENCES users(user_uuid) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,  -- 'user' or 'assistant'
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```
- **主要目的**: 儲存對話中的消息（用戶查詢和系統回應）
- **索引**:
  - `conversation_uuid` (外鍵索引)
  - `user_uuid` (外鍵索引)
  - `(conversation_uuid, created_at)` (複合索引，用於排序)
- **約束**:
  - `conversation_uuid` 參照 `conversations` 表的外鍵約束，CASCADE 刪除
  - `user_uuid` 參照 `users` 表的外鍵約束，CASCADE 刪除
- **資料類型選擇理由**:
  - `VARCHAR(20)` 用於角色，限定為 'user' 或 'assistant'
  - `TEXT` 用於消息內容，不限制長度

#### 2.1.6 消息引用資料表 (message_references)
```sql
CREATE TABLE message_references (
    reference_uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_uuid UUID NOT NULL REFERENCES messages(message_uuid) ON DELETE CASCADE,
    sentence_uuid UUID NOT NULL REFERENCES sentences(sentence_uuid) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```
- **主要目的**: 儲存系統回應中引用的原文句子關聯
- **索引**:
  - `message_uuid` (外鍵索引)
  - `sentence_uuid` (外鍵索引)
  - `(message_uuid, sentence_uuid)` (唯一複合索引)
- **約束**:
  - `message_uuid` 參照 `messages` 表的外鍵約束，CASCADE 刪除
  - `sentence_uuid` 參照 `sentences` 表的外鍵約束，CASCADE 刪除
  - `(message_uuid, sentence_uuid)` 唯一約束，防止重複引用
- **資料類型選擇理由**: 標準的 UUID 和時間戳類型

#### 2.1.7 上傳分片資料表 (upload_chunks)
```sql
CREATE TABLE upload_chunks (
    chunk_uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_uuid UUID NOT NULL REFERENCES users(user_uuid) ON DELETE CASCADE,
    upload_id VARCHAR(100) NOT NULL,
    file_id VARCHAR(100) NOT NULL,
    chunk_number INTEGER NOT NULL,
    chunk_total INTEGER NOT NULL,
    chunk_size BIGINT NOT NULL,
    minio_bucket_name VARCHAR(100) NOT NULL,
    minio_object_key VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL
);
```
- **主要目的**: 追踪檔案分片上傳狀態，支援斷點續傳
- **索引**:
  - `user_uuid` (外鍵索引)
  - `(upload_id, chunk_number)` (複合索引)
  - `expires_at` (用於清理過期記錄)
- **約束**: `user_uuid` 參照 `users` 表的外鍵約束，CASCADE 刪除
- **資料類型選擇理由**:
  - `VARCHAR(100)` 用於上傳 ID 和檔案 ID，足夠長度
  - `INTEGER` 用於分片編號和總數
  - `BIGINT` 用於分片大小，支援大檔案
  - `TIMESTAMPTZ` 用於過期時間，支援自動清理

### 2.2 索引策略

#### 2.2.1 B-tree 索引
- 用於精確匹配和範圍查詢
- 應用於主鍵、外鍵和常用篩選條件

#### 2.2.2 GIN 索引
- 用於全文搜尋
- 應用於 `sentences` 表的 `sentence` 欄位
```sql
CREATE INDEX idx_sentences_sentence_tsv ON sentences USING GIN (to_tsvector('chinese', sentence));
```

#### 2.2.3 複合索引
- 針對常見的多欄位查詢
- 例如 `(user_uuid, defining_type)` 用於查詢特定用戶的特定定義類型
```sql
CREATE INDEX idx_sentences_user_defining_type ON sentences(user_uuid, defining_type);
```

### 2.3 約束與資料完整性

#### 2.3.1 主鍵約束
- 所有表都使用 UUID 作為主鍵
- 使用 `gen_random_uuid()` 函數自動生成

#### 2.3.2 外鍵約束
- 所有關聯都使用外鍵約束
- 大多採用 `ON DELETE CASCADE` 策略，確保刪除父記錄時級聯刪除子記錄
- 刪除 `files` 記錄時會自動級聯刪除其關聯的 `sentences` 和 `message_references` 記錄

#### 2.3.3 唯一約束
- `users` 表的 `email` 欄位
- `message_references` 表的 `(message_uuid, sentence_uuid)` 組合

#### 2.3.4 非空約束
- 所有關鍵欄位都設置 `NOT NULL` 約束
- 例如用戶電子郵件、密碼雜湊、檔案名稱等

#### 2.3.5 檢查約束
- 頁碼必須為正整數
```sql
ALTER TABLE sentences ADD CONSTRAINT check_positive_page CHECK (page > 0);
```
- 定義類型必須為有效值
```sql
ALTER TABLE sentences ADD CONSTRAINT check_valid_defining_type CHECK (defining_type IN ('cd', 'od', 'none'));
```
- 上傳狀態必須為有效值
```sql
ALTER TABLE files ADD CONSTRAINT check_valid_upload_status CHECK (upload_status IN ('pending', 'in_progress', 'completed', 'failed', 'timeout'));
```

### 2.4 資料庫遷移策略
- 使用 Alembic 管理資料庫結構變更
- 每次變更生成適當的遷移腳本
- 支援升級和回滾操作
- 在 CI/CD 流程中自動應用遷移

## 3. MinIO 物件儲存設計

### 3.1 Bucket 策略
- 為每個用戶創建一個專屬的 bucket
- Bucket 命名格式: `user-{user_uuid}`
- 使用自定義的存取政策，僅允許用戶和系統存取其 bucket

### 3.2 物件命名策略
- 上傳的原始檔案: `{file_uuid}.pdf`
- 分片上傳的暫存片段: `uploads/{upload_id}/{chunk_number}`
- 處理中間結果: `processing/{file_uuid}/{step_name}.data`

### 3.3 存取控制
- 後端服務使用專用的 MinIO 訪問金鑰
- 使用有限權限的 IAM 政策
- 使用預簽名 URL 提供臨時檔案存取權限
- 設置合理的 URL 過期時間 (例如 15 分鐘)

### 3.4 生命週期管理
- 自動清理已處理完成的暫存檔案
- 定期清理過期的分片上傳
- 保留 7 天的上傳日誌

## 4. 資料完整性與一致性策略

### 4.1 事務管理
- 使用資料庫事務確保操作的原子性
- 關鍵操作使用顯式事務，例如:
  - 用戶註冊 (創建用戶記錄 + MinIO bucket)
  - 檔案處理完成 (更新檔案狀態 + 批量插入句子)
  - 刪除檔案 (刪除 PostgreSQL 記錄 + MinIO 物件)

### 4.2 資料同步
- 刪除檔案時，確保 PostgreSQL 和 MinIO 的資料同步刪除:
  1. 開始事務
  2. 標記檔案為 "deleting"
  3. 刪除 MinIO 物件
  4. 若成功，刪除資料庫記錄並提交事務
  5. 若失敗，回滾事務並記錄錯誤

### 4.3 並發控制
- 使用樂觀鎖 (版本號) 處理並發更新
- 在關鍵表添加 `version` 欄位
- 更新時檢查版本號，防止髒寫

### 4.4 備份策略
- 每日全量資料庫備份
- 每小時增量備份
- MinIO 物件的定期快照
- 備份加密存儲
- 定期測試恢復流程

## 5. 資料庫測試策略

### 5.1 結構測試
- 測試資料表結構是否正確創建
- 測試約束是否生效
- 測試索引是否正確建立

### 5.2 CRUD 操作測試
- 測試所有資料表的基本操作
- 測試關聯操作 (級聯刪除等)
- 測試批量操作性能

### 5.3 索引效率測試
- 使用 `EXPLAIN ANALYZE` 驗證查詢計劃
- 測試常用查詢的索引命中情況
- 測試全文搜尋效率

### 5.4 一致性測試
- 測試事務在異常情況下的行為
- 模擬網路故障、MinIO 服務不可用等情況
- 驗證資料完整性和一致性

### 5.5 效能測試
- 測試大量並發連接
- 測試大數據量下的查詢性能
- 測試 MinIO 物件存取效率

## 6. 資料操作實作 (Data Operations)

### 6.1 檔案刪除級聯操作

當從系統中刪除檔案時，需要確保同時清理所有相關數據，包括：

1. **PostgreSQL 資料表中的記錄**:
   - 首先刪除 `files` 表中的檔案記錄
   - 通過外鍵 CASCADE 自動刪除 `sentences` 表中關聯的所有句子記錄
   - 通過外鍵 CASCADE 自動刪除 `message_references` 表中的相關引用記錄

2. **MinIO 物件儲存中的檔案**:
   - 從 `files` 表獲取 `minio_bucket_name` 和 `minio_object_key`
   - 使用 MinIO 客戶端 API 刪除對應的物件

3. **事務處理**:
   - 使用資料庫事務確保操作的原子性
   - 如果 MinIO 刪除失敗，回滾資料庫事務
   - 實現重試機制處理暫時性故障

#### 6.1.1 資料庫刪除函數
```sql
CREATE OR REPLACE FUNCTION delete_file_with_cleanup(file_uuid_param UUID)
RETURNS BOOLEAN AS $$
DECLARE
    bucket_name VARCHAR;
    object_key VARCHAR;
    success BOOLEAN := FALSE;
BEGIN
    -- 獲取 MinIO 信息
    SELECT minio_bucket_name, minio_object_key INTO bucket_name, object_key
    FROM files
    WHERE file_uuid = file_uuid_param;
    
    -- 記錄刪除操作
    INSERT INTO deletion_logs (file_uuid, minio_bucket_name, minio_object_key, deleted_at)
    VALUES (file_uuid_param, bucket_name, object_key, NOW());
    
    -- 刪除檔案記錄 (會通過 CASCADE 刪除相關記錄)
    DELETE FROM files WHERE file_uuid = file_uuid_param;
    
    -- 標記操作成功
    success := TRUE;
    
    RETURN success;
END;
$$ LANGUAGE plpgsql;
```

#### 6.1.2 刪除日誌表
```sql
CREATE TABLE deletion_logs (
    log_uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_uuid UUID NOT NULL,
    minio_bucket_name VARCHAR(100) NOT NULL,
    minio_object_key VARCHAR(255) NOT NULL,
    deleted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    minio_cleanup_status VARCHAR(20) DEFAULT 'pending',
    minio_cleanup_attempts INTEGER DEFAULT 0,
    minio_cleanup_completed_at TIMESTAMPTZ
);
```

### 6.2 上傳超時處理

系統需要追踪檔案上傳時間，並處理超過 10 分鐘的上傳：

1. **上傳時間追踪**:
   - 當上傳開始時記錄 `upload_started_at` 時間戳
   - 上傳完成時記錄 `upload_completed_at` 時間戳
   - 定期檢查進行中的上傳，標記超過 10 分鐘未完成的為 `timeout`

2. **超時處理函數**:
```sql
CREATE OR REPLACE FUNCTION mark_timed_out_uploads()
RETURNS INTEGER AS $$
DECLARE
    updated_count INTEGER;
BEGIN
    UPDATE files
    SET upload_status = 'timeout',
        error_message = '上傳超時：超過10分鐘未完成',
        updated_at = NOW()
    WHERE upload_status = 'in_progress'
      AND upload_started_at IS NOT NULL
      AND NOW() - upload_started_at > INTERVAL '10 minutes';
    
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RETURN updated_count;
END;
$$ LANGUAGE plpgsql;
```

3. **排程執行**:
   - 使用 Celery Beat 定期執行超時檢查函數
   - 每分鐘運行一次，標記超時的上傳 