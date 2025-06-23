# 環境變數配置指南

本文件詳細說明 `pure_front` 專案所有可用的環境變數，並提供建議值與用途說明。請在佈署前於專案根目錄建立 `.env` 檔案，或使用 CI/CD Secrets 方式注入。

| 變數 | 必填 | 預設值 | 說明 |
|------|------|--------|------|
| `POSTGRES_HOST` | ✔ | `postgres` | PostgreSQL 容器名稱或主機位址 |
| `POSTGRES_PORT` | ✔ | `5432` | PostgreSQL 連接埠 |
| `POSTGRES_DB` | ✔ | `paper_analysis` | 資料庫名稱 |
| `POSTGRES_USER` | ✔ | `postgres` | 資料庫使用者 |
| `POSTGRES_PASSWORD` | ✔ | `password` | 資料庫密碼 |
| `GROBID_URL` | ✔ | `http://localhost:8070` | Grobid server Base URL |
| `N8N_BASE_URL` | ✔ | `http://localhost:5678` | n8n server Base URL (不包含結尾斜線) |
| `SPLIT_SENTENCES_URL` | ✔ | `http://split_sentences:8000` | Split Sentences 服務 URL，後端將 Proxy 使用 |
| `SECRET_KEY` | ✔ | *(無)* | FastAPI Session 用隨機字串，必須修改 |
| `JWT_SECRET_KEY` | ✔ | *(無)* | JWT 簽章密鑰，需自行產生 |
| `JWT_ALGORITHM` | ✖ | `HS256` | JWT 加密演算法 |
| `JWT_EXPIRE_HOURS` | ✖ | `24` | Token 有效時間 (小時) |
| `GOOGLE_CLIENT_ID` | ✖ | *(空)* | Google OAuth Client ID |
| `GOOGLE_CLIENT_SECRET` | ✖ | *(空)* | Google OAuth Client Secret |
| `GOOGLE_REDIRECT_URI` | ✖ | `http://localhost:28001/api/auth/google/callback` | Google OAuth Redirect URI |
| `FRONTEND_URL` | ✔ | `http://localhost:20080` | 前端 URL，用於 CORS 及 OAuth 轉址 |
| `ENVIRONMENT` | ✖ | `development` | `development` / `production` |
| `LOG_LEVEL` | ✖ | `INFO` | Python log level |
| `SQLALCHEMY_ECHO` | ✖ | `false` | 是否輸出 SQL 語句 |
| `BATCH_PROCESSING_SIZE` | ✖ | `10` | 背景批次處理量 |

## 前端 (Vite) 變數

| 變數 | 必填 | 預設值 | 說明 |
|------|------|--------|------|
| `VITE_API_BASE_URL` | ✔ | `http://localhost:28001/api` | 後端 API Base URL |
| `VITE_WS_BASE_URL` | ✔ | `ws://localhost:28001` | WebSocket URL |
| `VITE_SPLIT_SENTENCES_BASE_URL` | ✔ | `http://localhost:28000` | Split Sentences API URL (前端直接呼叫) |
| `VITE_API_TIMEOUT` | ✖ | `30000` | Axios 逾時(ms) |
| `VITE_DEBUG_MODE` | ✖ | `false` | 於 Console 列印除錯資訊 |
| `VITE_USE_UNIFIED_QUERY` | ✖ | `true` | 切換「整合查詢」功能 |
| `VITE_ENABLE_JWT_AUTH` | ✖ | `true` | 切換 JWT 認證 |
| `VITE_GOOGLE_OAUTH_CLIENT_ID` | ✖ | *(空)* | 前端進行 gapi 登入時使用 |

> ⚠️ 前端變數需以 `VITE_` 為前綴，否則 Vite 在建置時不會將其注入。

## 建議產生密鑰方式

```bash
# 產生 32 bytes Base64 字串
$ openssl rand -base64 32
```

## 檢查與驗證

啟動容器後，可透過以下指令確認後端是否讀取到相應變數：

```bash
docker-compose exec backend python - <<'PY'
import os, json, pprint
keys = [k for k in os.environ.keys() if k in [
    'POSTGRES_HOST','GROBID_URL','N8N_BASE_URL','SECRET_KEY']]
pprint.pprint({k: os.getenv(k) for k in keys})
PY
```

若變數未正確顯示，請確認：
1. `.env` 是否位於專案根目錄。
2. `docker-compose up` 時是否傳入 `--env-file`（若非預設位置）。 