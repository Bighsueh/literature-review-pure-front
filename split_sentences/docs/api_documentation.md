# PDF 句子分割 API 文檔

這個 API 服務提供了從 PDF 文件中提取文本並分割成句子的功能，使用了 PyMuPDF 進行文本提取和 spaCy 進行句子分割，並提供了頁碼追蹤功能。

## 目錄

1. [安裝和設置](#安裝和設置)
2. [API 端點](#api-端點)
3. [WebSocket 接口](#websocket-接口)
4. [響應格式](#響應格式)
5. [錯誤處理](#錯誤處理)
6. [Docker 部署](#docker-部署)

## 安裝和設置

### 本地運行

1. 安裝依賴:

```bash
pip install -r requirements.txt
```

2. 下載 spaCy 中文模型:

```bash
python -m spacy download zh_core_web_sm
```

3. 運行應用:

```bash
uvicorn app.main:app --reload
```

### Docker 運行

使用 Docker Compose:

```bash
docker-compose up -d
```

## API 端點

### 健康檢查

```
GET /health
```

檢查 API 服務是否正常運行。

**回應**:

```json
{
  "status": "healthy"
}
```

### 處理 PDF

```
POST /api/process-pdf
```

上傳 PDF 文件並提取文本，然後分割成句子，同時提供每個句子所在的頁碼信息。

**參數**:

- `file`: PDF 文件（multipart/form-data）

**回應**:

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

## WebSocket 接口

### 處理 PDF 及進度跟蹤

```
WebSocket /ws/process-pdf/{client_id}
```

通過 WebSocket 連接上傳 PDF 文件並接收處理進度。

**參數**:

- `client_id`: 客戶端唯一標識符

**連接流程**:

1. 建立 WebSocket 連接，提供唯一的 `client_id`
2. 發送 PDF 文件二進制數據
3. 接收處理進度更新
4. 接收最終處理結果

**進度更新格式**:

```json
{
  "status": "processing",
  "message": "正在處理第 1/10 頁",
  "progress": 0.15
}
```

**最終結果格式**:

```json
{
  "status": "completed",
  "progress": 1.0,
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

**錯誤格式**:

```json
{
  "status": "error",
  "error": "處理 PDF 時發生錯誤: 文件格式不支持"
}
```

## 響應格式

### 成功回應

帶頁碼的句子列表：

```json
{
  "sentences": [
    {
      "sentence": "句子1",
      "page": 1
    },
    {
      "sentence": "句子2",
      "page": 1
    },
    {
      "sentence": "句子3",
      "page": 2
    }
  ]
}
```

### 錯誤回應

```json
{
  "error": "錯誤信息"
}
```

## 錯誤處理

| 狀態碼 | 說明 |
|--------|------|
| 200    | 請求成功 |
| 400    | 請求錯誤，例如缺少文件或文件格式錯誤 |
| 500    | 伺服器內部錯誤 |

## 句子處理優化

本 API 提供以下優化的句子切分功能：

1. **精確的句子分割**：使用 spaCy 配合自定義分割邏輯，確保準確地分割每個句子。
2. **過濾非正文內容**：自動移除 PDF 中的標題、頁眉、頁腳、列表標號等非敘述性內容。
3. **列表處理**：自動清理列表項前的標號和項目符號，保留完整的句子內容。
4. **頁碼追蹤**：為每個句子提供其在原始 PDF 中的頁碼，便於引用和追蹤。

## Docker 部署

本項目提供了完整的 Docker 支持，可以使用 Docker 或 Docker Compose 進行部署。

### 使用 Docker 運行

```bash
docker build -t pdf-sentence-splitter .
docker run -p 8000:8000 pdf-sentence-splitter
```

### 使用 Docker Compose 運行

```bash
docker-compose up -d
```

Docker Compose 配置將在 8000 端口暴露服務，並創建一個 volume 用於持久化上傳的文件。 