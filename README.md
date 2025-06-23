# 📚 論文分析與定義辨識平台

> **重要提醒：本系統僅支援 *Docker Compose* 部署方式，請勿嘗試以其他方式啟動。**

本專案是一個端到端的學術研究輔助平台，協助研究者自動化完成「PDF 上傳 ➜ 章節與句子切割 ➜ OD／CD／引用抽取 ➜ 智慧查詢」等流程。專案採用 *FastAPI + PostgreSQL* 作為後端核心、*React + Zustand* 作為前端，並透過 *Docker Compose* 進行一鍵化部署。

---

## 📌 目錄

1. [主要功能](#主要功能)
2. [技術棧](#技術棧)
3. [系統要求](#系統要求)
4. [前置作業──外部依賴服務](#前置作業──外部依賴服務)
5. [環境配置（.env）](#環境配置env)
6. [Docker Compose 部署指南](#docker-compose-部署指南)
7. [快速開始](#快速開始)
8. [專案結構說明](#專案結構說明)
9. [開發指南](#開發指南)
10. [故障排除](#故障排除)
11. [貢獻指南](#貢獻指南)
12. [授權資訊](#授權資訊)

---

## 主要功能

- 📄 **PDF 上傳與解析**：支援多檔同時上傳，使用 *Grobid* 進行 TEI 結構化。
- ✂️ **句子切割與標註**：內建 *Split Sentences API*，將章節內容拆成句子並預先標記頁碼、段落。
- 🤖 **OD / CD 辨識**：透過 *n8n* 觸發 LLM 工作流程，在背景批次判斷句子屬性。
- 🔎 **智慧查詢**：使用者可對已處理的論文集合提出問題，由後端串接 *n8n* 進行語義規劃與內容分析。
- 📊 **處理進度與狀態監控**：整合 `health` 端點、Prometheus 風格 metrics，快速診斷系統健康。

---

## 技術棧

| Layer | Tech | 說明 |
|-------|------|------|
| Front-End | React 18, Vite 4, TypeScript 5, TailwindCSS | SPA 介面與狀態管理 (Zustand) |
| Back-End | FastAPI, SQLAlchemy 2, Alembic | REST / WebSocket API 與資料存取層 |
| Database | PostgreSQL 15 | 永續化儲存章節、句子、工作區及任務資訊 |
| Messaging / Cache | Redis (for Split Sentences) | 臨時任務快取、佇列 |
| External Services | Grobid, n8n, LLM Provider | PDF TEI 解析、工作流程、AI 推論 |
| Container | Docker 24+, Docker Compose v2 | 一鍵多容器部署 |

---

## 系統要求

| 軟體 | 最低版本 |
|------|-----------|
| Docker | 24.0 |
| Docker Compose | v2.20 |
| `make`（⾮必需） | 任意版本，用於簡化命令 |

> 備註：所有語言執行環境（Python、Node.js）皆已封裝於映像檔中，本機無需額外安裝。

---

## 前置作業──外部依賴服務

在執行 `docker-compose up` 之前，**務必**確定以下服務已就緒：

1. **Grobid Server**  
   - 官方映像：`lfoppiano/grobid:0.8.0`  
   - 建議透過 `docker run -d -p 8070:8070 lfoppiano/grobid:0.8.0` 方式啟動。
   - 系統將透過 `GROBID_URL`（預設 `http://localhost:8070`) 呼叫 `api/processFulltextDocument` 端點。
2. **n8n Server**  
   - 官方映像：`n8nio/n8n:1.46.0`  
   - 需匯入 `docs/n8n_api_document.md` 所描述之 workflow ID。  
   - 建議以 `docker run -d -p 5678:5678 --name n8n n8nio/n8n:1.46.0` 快速啟動。
   - 系統透過 `N8N_BASE_URL` 觸發 `intelligent_section_selection`、`unified_content_analysis` 等 webhook。
3. **（選用）LLM Provider**  
   若 workflow 內包含 OpenAI / Gemini 等模型，請於 n8n 內部完成 API Key 設定。

> 🎯 完整安裝流程與最佳化建議請參考 [`docs/external_services_setup.md`](docs/external_services_setup.md)。

---

## 環境配置 (.env)

系統透過 *dotenv* 讀取環境變數，**缺少任何關鍵變數都將導致容器啟動失敗**。以下為最小可運行範例：

```dotenv
# === 資料庫 ===
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=paper_analysis
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password

# === 外部服務 ===
GROBID_URL=http://localhost:8070
N8N_BASE_URL=http://localhost:5678
SPLIT_SENTENCES_URL=http://split_sentences:8000

# === JWT / 安全 ===
SECRET_KEY=please_change_me
JWT_SECRET_KEY=another_change_me
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=24

# === Google OAuth (可選) ===
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:28001/api/auth/google/callback
FRONTEND_URL=http://localhost:20080

# === 前端 Vite 變數 ===
VITE_API_BASE_URL=http://localhost:28001/api
VITE_WS_BASE_URL=ws://localhost:28001
VITE_SPLIT_SENTENCES_BASE_URL=http://localhost:28000
```

> 🔖 各變數完整說明見 [`docs/environment_configuration.md`](docs/environment_configuration.md)。

---

## Docker Compose 部署指南

```bash
# 1️⃣ 複製專案並進入目錄
$ git clone <repository-url>
$ cd pure_front

# 2️⃣ 複製 .env 範本並調整
$ cp .env.example .env  # 若無範本，請手動建立並參考上方區段

# 3️⃣ 啟動服務
$ docker-compose pull            # 下載基礎映像（第一次建議先行）
$ docker-compose up -d           # 以背景模式啟動

# 4️⃣ 確認所有容器均為 healthy
$ docker-compose ps --services --filter "status=running"

# 5️⃣ 開啟瀏覽器
$ open http://localhost:20080     # 或您在 .env 中設定的 FRONTEND_URL
```

> 若需重新建置映像，請使用 `docker-compose build --no-cache`。

---

## 快速開始

1. 登入前端介面，上傳一份 PDF。
2. 於「進度面板」觀察 *Grobid ➜ 句子切割 ➜ OD/CD 分析* 等任務狀態。
3. 完成後，切換至「智慧查詢」分頁，輸入研究問題。
4. 系統將串接 *n8n* 工作流程，回傳帶引用的答案。

---

## 專案結構說明

```text
pure_front/
├── backend/                # FastAPI 專案（資料庫、服務、API）
├── split_sentences/        # 句子切割子服務（FastAPI）
├── src/                    # React 前端原始碼
├── docs/                   # 技術與流程文檔
├── docker-compose.yml      # 多容器協調
└── (其餘略)
```

- **backend/**  
  - `api/`：REST & WebSocket 端點  
  - `services/`：Grobid、n8n、資料庫服務封裝  
  - `core/`：設定、日誌、例外處理  
  - `models/`：SQLAlchemy ORM Model  
- **split_sentences/**  
  獨立的 PDF ➜ 句子切割服務，使用 Celery / Redis 作為背景工作。
- **src/**  
  Vite + React 原始碼，含 Zustand store 與 hooks。

---

## 開發指南

```bash
# 進入後端開發容器
$ docker-compose exec backend bash

# 執行單元測試
$ pytest -q

# 進入前端開發容器 (dev server 已 Hot-Reload)
$ docker-compose exec react sh
```

- **資料庫遷移**：`alembic revision --autogenerate -m "<message>" && alembic upgrade head`  
- **觀察指標**：`curl http://localhost:28001/api/health/metrics`

---

## 故障排除

| 現象 | 可能原因 | 解決方案 |
|------|----------|---------|
| `backend` 容器不斷重啟 | `.env` 缺少 `GROBID_URL` / `N8N_BASE_URL` | 確認環境變數並重新啟動 |
| 上傳 PDF 卡在 *processing* | Grobid server 未啟動或連線被防火牆阻擋 | `curl <GROBID_URL>/api/isalive` 檢查服務健康 |
| 智慧查詢回傳 502 | n8n webhook URL 錯誤 | 於 n8n UI 重新確認 workflow ID 及 Base URL |
| 前端畫面顯示 `Network Error` | `VITE_API_BASE_URL` 配置錯誤 | 修改 .env 並重新建置前端映像 |

更多案例請見 [`docs/troubleshooting.md`](docs/troubleshooting.md)。

---

## 貢獻指南

1. Fork 本倉庫並建立分支：`git checkout -b feat/my-feature`  
2. 提交 Commit 並確保 `pytest` 與 `eslint` 全數通過。  
3. 發送 Pull Request，並詳述變更動機與測試結果。

---

## 授權資訊

本專案採用 **MIT License** 釋出，詳細條款請參閱 [LICENSE](LICENSE)。
