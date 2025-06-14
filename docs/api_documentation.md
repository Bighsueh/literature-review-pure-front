# API 文檔

## 概述

論文分析系統提供 RESTful API，支援論文上傳、處理狀態查詢、內容分析等功能。

## 基本資訊

- **Base URL**: `http://localhost:8000/api`
- **Content-Type**: `application/json`
- **文件上傳**: `multipart/form-data`

## 認證

目前系統不需要認證，所有 API 端點都是公開的。

## API 端點

### 1. 論文管理

#### 1.1 上傳論文

**端點**: `POST /upload/`

**描述**: 上傳 PDF 論文檔案進行分析

**請求格式**:
```http
POST /api/upload/
Content-Type: multipart/form-data

file: [PDF檔案]
```

**響應格式**:
```json
{
    "message": "File uploaded successfully",
    "paper_id": "d5e0ad48-c188-45b4-8408-9e975105f863",
    "filename": "test.pdf"
}
```

**錯誤響應**:
```json
{
    "detail": "No file uploaded"
}
```

**狀態碼**:
- `200`: 上傳成功
- `400`: 請求錯誤（無檔案、格式錯誤等）
- `500`: 伺服器錯誤

#### 1.2 獲取論文列表

**端點**: `GET /papers/`

**描述**: 獲取所有已上傳論文的列表

**請求參數**:
- `status` (可選): 篩選特定狀態的論文 (`pending`, `processing`, `completed`, `error`)
- `limit` (可選): 限制返回數量，預設 50
- `offset` (可選): 分頁偏移量，預設 0

**請求範例**:
```http
GET /api/papers/?status=completed&limit=10&offset=0
```

**響應格式**:
```json
{
    "papers": [
        {
            "id": "d5e0ad48-c188-45b4-8408-9e975105f863",
            "file_name": "test.pdf",
            "original_filename": "test.pdf",
            "processing_status": "completed",
            "file_size": 372379,
            "upload_timestamp": "2025-01-14T10:30:00Z",
            "processing_completed_at": "2025-01-14T10:35:00Z",
            "section_count": 23,
            "sentence_count": 209,
            "od_count": 15,
            "cd_count": 8
        }
    ],
    "total": 1,
    "limit": 10,
    "offset": 0
}
```

#### 1.3 獲取論文詳情

**端點**: `GET /papers/{paper_id}`

**描述**: 獲取特定論文的詳細資訊

**路徑參數**:
- `paper_id`: 論文 UUID

**響應格式**:
```json
{
    "id": "d5e0ad48-c188-45b4-8408-9e975105f863",
    "file_name": "test.pdf",
    "original_filename": "test.pdf",
    "processing_status": "completed",
    "file_size": 372379,
    "upload_timestamp": "2025-01-14T10:30:00Z",
    "processing_completed_at": "2025-01-14T10:35:00Z",
    "grobid_processed": true,
    "sentences_processed": true,
    "od_cd_processed": true,
    "tei_metadata": {
        "title": "論文標題",
        "authors": ["作者1", "作者2"],
        "abstract": "摘要內容..."
    }
}
```

#### 1.4 刪除論文

**端點**: `DELETE /papers/{paper_id}`

**描述**: 刪除指定論文及其所有相關資料

**路徑參數**:
- `paper_id`: 論文 UUID

**響應格式**:
```json
{
    "message": "Paper deleted successfully"
}
```

### 2. 章節管理

#### 2.1 獲取論文章節

**端點**: `GET /papers/{paper_id}/sections`

**描述**: 獲取論文的所有章節

**路徑參數**:
- `paper_id`: 論文 UUID

**請求參數**:
- `section_type` (可選): 篩選特定類型章節

**響應格式**:
```json
{
    "sections": [
        {
            "id": "section-uuid-1",
            "section_type": "introduction",
            "page_num": 1,
            "content": "章節內容...",
            "section_order": 1,
            "word_count": 250,
            "sentence_count": 12
        },
        {
            "id": "section-uuid-2",
            "section_type": "methodology",
            "page_num": 3,
            "content": "方法論內容...",
            "section_order": 2,
            "word_count": 450,
            "sentence_count": 23
        }
    ]
}
```

#### 2.2 獲取章節詳情

**端點**: `GET /sections/{section_id}`

**描述**: 獲取特定章節的詳細資訊

**路徑參數**:
- `section_id`: 章節 UUID

**響應格式**:
```json
{
    "id": "section-uuid-1",
    "paper_id": "d5e0ad48-c188-45b4-8408-9e975105f863",
    "section_type": "introduction",
    "page_num": 1,
    "content": "完整章節內容...",
    "section_order": 1,
    "word_count": 250,
    "tei_coordinates": "TEI座標資訊",
    "created_at": "2025-01-14T10:32:00Z"
}
```

### 3. 句子分析

#### 3.1 獲取論文句子

**端點**: `GET /papers/{paper_id}/sentences`

**描述**: 獲取論文的所有句子及其分析結果

**路徑參數**:
- `paper_id`: 論文 UUID

**請求參數**:
- `has_objective` (可選): 篩選包含目標定義的句子 (`true`, `false`)
- `has_dataset` (可選): 篩選包含資料集定義的句子 (`true`, `false`)
- `has_contribution` (可選): 篩選包含貢獻定義的句子 (`true`, `false`)
- `section_type` (可選): 篩選特定章節類型的句子
- `limit` (可選): 限制返回數量
- `offset` (可選): 分頁偏移量

**請求範例**:
```http
GET /api/papers/d5e0ad48-c188-45b4-8408-9e975105f863/sentences?has_objective=true&limit=20
```

**響應格式**:
```json
{
    "sentences": [
        {
            "id": "sentence-uuid-1",
            "content": "本研究的主要目標是開發一個新的機器學習模型...",
            "sentence_order": 5,
            "word_count": 25,
            "has_objective": true,
            "has_dataset": false,
            "has_contribution": false,
            "detection_status": "success",
            "explanation": "此句子明確描述了研究目標",
            "section_type": "introduction",
            "section_id": "section-uuid-1"
        }
    ],
    "total": 15,
    "limit": 20,
    "offset": 0
}
```

#### 3.2 搜尋句子

**端點**: `GET /sentences/search`

**描述**: 在所有論文中搜尋包含特定關鍵詞的句子

**請求參數**:
- `q`: 搜尋關鍵詞（必填）
- `paper_ids` (可選): 限制搜尋的論文 ID 列表
- `section_types` (可選): 限制搜尋的章節類型
- `has_objective` (可選): 篩選包含目標定義的句子
- `has_dataset` (可選): 篩選包含資料集定義的句子
- `has_contribution` (可選): 篩選包含貢獻定義的句子
- `limit` (可選): 限制返回數量，預設 50

**請求範例**:
```http
GET /api/sentences/search?q=machine%20learning&section_types=introduction,methodology&limit=10
```

**響應格式**:
```json
{
    "sentences": [
        {
            "id": "sentence-uuid-1",
            "content": "Machine learning algorithms have shown great promise...",
            "paper_id": "paper-uuid-1",
            "paper_filename": "ml_paper.pdf",
            "section_type": "introduction",
            "has_objective": true,
            "has_dataset": false,
            "has_contribution": false,
            "relevance_score": 0.95
        }
    ],
    "total": 25,
    "query": "machine learning",
    "limit": 10
}
```

### 4. 論文選擇

#### 4.1 選擇論文

**端點**: `POST /papers/{paper_id}/select`

**描述**: 將論文標記為已選擇，用於後續分析

**路徑參數**:
- `paper_id`: 論文 UUID

**響應格式**:
```json
{
    "message": "Paper selected successfully",
    "paper_id": "d5e0ad48-c188-45b4-8408-9e975105f863"
}
```

#### 4.2 取消選擇論文

**端點**: `DELETE /papers/{paper_id}/select`

**描述**: 取消論文的選擇狀態

**路徑參數**:
- `paper_id`: 論文 UUID

**響應格式**:
```json
{
    "message": "Paper unselected successfully",
    "paper_id": "d5e0ad48-c188-45b4-8408-9e975105f863"
}
```

#### 4.3 獲取選中論文

**端點**: `GET /papers/selected`

**描述**: 獲取所有已選擇的論文列表

**響應格式**:
```json
{
    "selected_papers": [
        {
            "id": "d5e0ad48-c188-45b4-8408-9e975105f863",
            "file_name": "test.pdf",
            "processing_status": "completed",
            "selected_at": "2025-01-14T11:00:00Z",
            "section_count": 23,
            "sentence_count": 209,
            "od_count": 15,
            "cd_count": 8
        }
    ]
}
```

### 5. 統計分析

#### 5.1 獲取系統統計

**端點**: `GET /stats/system`

**描述**: 獲取系統整體統計資訊

**響應格式**:
```json
{
    "total_papers": 50,
    "completed_papers": 45,
    "processing_papers": 3,
    "error_papers": 2,
    "total_sections": 1150,
    "total_sentences": 12500,
    "total_od_sentences": 850,
    "total_cd_sentences": 420,
    "total_contribution_sentences": 380,
    "average_processing_time": 120.5
}
```

#### 5.2 獲取論文統計

**端點**: `GET /papers/{paper_id}/stats`

**描述**: 獲取特定論文的統計資訊

**路徑參數**:
- `paper_id`: 論文 UUID

**響應格式**:
```json
{
    "paper_id": "d5e0ad48-c188-45b4-8408-9e975105f863",
    "section_count": 23,
    "sentence_count": 209,
    "word_count": 5240,
    "od_sentences": 15,
    "cd_sentences": 8,
    "contribution_sentences": 12,
    "section_breakdown": {
        "introduction": {
            "sentence_count": 45,
            "od_count": 8,
            "cd_count": 2,
            "contribution_count": 3
        },
        "methodology": {
            "sentence_count": 67,
            "od_count": 3,
            "cd_count": 4,
            "contribution_count": 5
        }
    }
}
```

### 6. 處理狀態

#### 6.1 獲取處理狀態

**端點**: `GET /papers/{paper_id}/status`

**描述**: 獲取論文的詳細處理狀態

**路徑參數**:
- `paper_id`: 論文 UUID

**響應格式**:
```json
{
    "paper_id": "d5e0ad48-c188-45b4-8408-9e975105f863",
    "processing_status": "completed",
    "grobid_processed": true,
    "sentences_processed": true,
    "od_cd_processed": true,
    "processing_stages": [
        {
            "stage": "grobid",
            "status": "completed",
            "started_at": "2025-01-14T10:30:15Z",
            "completed_at": "2025-01-14T10:31:20Z",
            "duration": 65
        },
        {
            "stage": "sentences",
            "status": "completed",
            "started_at": "2025-01-14T10:31:25Z",
            "completed_at": "2025-01-14T10:33:10Z",
            "duration": 105
        },
        {
            "stage": "od_cd",
            "status": "completed",
            "started_at": "2025-01-14T10:33:15Z",
            "completed_at": "2025-01-14T10:35:00Z",
            "duration": 105
        }
    ],
    "total_processing_time": 275,
    "error_message": null
}
```

## 錯誤處理

### 標準錯誤格式

```json
{
    "detail": "錯誤描述",
    "error_code": "ERROR_CODE",
    "timestamp": "2025-01-14T10:30:00Z"
}
```

### 常見錯誤碼

| 狀態碼 | 錯誤碼 | 描述 |
|--------|--------|------|
| 400 | INVALID_FILE_FORMAT | 不支援的檔案格式 |
| 400 | FILE_TOO_LARGE | 檔案大小超過限制 |
| 404 | PAPER_NOT_FOUND | 論文不存在 |
| 404 | SECTION_NOT_FOUND | 章節不存在 |
| 409 | PAPER_ALREADY_EXISTS | 論文已存在（基於檔案雜湊） |
| 422 | PROCESSING_IN_PROGRESS | 論文正在處理中 |
| 500 | PROCESSING_ERROR | 處理過程發生錯誤 |
| 500 | DATABASE_ERROR | 資料庫錯誤 |

## 使用範例

### Python 範例

```python
import requests
import json

# 上傳論文
def upload_paper(file_path):
    url = "http://localhost:8000/api/upload/"
    with open(file_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(url, files=files)
    return response.json()

# 獲取論文狀態
def get_paper_status(paper_id):
    url = f"http://localhost:8000/api/papers/{paper_id}/status"
    response = requests.get(url)
    return response.json()

# 搜尋句子
def search_sentences(query, limit=10):
    url = "http://localhost:8000/api/sentences/search"
    params = {'q': query, 'limit': limit}
    response = requests.get(url, params=params)
    return response.json()

# 使用範例
paper_result = upload_paper("test.pdf")
paper_id = paper_result['paper_id']

# 等待處理完成
import time
while True:
    status = get_paper_status(paper_id)
    if status['processing_status'] == 'completed':
        break
    time.sleep(5)

# 搜尋相關句子
results = search_sentences("machine learning")
print(f"找到 {results['total']} 個相關句子")
```

### JavaScript 範例

```javascript
// 上傳論文
async function uploadPaper(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch('/api/upload/', {
        method: 'POST',
        body: formData
    });
    
    return await response.json();
}

// 獲取論文列表
async function getPapers(status = null) {
    const params = new URLSearchParams();
    if (status) params.append('status', status);
    
    const response = await fetch(`/api/papers/?${params}`);
    return await response.json();
}

// 搜尋句子
async function searchSentences(query, filters = {}) {
    const params = new URLSearchParams({ q: query, ...filters });
    const response = await fetch(`/api/sentences/search?${params}`);
    return await response.json();
}
```

## 速率限制

目前系統沒有實施速率限制，但建議：
- 檔案上傳：每分鐘最多 10 個檔案
- API 查詢：每秒最多 100 個請求
- 搜尋查詢：每分鐘最多 60 個請求

## 版本資訊

- **API 版本**: v1
- **最後更新**: 2025-01-14
- **相容性**: 向後相容 