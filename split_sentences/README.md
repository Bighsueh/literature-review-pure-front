# PDF 句子分割 API

這是一個基於 FastAPI 的 API 服務，用於從 PDF 文件中提取文本並分割成句子。該服務使用 Nougat 進行 PDF 文本提取（特別適合學術論文）和 spaCy 進行句子分割。

## 特點

- 支持通過 RESTful API 上傳 PDF 文件
- 支持 WebSocket 連接，提供實時處理進度
- 使用 Nougat 進行高品質 PDF 文本提取
- 使用 spaCy 進行準確的句子分割
- 完整的 Docker 和 Docker Compose 支持
- 提供 Swagger UI 和詳細的 API 文檔

## 快速開始

### 使用 Docker Compose（推薦）

1. 確保已安裝 Docker 和 Docker Compose
2. 克隆此存儲庫
3. 啟動服務:

```bash
docker-compose up -d
```

4. 訪問 API 文檔: http://localhost:8000/docs

### 本地安裝

1. 確保已安裝 Python 3.8 或更高版本
2. 克隆此存儲庫
3. 安裝依賴:

```bash
pip install -r requirements.txt
```

4. 下載 spaCy 模型:

```bash
python -m spacy download zh_core_web_sm
```

5. 運行應用:

```bash
uvicorn app.main:app --reload
```

6. 訪問 API 文檔: http://localhost:8000/docs

## API 使用

### 處理 PDF 文件

```bash
curl -X 'POST' \
  'http://localhost:8000/api/process-pdf' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@your_document.pdf'
```

### WebSocket 連接

使用支持 WebSocket 的客戶端（如 JavaScript、Python 等）連接 `ws://localhost:8000/ws/process-pdf`。

## 詳細文檔

更多詳細信息，請參見:

- API 文檔: `/docs/api_documentation.md`
- Swagger UI: `http://localhost:8000/docs`

## 系統需求

- Python 3.8+
- 至少 4GB RAM（因為 Nougat 模型需要較多內存）
- 如果使用 GPU，需要支持 CUDA 的 GPU（可選，但能顯著提高處理速度）

## 許可證

MIT 