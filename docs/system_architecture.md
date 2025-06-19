# 系統整體架構說明

> 本文件旨在快速讓新進開發者或研究人員了解「學術論文定義查詢助手」的 **整體運作脈絡**，並對各元件的責任、通訊協定與資料流做一覽式說明。內容係根據 `docker-compose.yml` 設定、現有流程圖文件及系統設計整理而成。

---

## 1. 高階元件與容器架構

本系統採用微服務架構，各主要元件均於 Docker 容器中運行，透過定義的網路進行通訊。

```mermaid
graph LR
    subgraph UserBrowser [使用者瀏覽器]
        Frontend[React SPA (Vite)<br>提供使用者介面<br>Port: 20080]
    end

    subgraph DockerEnvironment [Docker 容器環境]
        Frontend --> BackendAPI[後端 API (FastAPI)<br>Port: 28001]
        BackendAPI --> DB[(PostgreSQL<br>資料庫<br>Port: 25432)]
        BackendAPI --> SplitSentencesService[句子分割服務<br>(FastAPI, Spacy)<br>Port: 28000]
        BackendAPI --> Redis[(Redis<br>快取/任務佇列<br>Port: 26379)]
        BackendAPI --> N8N_APIs[N8N 工作流程 API<br>(外部 AI 服務)]
        BackendAPI --> Grobid[Grobid 服務<br>(外部文件解析)]

        classDef frontend fill:#ADD8E6,stroke:#00008B,stroke-width:2px;
        classDef backend fill:#90EE90,stroke:#006400,stroke-width:2px;
        classDef database fill:#FFDAB9,stroke:#A0522D,stroke-width:2px;
        classDef service fill:#D8BFD8,stroke:#4B0082,stroke-width:2px;
        classDef external fill:#F0E68C,stroke:#BDB76B,stroke-width:2px;

        class Frontend frontend;
        class BackendAPI backend;
        class DB database;
        class SplitSentencesService service;
        class Redis database;
        class N8N_APIs external;
        class Grobid external;
    end

    UserBrowser --> Frontend
```

**主要服務容器:**

*   **`react` (Frontend)**: 使用者介面，基於 React、TypeScript 和 Vite。運行於 Port `20080`。
*   **`backend` (Backend API)**: 核心後端服務，基於 FastAPI，負責業務邏輯協調。運行於 Port `28001`。
*   **`postgres` (Database)**: PostgreSQL 資料庫，儲存所有持久化數據。運行於 Port `25432`。
*   **`split_sentences` (句子分割服務)**: 專責處理 TEI XML 內容解析與句子分割。運行於 Port `28000`。
*   **`redis` (Cache/Queue)**: Redis 服務，供後端及其他服務使用。運行於 Port `26379`。
*   **(外部) Grobid 服務**: 透過 API 整合，將 PDF 轉換為結構化的 TEI XML。
*   **(外部) N8N 工作流程**: 透過 API 整合，提供 AI 分析能力。

---

## 2. 元件職責詳解

### 2.1. 前端 (React SPA)
*   **技術棧**: React 18, TypeScript, Vite, TailwindCSS, Zustand, React Router, React Query, Axios.
*   **主要職責**:
    *   提供使用者互動介面。
    *   處理使用者 PDF 檔案上傳請求 (包含前端驗證)。
    *   提交使用者查詢。
    *   顯示後端回傳的分析結果與引用。
    *   透過 WebSocket 或輪詢監控檔案處理進度。

### 2.2. 後端 API (FastAPI)
*   **技術棧**: Python, FastAPI, SQLAlchemy, Alembic.
*   **主要職責**:
    *   作為系統的**總指揮 (Orchestrator)**，處理來自前端的所有請求並協調後續處理流程。
    *   **協調檔案上傳與處理流程**:
        1.  接收檔案，進行伺服器端驗證，儲存暫存檔。
        2.  調用外部 **Grobid** 服務，將 PDF 解析為結構化的 TEI XML。
        3.  調用 **`split_sentences`** 服務，傳入 TEI XML，獲取分割後的句子列表。
        4.  調用 **N8N API** (`detect_od_cd`) 進行定義句 (OD/CD) 檢測。
        5.  將論文元資訊、章節、句子及分析結果存入 PostgreSQL 資料庫，並更新處理狀態。
    *   **協調使用者查詢流程**:
        *   接收查詢，準備上下文資訊 (如論文摘要)。
        *   調用 N8N API (`intelligent_section_selection`) 進行查詢規劃與範疇界定。
        *   根據規劃，從資料庫提取相關內容。
        *   調用 N8N API (`unified_content_analysis`) 進行最終分析與綜合。
        *   格式化並回傳結果給前端。
    *   管理與資料庫 (PostgreSQL) 的所有互動。

### 2.3. 資料庫 (PostgreSQL)
*   **技術棧**: PostgreSQL 15.
*   **主要職責**:
    *   持久化儲存系統核心數據，包括：
        *   論文元資訊 (`papers` 表：檔案雜湊、狀態、TEI XML 等)。
        *   論文章節資訊 (`paper_sections` 表)。
        *   提取出的句子 (`sentences` 表：文本、頁碼、OD/CD 類型、分析原因等)。

### 2.4. 句子分割服務 (`split_sentences`)
*   **技術棧**: Python, FastAPI, Spacy.
*   **主要職責**:
    *   提供 `/api/split-sentences` 端點，接收由後端傳來的 TEI XML 資料。
    *   解析 TEI XML，提取各章節的文本內容。
    *   使用 Spacy NLP 模型將文本分割成高品質的獨立句子。
    *   回傳包含句子文本、頁碼、所屬章節等結構化資訊的列表給後端 API。
    *   **註**: 此服務不直接處理 PDF 或調用 Grobid，而是消費 Grobid 的產出。

### 2.5. Redis
*   **技術棧**: Redis (Alpine).
*   **主要職責**:
    *   在 `docker-compose.yml` 中被定義，但根據目前的程式碼，其主要使用者（如 `split_sentences` 或後端）尚不明確，可能用於未來的快取或任務佇列功能。

### 2.6. N8N 工作流程 (外部 AI 服務)
*   **技術棧**: N8N (外部服務，透過 HTTP API 整合)。
*   **主要職責**: 提供 AI 驅動的分析能力，透過多個特定功能的 API 端點實現：
    *   `detect_od_cd`: (檔案處理流程中) 檢測句子是否為操作型定義 (OD) 或概念型定義 (CD)。
    *   `intelligent_section_selection`: (查詢流程中) 根據使用者查詢和論文內容，智能規劃分析的章節與焦點。
    *   `query_keyword_extraction`: (查詢流程中，`definitions` 特殊處理) 從使用者查詢中提取關鍵詞。
    *   `unified_content_analysis`: (查詢流程中) 根據提取的內容和分析焦點，生成最終的綜合性回答。

---

## 3. 核心資料流程

### 3.1. 檔案上傳與處理流程
1.  **前端**: 使用者選擇 PDF，前端進行初步驗證並上傳至後端 API (`/upload`)。
2.  **後端 API**:
    *   驗證檔案，計算雜湊值，檢查重複。
    *   若為新檔案，存入暫存區，資料庫記錄狀態為 `uploading`。
    *   觸發背景處理任務。
3.  **背景處理 (由後端 API 協調)**:
    *   **Grobid TEI XML 處理**: 後端 API 調用外部 Grobid 服務，解析 PDF 結構與內容，獲得 TEI XML。
    *   **章節與句子提取**: 後端 API 調用 `split_sentences` 服務，傳入 TEI XML，服務回傳分割好的句子列表。
    *   **資料庫儲存**: 後端 API 將章節和句子資訊存入資料庫。
    *   **OD/CD 檢測**: 後端 API 調用 N8N (`detect_od_cd`) 分析句子類型，結果更新至資料庫。
    *   完成後，更新檔案狀態為 `completed`，清理暫存檔。
4.  **前端**: 透過 WebSocket/輪詢接收進度更新，最終顯示處理完成。

詳細流程請參考：[`file_upload_flowchart.md`](./file_upload_flowchart.md)

### 3.2. 使用者查詢與分析流程
1.  **前端**: 使用者輸入查詢，發送至後端 API (`/unified-query`)。
2.  **後端 API (階段一：規劃)**:
    *   從資料庫獲取已選取論文的章節摘要。
    *   調用 N8N (`intelligent_section_selection`) 獲取執行計畫 (分析焦點、目標章節、內容提取策略)。
3.  **後端 API (內容提取)**:
    *   **特殊處理 `definitions`**: 若計畫包含 `focus_type: "definitions"`，則：
        *   調用 N8N (`query_keyword_extraction`) 提取查詢關鍵詞。
        *   從資料庫檢索相關章節的句子。
        *   使用關鍵詞進行全文本比對，篩選出 OD/CD 句子。
    *   **一般內容提取**: 根據計畫的 `focus_type` (`key_sentences` 或 `full_section`) 從資料庫提取內容。
    *   組裝 `selected_content`。
4.  **後端 API (階段二：執行與綜合)**:
    *   調用 N8N (`unified_content_analysis`)，傳入查詢、`selected_content` 和分析焦點。
    *   接收 N8N 回傳的包含引用標記的最終答案。
5.  **前端**: 接收後端結果，渲染答案和可點擊的引用。

詳細流程請參考：[`user_query_flowchart.md`](./user_query_flowchart.md)

---

## 4. 通訊協定

*   **使用者瀏覽器 <-> 前端伺服器 (Vite)**: HTTP/HTTPS.
*   **前端 (React SPA) <-> 後端 API (FastAPI)**: HTTP/HTTPS (RESTful API calls using Axios), WebSocket (for real-time progress updates).
*   **後端 API (FastAPI) <-> PostgreSQL**: TCP/IP (SQLAlchemy ORM).
*   **後端 API (FastAPI) <-> `split_sentences` 服務**: HTTP/HTTPS (內部 API call).
*   **後端 API (FastAPI) <-> Grobid 服務**: HTTP/HTTPS (外部 API call).
*   **後端 API (FastAPI) <-> N8N 工作流程**: HTTP/HTTPS (external API calls).
*   **`split_sentences` 服務 <-> Redis**: TCP/IP.
*   **Docker 容器間通訊**: 透過 Docker 自訂橋接網路 (`app-network`)。

---

## 5. 部署架構
系統採用 Docker 容器化部署，透過 `docker-compose.yml` 檔案統一定義和管理各服務容器、網路及資料卷。這確保了開發、測試與生產環境的一致性與可移植性。
