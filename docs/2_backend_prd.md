# II. 後端 PRD (Backend PRD - FastAPI)

## 1. 概述與職責 (Overview & Responsibilities)

後端服務是整個系統的核心，負責以下主要職責：
- 提供安全的使用者認證與授權機制
- 處理檔案上傳與儲存管理
- 協調 PDF 處理和內容分析流程
- 管理智能問答流程及相關外部 API 調用
- 透過 WebSocket 提供實時進度更新
- 持久化存儲使用者的對話歷史記錄
- 支援 Docker 容器化部署
- 管理檔案的完整生命週期（上傳、處理、預覽、刪除）

## 2. 技術棧 (Technical Stack)

### 2.1 核心框架與語言
- **語言**: Python 3.10+
- **Web 框架**: FastAPI 0.95+
- **開發伺服器**: Uvicorn
- **生產伺服器**: Gunicorn (worker 數量為 CPU 核心數 * 2 + 1)
- **負載均衡**: Nginx (使用 upstream 模塊實現後端負載平衡)

### 2.2 任務處理與非同步
- **任務隊列**: Celery 5.2+
- **消息代理**: Redis 7.0+ (主從複製 + 哨兵模式)
- **狀態儲存**: Redis (用於儲存任務執行狀態和斷點續傳資訊)
- **併發控制**: Semaphore 和 Rate Limiter (限制外部 API 調用頻率)

### 2.3 資料庫與儲存
- **ORM**: SQLAlchemy 2.0+ (非同步引擎)
- **資料模型**: SQLModel (結合 SQLAlchemy 與 Pydantic)
- **關聯資料庫**: PostgreSQL 14+ (主從架構，讀寫分離)
- **連接池**: 資料庫連接池 (控制和優化資料庫連接數)
- **物件儲存**: MinIO (S3 相容介面，分佈式部署)
- **快取層**: Redis 用於高頻訪問數據快取
- **資源清理**: 實現級聯刪除，確保檔案刪除時同步清理資料庫記錄與MinIO物件

### 2.4 身份驗證與安全
- **密碼雜湊**: BCrypt
- **認證機制**: JWT (access token + refresh token)
- **HTTP 客戶端**: httpx (非同步 HTTP 客戶端，用於呼叫外部 API)

### 2.5 監控與日誌
- **日誌工具**: Loguru
- **請求記錄**: 自訂 FastAPI 中間件
- **性能監控**: Prometheus + Grafana (可選)

## 3. API 端點規格 (API Endpoints Specification)

### 3.1 驗證與授權 (Auth)

#### 3.1.1 註冊
- **路徑**: `/auth/register`
- **方法**: `POST`
- **請求體**:
  ```json
  {
    "email": "user@example.com",
    "password": "strongPassword123"
  }
  ```
- **成功回應** (201 Created):
  ```json
  {
    "user_uuid": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "created_at": "2023-08-18T12:34:56.789Z"
  }
  ```
- **錯誤回應** (409 Conflict):
  ```json
  {
    "detail": "使用者已存在"
  }
  ```
- **驗收標準**:
  - 密碼長度至少 8 個字元，包含至少一個大寫字母和一個數字
  - 電子郵件格式必須有效
  - 生成的 UUID 符合 v4 標準

#### 3.1.2 登入
- **路徑**: `/auth/login`
- **方法**: `POST`
- **請求體**:
  ```json
  {
    "email": "user@example.com",
    "password": "strongPassword123"
  }
  ```
- **成功回應** (200 OK):
  ```json
  {
    "user_uuid": "550e8400-e29b-41d4-a716-446655440000",
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6...",
    "token_type": "bearer"
  }
  ```
- **錯誤回應** (401 Unauthorized):
  ```json
  {
    "detail": "帳號或密碼錯誤"
  }
  ```
- **驗收標準**:
  - access_token 有效期為 30 分鐘
  - refresh_token 有效期為 7 天
  - 連續 5 次登入失敗將暫時鎖定帳戶 15 分鐘

#### 3.1.3 登出
- **路徑**: `/auth/logout`
- **方法**: `POST`
- **請求頭**: `Authorization: Bearer {access_token}`
- **成功回應** (200 OK):
  ```json
  {
    "detail": "成功登出"
  }
  ```
- **驗收標準**:
  - refresh_token 被加入黑名單，無法再用於獲取新的 access_token
  - 用戶的活躍會話記錄被更新

#### 3.1.4 更新 Token
- **路徑**: `/auth/refresh`
- **方法**: `POST`
- **請求體**:
  ```json
  {
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6..."
  }
  ```
- **成功回應** (200 OK):
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6...",
    "token_type": "bearer"
  }
  ```
- **驗收標準**:
  - 使用有效的 refresh_token 能獲取新的 access_token
  - 過期或黑名單中的 refresh_token 會被拒絕

### 3.2 檔案管理 (Files)

#### 3.2.1 上傳檔案
- **路徑**: `/files/upload`
- **方法**: `POST`
- **請求頭**: `Authorization: Bearer {access_token}`
- **請求內容類型**: `multipart/form-data`
- **請求參數**:
  - `files`: 檔案列表 (支援多檔案上傳)
  - `chunk_number` (選填): 當前分片編號
  - `chunk_total` (選填): 總分片數
  - `file_id` (選填): 用於斷點續傳的檔案標識
- **成功回應** (201 Created):
  ```json
  {
    "files": [
      {
        "file_uuid": "550e8400-e29b-41d4-a716-446655440000",
        "original_name": "example.pdf",
        "size_bytes": 1024000,
        "upload_status": "completed",
        "processing_status": "pending",
        "created_at": "2023-08-18T12:34:56.789Z"
      }
    ],
    "upload_id": "abc123" // 用於分片上傳的標識
  }
  ```
- **錯誤回應** (400 Bad Request):
  ```json
  {
    "detail": "檔案格式不支援，僅接受 PDF 檔案"
  }
  ```
- **驗收標準**:
  - 支援一次上傳多達 5 個檔案
  - 僅接受 PDF 檔案 (MIME type: application/pdf)
  - 單一檔案大小上限為 10MB
  - 支援分片上傳和斷點續傳
  - 斷點續傳接受時間最長為 10 分鐘，超過則標記為上傳失敗
  - 生成的檔案 UUID 符合 v4 標準
  - 實現清理機制，定期清理過期的部分上傳文件

#### 3.2.2 取得使用者檔案列表
- **路徑**: `/files`
- **方法**: `GET`
- **請求頭**: `Authorization: Bearer {access_token}`
- **查詢參數**:
  - `page`: 頁碼 (預設: 1)
  - `limit`: 每頁項目數 (預設: 10, 最大: 50)
  - `sort_by`: 排序欄位 (可選: created_at, original_name)
  - `sort_order`: 排序方向 (可選: asc, desc, 預設: desc)
- **成功回應** (200 OK):
  ```json
  {
    "total": 25,
    "page": 1,
    "limit": 10,
    "files": [
      {
        "file_uuid": "550e8400-e29b-41d4-a716-446655440000",
        "original_name": "example.pdf",
        "size_bytes": 1024000,
        "upload_status": "completed",
        "processing_status": "completed",
        "sentence_count": 120,
        "cd_count": 5,
        "od_count": 8,
        "created_at": "2023-08-18T12:34:56.789Z",
        "updated_at": "2023-08-18T13:00:00.000Z"
      },
      // 更多檔案...
    ]
  }
  ```
- **驗收標準**:
  - 僅返回當前用戶的檔案
  - 支援分頁、排序和過濾
  - 包含檔案的處理狀態和統計信息

#### 3.2.3 取得單一檔案詳情
- **路徑**: `/files/{file_uuid}`
- **方法**: `GET`
- **請求頭**: `Authorization: Bearer {access_token}`
- **路徑參數**:
  - `file_uuid`: 檔案的 UUID
- **成功回應** (200 OK):
  ```json
  {
    "file_uuid": "550e8400-e29b-41d4-a716-446655440000",
    "user_uuid": "550e8400-e29b-41d4-a716-446655440000",
    "original_name": "example.pdf",
    "size_bytes": 1024000,
    "minio_bucket_name": "user-550e8400-e29b-41d4-a716-446655440000",
    "minio_object_key": "550e8400-e29b-41d4-a716-446655440000.pdf",
    "upload_status": "completed",
    "processing_status": "completed",
    "error_message": null,
    "sentence_count": 120,
    "cd_count": 5,
    "od_count": 8,
    "created_at": "2023-08-18T12:34:56.789Z",
    "updated_at": "2023-08-18T13:00:00.000Z",
    "download_url": "https://api.example.com/files/550e8400-e29b-41d4-a716-446655440000/download",
    "preview_url": "https://api.example.com/files/550e8400-e29b-41d4-a716-446655440000/preview"
  }
  ```
- **錯誤回應** (404 Not Found):
  ```json
  {
    "detail": "檔案不存在或無權存取"
  }
  ```
- **驗收標準**:
  - 僅允許檔案所有者存取
  - 提供臨時的下載和預覽 URL (有效期 15 分鐘)

#### 3.2.4 刪除檔案
- **路徑**: `/files/{file_uuid}`
- **方法**: `DELETE`
- **請求頭**: `Authorization: Bearer {access_token}`
- **路徑參數**:
  - `file_uuid`: 檔案的 UUID
- **成功回應** (200 OK):
  ```json
  {
    "detail": "檔案已成功刪除"
  }
  ```
- **驗收標準**:
  - 同時刪除 PostgreSQL 中的檔案記錄（files 表）
  - 同時刪除 PostgreSQL 中關聯的 sentences 記錄
  - 同時刪除 MinIO 中的檔案物件
  - 級聯刪除相關的句子記錄和對話引用
  - 僅允許檔案所有者刪除檔案
  - 使用事務確保刪除操作的原子性，防止部分刪除導致的數據不一致

#### 3.2.5 下載檔案
- **路徑**: `/files/{file_uuid}/download`
- **方法**: `GET`
- **請求頭**: `Authorization: Bearer {access_token}`
- **路徑參數**:
  - `file_uuid`: 檔案的 UUID
- **成功回應**: 檔案串流 (application/pdf)
- **驗收標準**:
  - 生成預簽名的 MinIO URL 並重定向
  - 支援大型檔案的分段下載 (HTTP Range header)

#### 3.2.6 預覽檔案
- **路徑**: `/files/{file_uuid}/preview`
- **方法**: `GET`
- **請求頭**: `Authorization: Bearer {access_token}`
- **路徑參數**:
  - `file_uuid`: 檔案的 UUID
- **查詢參數**:
  - `page`: 頁碼 (預設: 1)
- **成功回應** (200 OK): PDF 原始內容或轉換為 HTML/Canvas 的內容
- **驗收標準**:
  - 支援翻頁查看
  - 提供適合嵌入前端的格式
  - 支援高亮顯示特定句子
  - 支援從引用直接跳轉到對應頁面

#### 3.2.7 查看檔案中的特定句子
- **路徑**: `/files/{file_uuid}/sentences/{sentence_uuid}/view`
- **方法**: `GET`
- **請求頭**: `Authorization: Bearer {access_token}`
- **路徑參數**:
  - `file_uuid`: 檔案的 UUID
  - `sentence_uuid`: 句子的 UUID
- **成功回應** (200 OK):
  ```json
  {
    "file_uuid": "550e8400-e29b-41d4-a716-446655440000",
    "sentence_uuid": "550e8400-e29b-41d4-a716-446655440001",
    "page": 5,
    "sentence": "這是一個被引用的句子。",
    "preview_url": "https://api.example.com/files/550e8400-e29b-41d4-a716-446655440000/preview?page=5&highlight=550e8400-e29b-41d4-a716-446655440001"
  }
  ```
- **驗收標準**:
  - 提供句子在PDF中的精確位置
  - 生成能直接在預覽中高亮該句子的URL
  - 支援查看句子上下文

### 3.3 PDF 處理相關 (Processing)

#### 3.3.1 處理 PDF 檔案 (內部使用)
- **路徑**: `/api/process-pdf`
- **方法**: `POST`
- **請求內容類型**: `multipart/form-data`
- **請求參數**:
  - `file`: PDF 檔案
- **成功回應** (200 OK):
  ```json
  {
    "sentences": [
      {
        "sentence": "這是第一個句子。",
        "page": 1
      },
      {
        "sentence": "這是第二個句子。",
        "page": 1
      },
      {
        "sentence": "這是第三個句子。",
        "page": 2
      }
    ]
  }
  ```
- **備註**: 此端點將調用整合的 split_sentences 服務

#### 3.3.2 觸發檔案處理 (管理用)
- **路徑**: `/files/{file_uuid}/process`
- **方法**: `POST`
- **請求頭**: `Authorization: Bearer {access_token}`
- **路徑參數**:
  - `file_uuid`: 檔案的 UUID
- **成功回應** (202 Accepted):
  ```json
  {
    "detail": "處理任務已提交",
    "task_id": "550e8400-e29b-41d4-a716-446655440000"
  }
  ```
- **驗收標準**:
  - 創建 Celery 任務並立即返回任務 ID
  - 用戶可透過 WebSocket 追蹤任務進度 

### 3.4 句子和定義管理 (Sentences)

#### 3.4.1 獲取檔案的句子列表
- **路徑**: `/files/{file_uuid}/sentences`
- **方法**: `GET`
- **請求頭**: `Authorization: Bearer {access_token}`
- **路徑參數**:
  - `file_uuid`: 檔案的 UUID
- **查詢參數**:
  - `page`: 頁碼 (預設: 1)
  - `limit`: 每頁項目數 (預設: 20, 最大: 100)
  - `defining_type`: 過濾類型 (可選: cd, od, none)
  - `page_number`: 過濾特定頁碼 (可選)
- **成功回應** (200 OK):
  ```json
  {
    "total": 120,
    "page": 1,
    "limit": 20,
    "sentences": [
      {
        "sentence_uuid": "550e8400-e29b-41d4-a716-446655440000",
        "file_uuid": "550e8400-e29b-41d4-a716-446655440000",
        "sentence": "這是一個概念型定義的句子。",
        "page": 1,
        "defining_type": "cd",
        "reason": "此句包含明確的概念定義",
        "created_at": "2023-08-18T12:34:56.789Z"
      },
      // 更多句子...
    ]
  }
  ```
- **驗收標準**:
  - 支援分頁和過濾
  - 僅返回用戶自己檔案的句子

#### 3.4.2 搜尋定義
- **路徑**: `/search/definitions`
- **方法**: `GET`
- **請求頭**: `Authorization: Bearer {access_token}`
- **查詢參數**:
  - `query`: 搜尋關鍵字
  - `defining_type`: 過濾類型 (可選: cd, od, both)
  - `limit`: 結果數量上限 (預設: 10, 最大: 50)
- **成功回應** (200 OK):
  ```json
  {
    "results": [
      {
        "sentence_uuid": "550e8400-e29b-41d4-a716-446655440000",
        "file_uuid": "550e8400-e29b-41d4-a716-446655440000",
        "original_name": "example.pdf",
        "sentence": "這是一個概念型定義的句子。",
        "page": 1,
        "defining_type": "cd",
        "reason": "此句包含明確的概念定義",
        "relevance_score": 0.92
      },
      // 更多結果...
    ]
  }
  ```
- **驗收標準**:
  - 使用全文搜尋索引和相關性排序
  - 僅搜尋用戶自己上傳的檔案中的句子

### 3.5 聊天和查詢 (Chat)

#### 3.5.1 提交用戶查詢
- **路徑**: `/chat/query`
- **方法**: `POST`
- **請求頭**: `Authorization: Bearer {access_token}`
- **請求體**:
  ```json
  {
    "query": "什麼是自適應專業知識？",
    "conversation_uuid": "550e8400-e29b-41d4-a716-446655440000"  // 可選，用於繼續對話
  }
  ```
- **成功回應** (202 Accepted):
  ```json
  {
    "query_uuid": "550e8400-e29b-41d4-a716-446655440000",
    "conversation_uuid": "550e8400-e29b-41d4-a716-446655440000",
    "status": "processing",
    "created_at": "2023-08-18T12:34:56.789Z"
  }
  ```
- **驗收標準**:
  - 創建查詢記錄並立即返回查詢 ID 和對話 ID
  - 啟動 Celery 任務處理查詢
  - 將查詢新增至對話歷史記錄

#### 3.5.2 獲取對話歷史
- **路徑**: `/chat/conversations`
- **方法**: `GET`
- **請求頭**: `Authorization: Bearer {access_token}`
- **查詢參數**:
  - `page`: 頁碼 (預設: 1)
  - `limit`: 每頁項目數 (預設: 10, 最大: 50)
- **成功回應** (200 OK):
  ```json
  {
    "total": 15,
    "page": 1,
    "limit": 10,
    "conversations": [
      {
        "conversation_uuid": "550e8400-e29b-41d4-a716-446655440000",
        "title": "關於自適應專業知識的對話",
        "message_count": 6,
        "last_message_at": "2023-08-18T14:30:00.000Z",
        "created_at": "2023-08-18T12:34:56.789Z"
      },
      // 更多對話...
    ]
  }
  ```
- **驗收標準**:
  - 支援分頁
  - 按最後消息時間降序排序

#### 3.5.3 獲取單一對話內容
- **路徑**: `/chat/conversations/{conversation_uuid}`
- **方法**: `GET`
- **請求頭**: `Authorization: Bearer {access_token}`
- **路徑參數**:
  - `conversation_uuid`: 對話的 UUID
- **成功回應** (200 OK):
  ```json
  {
    "conversation_uuid": "550e8400-e29b-41d4-a716-446655440000",
    "title": "關於自適應專業知識的對話",
    "created_at": "2023-08-18T12:34:56.789Z",
    "messages": [
      {
        "message_uuid": "550e8400-e29b-41d4-a716-446655440000",
        "role": "user",
        "content": "什麼是自適應專業知識？",
        "created_at": "2023-08-18T12:34:56.789Z"
      },
      {
        "message_uuid": "660e8400-e29b-41d4-a716-446655440000",
        "role": "assistant",
        "content": "自適應專業知識是指...",
        "references": [
          {
            "sentence_uuid": "550e8400-e29b-41d4-a716-446655440000",
            "file_uuid": "550e8400-e29b-41d4-a716-446655440000",
            "original_name": "example.pdf",
            "sentence": "自適應專業知識是...",
            "page": 3,
            "defining_type": "cd"
          }
        ],
        "created_at": "2023-08-18T12:35:10.789Z"
      },
      // 更多消息...
    ]
  }
  ```
- **驗收標準**:
  - 按時間順序返回對話中的所有消息
  - 包含系統回覆中引用的原文句子詳情

### 3.6 WebSocket 端點

#### 3.6.1 檔案處理進度
- **路徑**: `ws://服務器地址/ws/processing/{file_uuid}`
- **事件類型**:
  - `processing_started`: 處理開始
  - `pdf_extraction_progress`: PDF 文本提取進度
  - `sentence_extraction_detail`: 每批句子提取的詳細信息，包含提取的句子內容
  - `sentence_classification_progress`: 句子分類進度
  - `sentence_classification_detail`: 句子分類的詳細信息，包含分類結果和分類依據
  - `processing_completed`: 處理完成
  - `processing_failed`: 處理失敗
- **範例消息**:
  ```json
  {
    "event": "sentence_classification_progress",
    "file_uuid": "550e8400-e29b-41d4-a716-446655440000",
    "progress": 45,  // 百分比
    "current": 54,
    "total": 120,
    "status": "processing",
    "timestamp": "2023-08-18T12:40:00.000Z"
  }
  ```
  ```json
  {
    "event": "sentence_classification_detail",
    "file_uuid": "550e8400-e29b-41d4-a716-446655440000",
    "sentences": [
      {
        "sentence_uuid": "550e8400-e29b-41d4-a716-446655440000",
        "sentence": "自適應專業知識是指...",
        "defining_type": "cd",
        "reason": "此句包含明確的概念定義",
        "page": 1
      },
      // 更多句子...
    ],
    "timestamp": "2023-08-18T12:40:05.000Z"
  }
  ```
- **驗收標準**:
  - 實時進度更新 (每秒最多 2 次更新)
  - 定期傳送分類詳情，允許前端展示處理中的句子內容
  - 連接中斷時自動重連
  - 僅允許檔案所有者接收其進度更新

#### 3.6.2 查詢處理進度
- **路徑**: `ws://服務器地址/ws/chat/{query_uuid}`
- **事件類型**:
  - `query_processing_started`: 查詢處理開始
  - `keyword_extraction_completed`: 關鍵詞提取完成
  - `database_search_progress`: 資料庫搜尋進度
  - `database_search_result`: 資料庫搜尋結果，包含找到的定義句子
  - `answer_generation_started`: 答案生成開始
  - `referenced_sentences`: 在生成答案時參考的關鍵句子
  - `query_completed`: 查詢處理完成
  - `query_failed`: 查詢處理失敗
- **範例消息**:
  ```json
  {
    "event": "database_search_progress",
    "query_uuid": "550e8400-e29b-41d4-a716-446655440000",
    "keywords": ["自適應專業知識", "專業知識"],
    "progress": 60,  // 百分比
    "current_step": "正在搜尋資料庫中符合關鍵詞的定義",
    "found_definitions": {
      "cd": 3,
      "od": 2
    },
    "timestamp": "2023-08-18T12:40:10.000Z"
  }
  ```
  ```json
  {
    "event": "database_search_result",
    "query_uuid": "550e8400-e29b-41d4-a716-446655440000", 
    "keyword": "自適應專業知識",
    "found_sentences": [
      {
        "sentence_uuid": "550e8400-e29b-41d4-a716-446655440000",
        "file_uuid": "550e8400-e29b-41d4-a716-446655440000",
        "original_name": "example.pdf",
        "sentence": "自適應專業知識是指...",
        "page": 3,
        "defining_type": "cd",
        "relevance_score": 0.92
      },
      // 更多句子...
    ],
    "timestamp": "2023-08-18T12:40:15.000Z"
  }
  ```
  ```json
  {
    "event": "referenced_sentences",
    "query_uuid": "550e8400-e29b-41d4-a716-446655440000",
    "referenced_sentences": [
      {
        "sentence_uuid": "550e8400-e29b-41d4-a716-446655440000",
        "file_uuid": "550e8400-e29b-41d4-a716-446655440000",
        "original_name": "example.pdf",
        "sentence": "自適應專業知識是指...",
        "page": 3,
        "defining_type": "cd"
      },
      // 更多句子...
    ],
    "timestamp": "2023-08-18T12:40:20.000Z"
  }
  ```
- **驗收標準**:
  - 實時進度更新
  - 詳細的處理步驟與進度信息，便於前端展示
  - 每個處理階段提供參考句子的詳細信息，支援前端互動式查看
  - 僅允許查詢提交者接收進度更新

## 4. 核心業務邏輯詳述

### 4.1 用戶認證與管理

- **註冊流程**:
  1. 接收電子郵件和密碼
  2. 驗證電子郵件格式和密碼強度
  3. 檢查電子郵件是否已存在
  4. 使用 BCrypt 對密碼進行雜湊
  5. 生成 UUID v4 作為 user_uuid
  6. 將用戶記錄儲存到資料庫
  7. 在 MinIO 中為用戶創建專屬的 bucket
  8. 返回用戶信息

- **登入流程**:
  1. 接收電子郵件和密碼
  2. 查詢資料庫獲取用戶記錄
  3. 使用 BCrypt 驗證密碼
  4. 生成 JWT access token 和 refresh token
  5. 記錄用戶登入活動
  6. 返回令牌和用戶信息

- **令牌刷新流程**:
  1. 接收 refresh token
  2. 驗證 token 簽名和有效期
  3. 檢查 token 是否在黑名單中
  4. 生成新的 access token
  5. 返回新的 access token

- **登出流程**:
  1. 接收 access token
  2. 解析 token 獲取用戶信息
  3. 將 refresh token 加入黑名單
  4. 更新用戶的活躍會話記錄
  5. 返回成功訊息

### 4.2 檔案上傳與處理流程

#### 4.2.1 檔案上傳邏輯
1. **接收檔案**:
   - 驗證檔案類型 (僅接受 PDF)
   - 驗證檔案大小 (上限 10MB)
   - 處理分片上傳 (如有)

2. **檔案儲存**:
   - 生成 file_uuid (UUID v4)
   - 將檔案存入 MinIO (bucket 名稱為 user_uuid)
   - 物件鍵為 file_uuid.pdf

3. **資料庫記錄**:
   - 在 files 表中創建記錄 (file_uuid, user_uuid, 原始檔名, MinIO 位置等)
   - 設置 processing_status 為 "pending"

4. **處理任務提交**:
   - 建立 Celery 任務處理該檔案
   - 立即返回結果，包含 file_uuid 和 upload_status

#### 4.2.2 檔案處理流程 (Celery 任務)
1. **PDF 文本提取**:
   - 透過 API 調用整合的 split_sentences 服務
   - 接收包含句子列表的回應 (句子文本和頁碼)
   - 透過 WebSocket 更新進度 (pdf_extraction_progress)
   - 每批處理 20 個句子後，發送 sentence_extraction_detail 事件，包含處理的句子內容

2. **句子儲存**:
   - 為每個句子生成 sentence_uuid (UUID v4)
   - 將句子儲存到資料庫 (sentence_uuid, file_uuid, user_uuid, sentence, page)
   - 設置 defining_type 初始值為 "none"

3. **句子分類**:
   - 對每個句子調用 n8n API 進行 CD/OD 分類
   - 實作指數退避重試機制 (最多 3 次，起始間隔 1 秒)
   - 設置每個 API 調用的超時為 30 秒
   - 每完成 10% 的句子分類，透過 WebSocket 更新進度
   - 每完成 10 個句子的分類，發送 sentence_classification_detail 事件，包含這些句子的分類結果和分類依據

4. **結果儲存**:
   - 更新每個句子的 defining_type 和 reason
   - 更新檔案記錄的 processing_status 為 "completed"
   - 計算並更新檔案的統計數據 (sentence_count, cd_count, od_count)
   - 透過 WebSocket 發送完成通知

5. **錯誤處理**:
   - 捕獲處理過程中的任何錯誤
   - 記錄詳細的錯誤信息到日誌
   - 更新檔案記錄的 processing_status 為 "failed" 和 error_message
   - 透過 WebSocket 發送失敗通知，包含錯誤詳情

### 4.3 使用者查詢處理流程

#### 4.3.1 查詢處理邏輯 (Celery 任務)
1. **接收查詢**:
   - 驗證查詢內容 (不為空，長度適當)
   - 查詢是否屬於現有對話或創建新對話
   - 生成 query_uuid (UUID v4)
   - 將查詢儲存到資料庫
   - 透過 WebSocket 發送處理開始通知

2. **關鍵詞提取**:
   - 調用 n8n API 提取查詢中的關鍵詞
   - 實作指數退避重試機制
   - 透過 WebSocket 更新提取到的關鍵詞 (keyword_extraction_completed 事件)
   - 如無有效關鍵詞，返回適當的提示消息

3. **資料庫搜尋**:
   - 對每個關鍵詞搜索用戶的 sentences 表
   - 過濾 defining_type 為 "cd" 或 "od" 的記錄
   - 使用全文搜尋和相關性排序
   - 透過 WebSocket 實時更新搜尋進度 (database_search_progress 事件)
   - 每找到一批與關鍵詞相關的句子，立即透過 WebSocket 發送句子詳情 (database_search_result 事件)

4. **答案生成**:
   - 將搜集到的 CD/OD 句子分組傳送給 n8n API
   - 發送 answer_generation_started 事件
   - 在生成答案前發送 referenced_sentences 事件，包含將用於生成答案的關鍵句子
   - 接收生成的回答
   - 添加原文引用 (sentence_uuid, file_uuid, original_name, page)
   - 透過 WebSocket 更新處理完成通知 (query_completed 事件)

5. **結果儲存**:
   - 將系統回答儲存到資料庫 (messages 表)
   - 關聯引用的原文句子
   - 更新對話的最後活動時間和標題

#### 4.3.2 原文引用格式
系統回答將包含以下結構的原文引用:
```json
{
  "content": "自適應專業知識是指...",
  "references": [
    {
      "sentence_uuid": "550e8400-e29b-41d4-a716-446655440000",
      "file_uuid": "550e8400-e29b-41d4-a716-446655440000",
      "original_name": "example.pdf",
      "sentence": "自適應專業知識是...",
      "page": 3,
      "defining_type": "cd"
    }
  ]
}
```

### 4.4 併發處理與負載平衡策略

#### 4.4.1 API 請求處理
- **限流機制**:
  - 基於 IP 的限流: 每個 IP 每分鐘最多 120 個請求
  - 基於用戶的限流: 每個用戶每分鐘最多 60 個請求
  - 基於端點的限流: 上傳端點每分鐘最多 10 個請求
  - 超過限制的請求返回 429 Too Many Requests 狀態碼

- **連接池管理**:
  - 使用 httpx 的非同步連接池管理外部 API 調用
  - 資料庫連接池大小: 最小 10，最大 50
  - 連接獲取超時: 60 秒，超時後返回錯誤

- **請求隊列**:
  - 針對長時間處理的請求實施請求隊列
  - 隊列大小: 最大 100 個待處理請求
  - 隊列滿時返回 503 Service Unavailable 狀態碼

#### 4.4.2 任務處理和並行策略
- **Celery 工作節點配置**:
  - 每個工作節點處理 8 個並行任務
  - 每個任務設置最大執行時間 (30 分鐘)
  - 優先級隊列: high, default, low 三級
  - 任務自動重試機制: 最多 3 次，指數退避間隔

- **資源隔離**:
  - 檔案處理任務與查詢處理任務使用不同的工作隊列
  - 關鍵任務與非關鍵任務隔離
  - 使用 Celery Canvas 管理工作流程，避免阻塞

- **任務調度優化**:
  - 大任務拆分為小任務並行處理
  - 實施公平調度，避免長任務佔用所有資源
  - 任務進度監控和超時處理

#### 4.4.3 效能監控與自動擴展
- **監控指標**:
  - 系統 CPU、記憶體、磁碟 I/O 使用率
  - 請求響應時間、請求等待時間
  - 任務處理時間、任務等待時間
  - API 調用錯誤率和超時率

- **告警機制**:
  - 定義關鍵指標閾值 (如 CPU > 80%, 響應時間 > 2s)
  - 通過 Email/Slack 發送告警
  - 自動擴展觸發條件配置

- **動態擴展**:
  - 根據任務隊列長度自動調整 Celery worker 數量
  - 基於 CPU 使用率自動擴展後端實例
  - 按照預定策略進行服務降級

## 5. 資料庫互動介面

### 5.1 PostgreSQL 互動
- 使用 SQLAlchemy 2.0+ 的非同步引擎
- 定義 SQLModel 模型對應資料表結構
- 實作資料庫工廠模式，便於測試和依賴注入
- 使用連接池管理資料庫連接

### 5.2 MinIO 互動
- 使用官方 MinIO Python SDK (minio-py)
- 對常見操作進行封裝 (創建桶、上傳/下載物件、生成預簽名 URL)
- 實作分片上傳和斷點續傳的邏輯
- 透過 Redis 儲存分片上傳的狀態信息
- 實現自動清理過期的分片上傳

## 6. 錯誤處理與日誌策略

### 6.1 統一的錯誤回應格式
```json
{
  "detail": "錯誤描述",
  "code": "ERROR_CODE",
  "timestamp": "2023-08-18T12:34:56.789Z",
  "path": "/api/resource",
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### 6.2 日誌記錄級別與內容
- **DEBUG**: 詳細的開發信息，如函數入參和返回值
- **INFO**: 正常操作信息，如用戶登入、檔案上傳成功
- **WARNING**: 潛在問題警告，如 API 重試
- **ERROR**: 錯誤信息，如資料庫連接失敗、API 調用失敗
- **CRITICAL**: 嚴重錯誤，如應用組件不可用

每條日誌至少包含:
- 時間戳
- 日誌級別
- 請求 ID (用於追踪)
- 用戶 ID (如適用)
- 操作描述
- 相關錯誤詳情 (如適用)

### 6.3 穩定性與應急處理
- **斷路器模式**:
  - 外部服務故障檢測 (連續 5 次失敗觸發)
  - 斷路器狀態: 關閉 (正常) -> 開啟 (失敗) -> 半開 (測試)
  - 自動恢復嘗試間隔: 起始 30 秒，最長 5 分鐘

- **流量管理**:
  - 動態請求優先級調整
  - 非關鍵請求降級或延遲處理
  - 大量請求時啟用請求合併機制

- **資源保護**:
  - 系統高負載時暫時拒絕非關鍵請求
  - API 限流和節流閥
  - 內存和連接數保護機制

- **應急處理流程**:
  - 自動故障轉移到備用服務
  - 系統過載時的自動調整策略
  - 事件回報與恢復流程

## 7. 後端測試策略

### 7.1 單元測試 (Pytest)
- **模型測試**: 驗證資料模型的驗證邏輯、關聯關係與查詢方法
- **服務層測試**: 測試業務邏輯層的功能，使用模擬的資料庫和外部服務
- **輔助函數測試**: 確保工具函數、格式轉換、驗證邏輯等正確運作
- **API 處理程序測試**: 測試各 API 端點的邏輯，使用 FastAPI 的測試客戶端
- **WebSocket 處理程序測試**: 測試 WebSocket 端點的連接、消息處理和斷開邏輯

### 7.2 整合測試 (Pytest)
- **資料庫整合測試**: 使用測試資料庫測試實際的資料操作
- **MinIO 整合測試**: 使用測試 MinIO 實例測試檔案儲存邏輯
- **Celery 任務測試**: 測試非同步任務的排程和執行
- **端點整合測試**: 模擬完整的請求/回應週期，測試端到端流程
- **WebSocket 整合測試**: 測試 WebSocket 連接的建立和消息推送

### 7.3 模擬外部依賴
- **模擬 split_sentences 服務**: 建立模擬回應，模擬不同大小的 PDF 處理結果
- **模擬 n8n API**: 模擬關鍵詞提取、句子分類、答案生成等 API 的回應
- **模擬錯誤情境**: 測試網路超時、服務不可用、無效回應等情況的處理
- **模擬部分成功**: 測試只有部分 API 調用成功的情況（如部分句子分類失敗）

## 8. API 文件

### 8.1 OpenAPI 自動生成
- 使用 FastAPI 的內建 OpenAPI 規範生成功能
- 自動生成 `/docs` 和 `/redoc` 端點
- 生成 JSON 格式的 OpenAPI 規範文件，供前端和其他服務使用
- 為所有端點添加詳細的中文描述和範例

### 8.2 API 文檔內容
- 端點 URL、HTTP 方法、請求頭
- 請求和回應的詳細結構定義
- 所有可能的狀態碼及其含義
- 身份驗證和授權要求
- 分頁、排序和過濾選項的使用說明
- WebSocket 端點的連接方式和事件類型
- API 呼叫範例 (使用 curl 或 httpx)

### 8.3 API 更新策略
- 維護 API 版本號
- 向後相容的更新不變更版本號
- 不相容的更新使用新的版本號
- 廢棄的 API 保留一段時間並標記為過時

## 9. Docker 容器化部署 (Docker Containerization)

### 9.1 容器組織結構

系統採用 Docker 容器化部署，每個主要組件都有專屬的容器：

```
├── backend
│   ├── Dockerfile               # 主後端服務
│   ├── Dockerfile.worker        # Celery 工作節點
│   └── Dockerfile.beat          # Celery 定時任務
├── split_sentences
│   └── Dockerfile               # split_sentences 服務
├── frontend
│   └── Dockerfile               # 前端應用
├── nginx
│   ├── Dockerfile               # Web 伺服器
│   └── conf                     # Nginx 配置
├── postgres
│   └── init                     # 初始化腳本
└── minio
    └── config                   # MinIO 配置
```

### 9.2 主要容器設計

#### 9.2.1 後端容器 (Backend Container)

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# 設置虛擬環境
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"

# 安裝依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用代碼
COPY . .

# 設置環境變數
ENV PYTHONUNBUFFERED=1
ENV DATABASE_URL=postgresql://user:password@postgres_master:5432/app
ENV MINIO_URL=minio:9000
ENV MINIO_ACCESS_KEY=minioaccess
ENV MINIO_SECRET_KEY=miniosecret
ENV REDIS_URL=redis://redis_master:6379/0
ENV PDF_SPLITTER_URL=http://pdf_sentence_splitter:8000
ENV MAX_WORKERS=8
ENV CONCURRENCY_LIMIT=60
ENV UPLOAD_TIMEOUT_MINUTES=10

# 暴露端口
EXPOSE 8000

# 啟動命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 9.2.2 Celery Worker 容器 (Celery Worker Container)

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# 設置虛擬環境
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"

# 安裝依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用代碼
COPY . .

# 設置環境變數
ENV PYTHONUNBUFFERED=1
ENV DATABASE_URL=postgresql://user:password@postgres_master:5432/app
ENV MINIO_URL=minio:9000
ENV MINIO_ACCESS_KEY=minioaccess
ENV MINIO_SECRET_KEY=miniosecret
ENV REDIS_URL=redis://redis_master:6379/0
ENV PDF_SPLITTER_URL=http://pdf_sentence_splitter:8000
ENV CELERY_CONCURRENCY=8

# 啟動命令
CMD ["celery", "-A", "app.worker.celery", "worker", "--loglevel=info", "--concurrency=8"]
```

#### 9.2.3 split_sentences 服務容器

```dockerfile
FROM python:3.9-slim

# 設置工作目錄
WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 複製需要的檔案
COPY requirements.txt .

# 安裝 Python 依賴
RUN pip install --no-cache-dir -r requirements.txt && \
    python -m spacy download zh_core_web_sm

# 複製應用程式碼
COPY . .

# 創建上傳目錄
RUN mkdir -p upload_data && chmod 777 upload_data

# 暴露端口
EXPOSE 8000

# 啟動應用
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 9.3 容器網絡與通信

- 使用 Docker Compose 的網絡功能，創建內部網絡以便容器間通信
- 使用服務名稱作為主機名進行容器間通信
- 只暴露必要的端口到主機（如 Nginx 80/443, MinIO 9000/9001）

### 9.4 容器健康檢查與重啟策略

```yaml
services:
  backend:
    build: ./backend
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    # 其他配置...
```

### 9.5 資料持久化

- 使用命名卷保存關鍵數據
- PostgreSQL 數據存儲在單獨的卷中
- MinIO 對象存儲使用專用卷
- Redis 數據也使用卷持久化

### 9.6 環境變數管理

- 開發環境使用 `.env` 文件
- 生產環境使用 Docker Secrets 或環境配置
- 敏感資訊（密碼、API 金鑰）通過安全方式注入

### 9.7 統一部署流程

整個系統採用單一的`docker-compose.yml`配置進行部署，包含所有服務組件：

```yaml
version: '3.8'
services:
  # 網頁伺服器
  nginx:
    image: nginx:alpine
    # 配置...
  
  # 前端應用
  frontend:
    build: ./frontend
    # 配置...
  
  # 後端API服務
  backend:
    build: ./backend
    # 配置...
  
  # split_sentences文字切分服務
  pdf_sentence_splitter:
    build: ./split_sentences
    ports:
      - "8000:8000"
    volumes:
      - ./upload_data:/app/upload_data
      - ./split_sentences/app:/app/app
    environment:
      - MAX_WORKERS=8
      - PYTHONUNBUFFERED=1
  
  # Celery工作節點
  celery_worker:
    build:
      context: ./backend
      dockerfile: Dockerfile.worker
    # 配置...
  
  # 其他服務（Redis、PostgreSQL、MinIO等）
  # ...
```

### 9.8 部署與啟動指令

系統採用單一指令即可部署整個應用堆疊：

```bash
# 構建並啟動所有服務
docker-compose up -d

# 查看服務狀態
docker-compose ps

# 查看服務日誌
docker-compose logs -f [service_name]

# 停止所有服務
docker-compose down
```

這種整合式部署方式確保所有服務使用相同的網絡和環境變數，實現無縫協作。

## 10. 檔案處理生命週期 (File Processing Lifecycle)

### 10.1 上傳流程

1. **初始化上傳**
   - 前端發起上傳請求，後端生成 `upload_id`
   - 設置上傳超時計時器（10分鐘）

2. **分片上傳**
   - 將檔案分割為多個小塊（如 1MB）
   - 依序上傳每個分片
   - 每個分片上傳成功後更新 Redis 中的進度

3. **完成上傳**
   - 所有分片上傳完成後，後端合併檔案
   - 將元數據寫入 PostgreSQL
   - 超過 10 分鐘未完成則標記為上傳失敗

### 10.2 處理流程

1. **文本提取**
   - 從 PDF 提取所有文本內容
   - 按頁碼組織
   - 通過 WebSocket 更新進度

2. **句子切分**
   - 將文本切分為句子
   - 保存頁碼與句子的對應關係
   - 通過 WebSocket 更新進度

3. **定義分類**
   - 分析每個句子是否為 CD 或 OD
   - 記錄分類結果與理由
   - 通過 WebSocket 更新進度與分類依據

### 10.3 預覽與引用

1. **檔案預覽**
   - 使用 PDF.js 或類似技術在前端渲染 PDF
   - 支援頁面導航

2. **句子引用**
   - 在系統回應中引用原文句子
   - 支援點擊跳轉至原文位置
   - 在原文位置高亮顯示引用句子

3. **上下文查看**
   - 查看引用句子的前後文
   - 在原 PDF 中標記關鍵信息

### 10.4 刪除流程

1. **驗證權限**
   - 確認當前用戶擁有刪除權限

2. **開始事務**
   - 啟動資料庫事務

3. **刪除檔案記錄**
   - 從 files 表中刪除記錄
   - 級聯刪除相關的 sentences 記錄
   - 級聯刪除引用記錄

4. **刪除 MinIO 檔案**
   - 從 MinIO 中刪除對應的 PDF 檔案
   
5. **提交事務**
   - 確保所有刪除操作成功完成
   - 若任一步驟失敗則回滾事務 