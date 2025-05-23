# I. 總體產品 PRD (Overall Product PRD)

## 1. 產品概述 (Product Overview)

### 1.1 核心價值與目標

本系統為一個基於 AI 的文件分析與互動平台，核心價值在於：
- 幫助使用者快速分析 PDF 文件中的概念型定義(CD)和操作型定義(OD)
- 提供智能問答功能，根據文檔內容回答使用者的查詢
- 自動引用原始文檔，增強回答的可信度和可追溯性

### 1.2 要解決的主要問題

- 大量文獻閱讀時難以快速識別核心概念及其定義
- 研究過程中需要反覆查詢和確認概念定義的低效率
- 問答過程缺乏明確的原文引用，導致可信度降低
- 多文件管理與檢索的複雜性

## 2. 目標用戶 (Target Audience)

### 2.1 用戶畫像 (User Personas)

#### 主要用戶：研究人員
- **特徵**：博士生、學術研究員、專業領域研究人員
- **目標**：高效整理文獻中的概念定義，快速查找特定定義
- **痛點**：閱讀大量論文時難以組織和記憶各種概念定義

#### 次要用戶：學生
- **特徵**：大學生、研究所學生
- **目標**：學習和理解學術文獻中的專業概念
- **痛點**：學術文獻中概念繁多，難以理解和區分

### 2.2 主要用戶故事

- 作為一名研究人員，我希望上傳多篇 PDF 論文，系統能自動識別並分類其中的概念型和操作型定義，以便我快速了解核心概念
- 作為一名博士生，我希望能詢問系統關於特定概念的問題，並得到基於上傳文件的精確答案，同時提供原文引用，以便在論文中正確引用
- 作為一名學生，我希望能上傳課程閱讀材料，並通過與系統的對話來理解複雜概念，以便提升學習效率

## 3. 整體系統架構圖 (High-Level System Architecture)

### 3.1 系統組件與協同工作方式

```
┌─────────────┐         ┌─────────────┐
│             │         │             │
│  外部 n8n   │         │ split_sentences │
│   API 服務   │         │  API 服務     │
│             │         │ (水平擴展)    │
└──────┬──────┘         └──────┬──────┘
       │                       │
       │ (API Call)            │ (API Call)
       │                       │
       │                       │
       ▼                       ▼
┌─────────────────────────────────────────┐
│                                         │
│              後端集群                    │
│          (FastAPI + Nginx)              │
│                                         │
└───────────────┬─────────────────────────┘
                │                        ▲
                │ (HTTP/WebSocket)       │ (任務提交/狀態查詢)
                ▼                        │
┌───────────────────────────────────────────────┐
│                                               │
│                  前端                          │
│                (React)                        │
│                                               │
└───────────────────────────────────────────────┘


                 ┌───────────────────┐
                 │                   │
                 │    後端集群        │
                 │  內部資源與連接     │
                 │                   │
                 └─────────┬─────────┘
                           │
                           │ (資料存取、提交任務)
                           │
            ┌──────────────┼──────────────┐
            │              │              │
    ┌───────▼──────┐ ┌─────▼─────┐ ┌──────▼──────┐
    │              │ │           │ │             │
    │ PostgreSQL   │ │ MinIO 集群 │ │ Redis 集群  │
    │ (主從架構)    │ │(分佈式存儲)│ │(主從 + 哨兵)│
    │              │ │           │ │             │
    └──────▲───────┘ └─────▲─────┘ └──────┬──────┘
           │               │              │
           │               │              │ (任務隊列)
           │               │              │
           │               │       ┌──────▼──────┐
           │               │       │             │
           └───────────────┴───────┤ Celery      │
                 (讀寫操作)         │ Workers     │
                                   │ (多工作節點) │
                                   └─────────────┘
```

**組件說明:**
- **前端 (React)**: 使用者互動介面，負責展示資訊、接收使用者輸入，並只與後端API通信。所有的數據存取和處理邏輯都通過後端集群進行，前端不直接訪問任何資料庫、Celery Worker或其他服務。

- **後端集群 (FastAPI + Nginx)**: 系統核心業務邏輯處理中心。負責使用者認證、檔案管理、協調文件處理流程、智能問答、管理 `Celery` 非同步任務、與 `PostgreSQL` 資料庫和 `MinIO` 物件儲存互動，並透過 WebSocket 提供實時更新。後端集群會分別調用 `split_sentences` API 處理文件切分，以及調用 `n8n` API 處理 AI 相關任務。後端負責將長時間執行的任務提交到Redis隊列，並可從Redis或資料庫查詢任務狀態和結果。

- **外部 n8n API 服務**: 外部的自動化工作流程服務，提供 AI 相關的 API，如句子分類 (OD/CD 判斷)、關鍵詞提取、答案生成等。由後端集群按需調用，也可能由Celery Workers在執行非同步任務時調用。

- **split_sentences API 服務**: 獨立的 API 服務，專門負責將上傳的 PDF 文件內容切分成句子。此服務由後端集群調用，也可能由Celery Workers在執行非同步任務時調用。程式碼本體無需更動，僅需啟動服務即可供調用。

- **PostgreSQL (主從架構)**: 關聯式資料庫，用於持久化存儲使用者資訊、檔案元數據、句子內容、對話歷史等結構化數據。採用主從架構以提高可用性和讀取效能。只與後端集群和Celery Workers交互，不直接與前端或其他外部服務連接。

- **MinIO 集群 (分佈式存儲)**: S3 相容的物件儲存服務，用於存儲使用者上傳的原始 PDF 檔案。採用集群部署以保證數據的可靠性和可擴展性。同樣只與後端集群和Celery Workers交互。

- **Redis 集群 (主從 + 哨兵)**: 高效能的記憶體資料庫。在此系統中主要扮演兩個角色：1) 作為 `Celery` 的消息代理 (Message Broker)，管理任務隊列，接收後端提交的任務並分發給Celery Workers。2) 作為快取層，儲存熱點數據或任務狀態，提升系統回應速度。採用集群和哨兵模式確保高可用性。

- **Celery Workers (多工作節點)**: 分佈式任務隊列的執行單元。負責處理後端提交的耗時非同步任務，例如 PDF 文件解析、調用外部 AI API (n8n)、資料庫密集型操作等。Celery Workers從Redis獲取任務，執行處理後可能將結果寫回Redis或直接更新PostgreSQL或MinIO。**Celery不會直接與前端通信**，任務進度和結果的更新是通過後端（使用WebSocket）推送給前端的。

### 3.2 Docker 容器化部署 (Container Deployment)

整個系統以 Docker 為基礎建置，實現容器化部署，具有以下優勢：
- 環境一致性：確保開發、測試和生產環境一致
- 快速部署：使用 Docker Compose 或 Kubernetes 進行快速部署和擴展
- 可移植性：容器可在任何支援 Docker 的環境中運行
- 資源隔離：各服務獨立運行，避免相互干擾
- 易於維護：支援滾動更新和版本控制

#### 3.2.1 Docker Compose 部署示意

```yaml
version: '3.8'
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/conf:/etc/nginx/conf.d
      - ./nginx/ssl:/etc/nginx/ssl
      - ./nginx/logs:/var/log/nginx
    depends_on:
      - backend
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 256M

  frontend:
    build: ./frontend
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
    depends_on:
      - nginx
    environment:
      - NODE_ENV=production
  
  backend:
    build: ./backend
    deploy:
      replicas: 4
      resources:
        limits:
          cpus: '1'
          memory: 1G
    depends_on:
      - postgres_master
      - redis_master
      - minio
      - pdf_sentence_splitter
    environment:
      - DATABASE_URL=postgresql://user:password@postgres_master:5432/app
      - MINIO_URL=minio:9000
      - MINIO_ACCESS_KEY=minioaccess
      - MINIO_SECRET_KEY=miniosecret
      - REDIS_URL=redis://redis_master:6379/0
      - PDF_SPLITTER_URL=http://pdf_sentence_splitter:8000
      - MAX_WORKERS=8
      - CONCURRENCY_LIMIT=60
      - UPLOAD_TIMEOUT_MINUTES=10
  
  pdf_sentence_splitter:
    build: ./split_sentences
    ports:
      - "8000:8000"
    volumes:
      - ./upload_data:/app/upload_data
      - ./split_sentences/app:/app/app
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 2G
    environment:
      - MAX_WORKERS=8
      - PYTHONUNBUFFERED=1
  
  celery_worker:
    build:
      context: ./backend
      dockerfile: Dockerfile.worker
    deploy:
      replicas: 5
      resources:
        limits:
          cpus: '1'
          memory: 1G
    depends_on:
      - redis_master
      - postgres_master
      - minio
      - pdf_sentence_splitter
    environment:
      - DATABASE_URL=postgresql://user:password@postgres_master:5432/app
      - MINIO_URL=minio:9000
      - MINIO_ACCESS_KEY=minioaccess
      - MINIO_SECRET_KEY=miniosecret
      - REDIS_URL=redis://redis_master:6379/0
      - PDF_SPLITTER_URL=http://pdf_sentence_splitter:8000
      - CELERY_CONCURRENCY=8
  
  celery_beat:
    build:
      context: ./backend
      dockerfile: Dockerfile.beat
    deploy:
      replicas: 1
      resources:
        limits:
          cpus: '0.2'
          memory: 256M
    depends_on:
      - redis_master
    environment:
      - REDIS_URL=redis://redis_master:6379/0
  
  postgres_master:
    image: postgres:14
    volumes:
      - postgres_master_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_PASSWORD=password
      - POSTGRES_USER=user
      - POSTGRES_DB=app
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
    command: postgres -c max_connections=200
  
  postgres_slave:
    image: postgres:14
    volumes:
      - postgres_slave_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_PASSWORD=password
      - POSTGRES_USER=user
      - POSTGRES_DB=app
    deploy:
      replicas: 1
      resources:
        limits:
          cpus: '2'
          memory: 4G
    command: postgres -c max_connections=200
    depends_on:
      - postgres_master
  
  minio:
    image: minio/minio
    volumes:
      - minio_data:/data
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      - MINIO_ROOT_USER=minioadmin
      - MINIO_ROOT_PASSWORD=minioadmin
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '1'
          memory: 2G

  redis_master:
    image: redis:7.0-alpine
    volumes:
      - redis_master_data:/data
    command: redis-server --requirepass redis_password --maxclients 100
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G

  redis_slave:
    image: redis:7.0-alpine
    volumes:
      - redis_slave_data:/data

volumes:
  postgres_master_data:
  postgres_slave_data:
  redis_master_data:
  redis_slave_data:
  minio_data:

### 3.3 主要的資料流程和控制流程

1. **用戶註冊/登入流程**:
   - 前端發送登入/註冊請求 → 後端驗證 → 生成 JWT 令牌 → 前端存儲令牌用於後續請求

2. **檔案上傳與處理流程**:
   - 前端上傳檔案 → 後端接收並存入 MinIO → 後端自動啟動 Celery 背景處理任務 → 
   - Worker 調用本地已整合的 split_sentences 服務進行文件切分 → Worker 接著調用 n8n API 進行句子分類 → 
   - Worker 將處理的每個階段和進度透過 WebSocket 實時推送到前端 → 前端顯示詳細進度信息 →
   - Worker 更新資料庫並完成最終處理

3. **使用者查詢處理流程**:
   - 使用者輸入查詢 → 後端接收 → 自動建立 Celery 任務 → Worker 提取關鍵詞 → 
   - Worker 查詢資料庫中的相關定義 → Worker 調用 n8n API 組合回答 → 
   - Worker 添加原文引用 → 整個處理過程的每個階段進度透過 WebSocket 實時回傳到前端 →
   - 前端顯示處理進度及結果，並支援點擊查看處理過程中參照的原句

## 4. 系統關鍵功能 (Key Features)

### 4.1 檔案上傳與處理

#### 4.1.1 上傳流程
- 支援多檔案上傳
- 實現斷點續傳 (超過10分鐘未完成視為上傳失敗)
- 檔案上傳後自動進行處理
- 通過 WebSocket 實時更新處理進度

#### 4.1.2 檔案預覽功能
- 使用者可以在系統中預覽已上傳的 PDF 檔案
- 提供頁面導航和縮放功能
- 支援直接在預覽中跳轉到包含特定句子的頁面
- 高亮顯示引用的句子

#### 4.1.3 檔案管理
- 列出所有已上傳檔案
- 查看檔案處理狀態和統計數據
- 下載原始檔案
- 刪除檔案 (同時刪除 PostgreSQL 中的記錄和 MinIO 中的檔案)

### 4.2 聊天與問答功能

#### 4.2.1 查詢流程
- 使用者提交自然語言查詢
- 系統在資料庫中查找相關定義
- 調用 n8n API 組合回答
- 通過 WebSocket 同步處理進度

#### 4.2.2 互動參考功能
- 在回答中引用原文句子
- 點擊引用句子時可跳轉至對應 PDF 頁面
- 在處理步驟中顯示參照的句子
- 在查看參照句子時可查看其上下文

### 4.3 進度顯示與互動功能

#### 4.3.1 處理進度展示
- 通過 WebSocket 即時更新進度
- 顯示當前處理階段 (文本提取、句子分割、定義分類等)
- 展示處理百分比和估計剩餘時間

#### 4.3.2 互動式查看參考句子
- 點擊進度條可查看當前處理的句子
- 滑鼠懸停在引用上顯示原文預覽
- 點擊引用可跳轉至 PDF 對應頁面
- 高亮顯示參考的句子

## 5. 全域非功能性需求 (Global Non-Functional Requirements)

### 5.1 安全性 (Security)
- 使用 HTTPS 加密所有通信
- 實施 CORS 政策，限制跨域請求
- JWT 身份驗證，含有效期和刷新機制
- 密碼使用 BCrypt 加密存儲
- MinIO 對象存儲基於用戶隔離，確保用戶只能存取自己的檔案

### 5.2 性能 (Performance)
- API 響應時間：簡單查詢 < 200ms，複雜查詢 < 1s
- 檔案上傳支援斷點續傳和分片上傳
- 長時間運行的任務轉為非同步處理，避免阻塞
- 使用資料庫索引優化查詢效率
- 使用 WebSocket 實時推送更新，減少輪詢

### 5.3 可擴展性 (Scalability)
- 所有服務採用無狀態設計，支援水平擴展
- 使用 Nginx 作為負載均衡器分發請求到多個後端實例
- 資料庫採用主從架構，提高讀取效能
- Redis 採用主從+哨兵模式，確保高可用性
- MinIO 配置為分佈式部署，提高存儲容量和存取效能
- Celery Worker 支援動態擴展，根據負載自動調整工作節點數量
- split_sentences 服務採用叢集部署，提高並行處理能力
- 使用連接池和併發限制控制外部服務的請求量
- 系統可輕鬆擴展至支援 100+ 並發用戶

### 5.4 易用性 (Usability)
- 直觀的文件上傳界面，支援拖放
- 清晰的進度指示，讓用戶實時了解系統處理狀態和每個階段的進展
- 提供處理失敗的明確錯誤訊息
- 回答中提供互動式原文引用，增強可信度並允許使用者查看引用來源
- 系統處理過程中各階段的參考句子可通過點擊互動方式查看，方便使用者對處理流程進行覆核
- 支援鍵盤快捷鍵 (例如 Shift+Enter 換行)，確保在 Windows/Mac 不同作業系統下，使用中文輸入法時快捷鍵功能依然能正常運作

### 5.5 可維護性 (Maintainability)
- 遵循模塊化設計原則
- 完整的 API 文檔 (OpenAPI 規範)
- 結構化日誌記錄，便於問題排查
- 單元測試與整合測試覆蓋核心功能
- 具備基本監控指標 (API 請求量、處理時間、錯誤率)

### 5.6 國際化 (Internationalization)
- 預設語言為繁體中文 (zh-TW)
- 設計支援未來添加多語言的可能性
- 日期時間格式依據用戶當地設置

## 6. 整體測試策略 (Overall Testing Strategy)

### 6.1 測試類型概述
- **單元測試**：測試獨立功能模塊
- **整合測試**：測試模塊間的交互
- **API 測試**：測試 RESTful 和 WebSocket 接口
- **前端元件測試**：測試 UI 元件的渲染和交互
- **端到端測試**：測試完整用戶流程

### 6.2 主要測試工具/框架
- **後端**：Pytest、pytest-asyncio
- **前端**：React Testing Library、Vitest
- **API 測試**：Postman、Swagger UI
- **端到端測試**：Playwright

### 6.3 測試資料管理
- 使用固定的測試數據集
- 測試用的資料庫遷移腳本
- 模擬外部 API 和獨立 PDF 處理服務的回應
- 使用 Docker 容器創建隔離的測試環境

## 7. 系統功能範圍 (Scope of Work - System Wide)

### 7.1 核心功能 (In Scope)
- 用戶註冊、登入和身份驗證系統
- PDF 檔案上傳、分片上傳和斷點續傳
- PDF 文本提取和句子分割
- 概念型定義(CD)和操作型定義(OD)自動識別
- 智能問答（基於用戶上傳的文檔內容）
- 聊天記錄持久化
- 詳細處理進度實時更新（WebSocket）
- 處理過程中參考句子的互動式查看功能
- PDF 檔案預覽功能（嵌入式檢視器，支援翻頁與內容查看）
- 互動式原文引用（包含出處、頁碼、句子內容，支援點擊查看）
- 用戶檔案管理（列表、刪除）
- API 文檔自動生成
- 支援中文輸入法下的快捷鍵功能

### 7.2 排除範圍 (Out of Scope - Initial Version)
- 用戶權限管理和角色系統
- 多語言支持（初期僅支援繁體中文）
- 檔案版本控制
- 團隊協作功能
- 管理後台
- 離線功能
- 除 PDF 外的其他檔案格式支援
- 檔案加密和解密
- 跨裝置同步

## 8. 待釐清問題 (Open Questions - System Wide)

- **併發處理能力**: 系統設計目標為同時支援 50 個並發用戶。透過 Nginx 負載均衡、服務實例複製、資料庫讀寫分離和快取策略，系統可以擴展至支援 100+ 並發用戶。監控工具將持續追蹤系統負載，根據需要調整資源配置。
- **PDF 檔案預覽功能是否有特定的效能要求**（例如，開啟大型 PDF 的載入時間）？
- **斷點續傳的狀態資訊需要保存多久**？如果使用者中斷後隔很久才回來，是否還能續傳？
- **高可用性要求**: 系統是否需要實現跨區域備份和災難恢復策略？需要確定可接受的恢復時間目標(RTO)和恢復點目標(RPO)。

## 9. 交付成果 (Deliverables - System Wide)

- 完整源代碼，按照指定的資料夾結構組織
- Docker Compose 配置文件，能一鍵啟動整個系統
- 自動生成的 OpenAPI 文檔
- 系統部署指南和使用說明
- 基本單元測試和整合測試集

## 10. 需求摘要 (Requirements Summary)

以下是系統實現的五個核心需求摘要：

### 10.1 Docker 容器化部署

系統完全基於 Docker 容器化架構建置，具體實現包括：
- 所有服務組件（前端、後端、PDF處理、資料庫等）均通過 Docker 容器部署
- 使用 Docker Compose 編排多個容器，確保服務間的協同工作
- 採用 Docker 命名卷保存持久數據（PostgreSQL、MinIO、Redis等）
- 實現容器健康檢查與自動重啟策略
- 環境變量和敏感信息通過 Docker Secrets 或環境配置安全注入

### 10.2 檔案預覽功能

系統提供完整的 PDF 檔案預覽功能：
- 使用者可直接在網頁中瀏覽已上傳的 PDF 文件
- 支援翻頁、縮放、頁面導航等基本操作
- 提供頁面縮略圖側邊欄，便於快速瀏覽和跳轉
- 支援鍵盤快捷鍵和觸控設備手勢操作
- 實現響應式設計，適配不同設備的屏幕大小

### 10.3 引用句子在 PDF 中的查看

系統支援查看處理步驟中參照的句子所在的 PDF 位置：
- 在聊天回答中點擊引用句子可直接跳轉至對應 PDF 頁面
- 在目標頁面中高亮顯示被引用的句子
- 提供查看句子上下文的功能
- 通過 PDF 預覽模態框實現不離開當前頁面的交互體驗
- 支援直接從進度顯示區域查看正在處理的句子對應位置

### 10.4 斷點續傳超時機制

系統對檔案上傳實現了完善的斷點續傳與超時機制：
- 上傳大檔案時自動進行分片上傳
- 支援在網絡中斷後從斷點處續傳
- 設置10分鐘上傳超時限制，超過則視為上傳失敗
- 通過資料庫時間戳追踪上傳開始和完成時間
- 前端顯示上傳剩餘時間，並在接近超時時提示用戶
- 後端定期檢查並清理超時的未完成上傳

### 10.5 檔案刪除與資源清理

系統實現完整的檔案刪除流程，確保同時清理相關資源：
- 點擊刪除按鈕時顯示確認對話框，清晰說明刪除範圍
- 確認後同時刪除 PostgreSQL 資料庫中的檔案記錄
- 級聯刪除資料庫中的相關句子記錄和引用記錄
- 同步刪除 MinIO 對象存儲中的 PDF 檔案
- 使用資料庫事務確保刪除操作的原子性
- 實現刪除日誌記錄與失敗重試機制 