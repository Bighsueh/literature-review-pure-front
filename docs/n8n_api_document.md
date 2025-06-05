# n8n Workflow API 文件

## 1. check od/cd

**描述：** 這個 workflow 接收一個句子，並判斷其是否為**操作型定義 (Operational Definition, OD)** 或是**概念型定義 (Conceptual Definition, CD)**。

**觸發方式：**

* **類型：** Webhook
* **HTTP 方法：** `POST`
* **路徑：** `/webhook/5fd2cefe-147a-490d-ada9-8849234c1580`

**輸入 (Request Body - `application/x-www-form-urlencoded`)：**

| 欄位名稱   | 型別     | 描述                                     | 是否必填 | 範例                                 |
| :--------- | :------- | :--------------------------------------- | :------- | :----------------------------------- |
| `sentence` | `string` | 要判斷是否為 OD 或 CD 的句子。             | 是       | `Learning is acquiring new knowledge.`       |

**輸出 (Response Body - `application/json`)：**

```json
{
  "defining_type": "string",
  "reason": "string"
}
```

| 欄位名稱        | 型別     | 描述                                           | 範例         |
| :-------------- | :------- | :--------------------------------------------- | :----------- |
| `defining_type` | `string` | 判斷結果的類型，可能為 "OD" 或 "CD"。           | `"cd"`       |
| `reason`        | `string` | 判斷的原因或說明。                               | `"This statement explains the meaning of 'learning' without describing how it is measured or observed, indicating a conceptual definition."` |

**範例呼叫：**

```bash
curl -X POST -H "Content-Type: application/x-www-form-urlencoded" \
  -d "sentence=Learning is acquiring new knowledge." \
  https://n8n.hsueh.tw/webhook/5fd2cefe-147a-490d-ada9-8849234c1580
```

**範例回應：**

```json
{
  "defining_type": "cd",
  "reason": "This statement explains the meaning of 'learning' without describing how it is measured or observed, indicating a conceptual definition."
}
```

---

## 2. query keyword extraction

**描述：** 這個 workflow 接收一個查詢語句 (query)，並萃取出其中的關鍵字 (keywords)。

**觸發方式：**

* **類型：** Webhook
* **HTTP 方法：** `POST`
* **路徑：** `/webhook/421337df-0d97-47b4-a96b-a70a6c35d416`

**輸入 (Request Body - `application/x-www-form-urlencoded`)：**

| 欄位名稱  | 型別     | 描述                     | 是否必填 | 範例                        |
| :-------- | :------- | :----------------------- | :------- | :-------------------------- |
| `query`   | `string` | 需要萃取關鍵字的查詢語句。 | 是       | `What is adaptive expertise?`    |

**輸出 (Response Body - `application/json`)：**

```json
[
  {
    "output": {
      "keywords": ["string", "string", ...]
    }
  }
]
```

| 欄位名稱   | 型別             | 描述                                       | 範例                                         |
| :--------- | :--------------- | :----------------------------------------- | :------------------------------------------- |
| `output`   | `object`         | 包含關鍵字結果的物件。                       | `{"keywords": ["expertise", "adaptive expertise"]}` |
| `keywords` | `array` of `string` | 在 `output` 物件內，包含萃取出的關鍵字列表。 | `["expertise", "adaptive expertise"]`         |

**範例呼叫：**

```bash
curl -X POST -H "Content-Type: application/x-www-form-urlencoded" \
  -d "query=What is adaptive expertise?" \
  https://n8n.hsueh.tw/webhook/421337df-0d97-47b4-a96b-a70a6c35d416
```

**範例回應：**

```json
[
  {
    "output": {
      "keywords": ["expertise", "adaptive expertise"]
    }
  }
]
```

---

## 3. query intent classification (**新增**)

**描述：** 這個 workflow 接收一個查詢語句，並判斷其查詢意圖，決定是否為定義相關查詢。

**觸發方式：**

* **類型：** Webhook  
* **HTTP 方法：** `POST`
* **路徑：** `/webhook/query-intent-classification` (**待建立**)

**輸入 (Request Body - `application/x-www-form-urlencoded`)：**

| 欄位名稱  | 型別     | 描述                     | 是否必填 | 範例                        |
| :-------- | :------- | :----------------------- | :------- | :-------------------------- |
| `query`   | `string` | 需要分類意圖的查詢語句。   | 是       | `What is adaptive expertise?` or `How to measure learning outcomes?`    |

**輸出 (Response Body - `application/json`)：**

```json
{
  "intent_type": "string",
  "is_definition_related": "boolean",
  "confidence": "number",
  "suggested_keywords": ["string", "string", ...]
}
```

| 欄位名稱              | 型別             | 描述                                       | 範例                                         |
| :-------------------- | :--------------- | :----------------------------------------- | :------------------------------------------- |
| `intent_type`         | `string`         | 查詢意圖類型                               | `"definition"`, `"measurement"`, `"comparison"`, `"importance"` |
| `is_definition_related` | `boolean`        | 是否為定義相關查詢                          | `true` or `false` |
| `confidence`          | `number`         | 分類信心度 (0-1)                           | `0.85` |
| `suggested_keywords`  | `array` of `string` | 建議關鍵詞                                 | `["expertise", "adaptive"]` |

**範例呼叫：**

```bash
curl -X POST -H "Content-Type: application/x-www-form-urlencoded" \
  -d "query=What is adaptive expertise?" \
  https://n8n.hsueh.tw/webhook/query-intent-classification
```

**範例回應：**

```json
{
  "intent_type": "definition",
  "is_definition_related": true,
  "confidence": 0.92,
  "suggested_keywords": ["expertise", "adaptive", "adaptive expertise"]
}
```

---

## 4. section suggestion (**新增**)

**描述：** 這個 workflow 接收非定義相關的查詢，並建議應該搜尋哪些論文章節來找到答案。

**觸發方式：**

* **類型：** Webhook
* **HTTP 方法：** `POST`  
* **路徑：** `/webhook/section-suggestion` (**待建立**)

**輸入 (Request Body - `application/x-www-form-urlencoded`)：**

| 欄位名稱  | 型別     | 描述                     | 是否必填 | 範例                        |
| :-------- | :------- | :----------------------- | :------- | :-------------------------- |
| `query`   | `string` | 非定義相關的查詢語句。     | 是       | `How to measure learning effectiveness?`    |

**輸出 (Response Body - `application/json`)：**

```json
{
  "suggested_sections": ["string", "string", ...],
  "reasoning": "string"
}
```

| 欄位名稱              | 型別             | 描述                                       | 範例                                         |
| :-------------------- | :--------------- | :----------------------------------------- | :------------------------------------------- |
| `suggested_sections`  | `array` of `string` | 建議搜尋的章節列表                         | `["method", "results", "discussion"]` |
| `reasoning`           | `string`         | 建議理由                                   | `"Measurement methods are typically described in methodology sections"` |

**範例呼叫：**

```bash
curl -X POST -H "Content-Type: application/x-www-form-urlencoded" \
  -d "query=How to measure learning effectiveness?" \
  https://n8n.hsueh.tw/webhook/section-suggestion
```

**範例回應：**

```json
{
  "suggested_sections": ["method", "results", "discussion"],
  "reasoning": "Measurement methods and their effectiveness are typically described in methodology, results, and discussion sections."
}
```

---

## 5. enhanced_organize_via_prompt_template (**修改版**)

**描述：** 這個 workflow 是原有 organize_via_prompt_template 的增強版本，支援多檔案處理並包含來源引用資訊。

**觸發方式：**

* **類型：** Webhook
* **HTTP 方法：** `POST`
* **路徑：** `/webhook/enhanced-organize-response` (**待建立**)

**輸入 (Request Body - `application/json`)：**

```json
{
  "query": "string",
  "papers": [
    {
      "file_name": "string",
      "operational_definitions": [
        {
          "sentence": "string",
          "section": "string",
          "page_num": "number"
        }
      ],
      "conceptual_definitions": [
        {
          "sentence": "string", 
          "section": "string",
          "page_num": "number"
        }
      ]
    }
  ]
}
```

| 欄位名稱              | 型別             | 描述                                       | 是否必填 | 範例                                         |
| :-------------------- | :--------------- | :----------------------------------------- | :------- | :------------------------------------------- |
| `query`               | `string`         | 使用者的查詢語句                            | 是       | `"Compare the definitions of adaptive expertise"` |
| `papers`              | `array`          | 論文列表                                   | 是       | 見上方JSON結構 |
| `file_name`           | `string`         | 論文檔名                                   | 是       | `"smith2023.pdf"` |
| `operational_definitions` | `array`      | 操作型定義句子列表，包含來源資訊             | 是       | 見上方JSON結構 |
| `conceptual_definitions`  | `array`      | 概念型定義句子列表，包含來源資訊             | 是       | 見上方JSON結構 |

**輸出 (Response Body - `application/json`)：**

```json
{
  "response": "string",
  "references": [
    {
      "id": "string",
      "file_name": "string", 
      "sentence": "string",
      "section": "string",
      "page_num": "number",
      "type": "string"
    }
  ],
  "source_summary": {
    "total_papers": "number",
    "papers_used": ["string"]
  }
}
```

| 欄位名稱        | 型別     | 描述                                   | 範例                                                        |
| :-------------- | :------- | :------------------------------------- | :---------------------------------------------------------- |
| `response`      | `string` | AI 整理後的回覆文本，包含 [[ref:id]] 標記 | `"根據文獻分析 [[ref:abc123]]，adaptive expertise的定義..."` |
| `references`    | `array`  | 引用來源列表                            | 見上方JSON結構 |
| `source_summary`| `object` | 來源摘要資訊                            | `{"total_papers": 3, "papers_used": ["paper1.pdf", "paper2.pdf"]}` |

**範例呼叫：**

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{
    "query": "Compare adaptive expertise definitions",
    "papers": [
      {
        "file_name": "smith2023.pdf",
        "operational_definitions": [
          {
            "sentence": "Adaptive expertise measured by problem-solving speed.",
            "section": "method",
            "page_num": 5
          }
        ],
        "conceptual_definitions": [
          {
            "sentence": "Adaptive expertise is flexible problem solving.",
            "section": "introduction", 
            "page_num": 2
          }
        ]
      }
    ]
  }' \
  https://n8n.hsueh.tw/webhook/enhanced-organize-response
```

---

## 6. multi_paper_content_analysis (**新增**)

**描述：** 這個 workflow 處理非定義相關查詢的多檔案內容整合，根據建議章節的內容產生回答。

**觸發方式：**

* **類型：** Webhook
* **HTTP 方法：** `POST`
* **路徑：** `/webhook/multi-paper-content-analysis` (**待建立**)

**輸入 (Request Body - `application/json`)：**

```json
{
  "query": "string",
  "papers": [
    {
      "file_name": "string",
      "sections": [
        {
          "section_type": "string",
          "content": "string",
          "page_num": "number"
        }
      ]
    }
  ]
}
```

**輸出 (Response Body - `application/json`)：**

```json
{
  "response": "string",
  "references": [
    {
      "id": "string",
      "file_name": "string",
      "section_type": "string", 
      "content_excerpt": "string",
      "page_num": "number"
    }
  ],
  "source_summary": {
    "total_papers": "number",
    "sections_analyzed": ["string"],
    "papers_used": ["string"]
  }
}
```

**範例呼叫：**

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{
    "query": "How to measure learning effectiveness?",
    "papers": [
      {
        "file_name": "jones2023.pdf", 
        "sections": [
          {
            "section_type": "method",
            "content": "Learning effectiveness was measured using pre-post test scores...",
            "page_num": 8
          }
        ]
      }
    ]
  }' \
  https://n8n.hsueh.tw/webhook/multi-paper-content-analysis
```

---

## 原有API保持不變

**organize\_via\_prompt\_template** 原有API保持不變，以確保向後相容性。新系統將使用增強版本 `enhanced_organize_via_prompt_template`。

---

## 注意事項

1. **處理時間**：新的多檔案API需要更長處理時間，建議設置至少 240 秒超時時間
2. **引用格式**：回應中的 `[[ref:id]]` 標記用於前端顯示引用按鈕
3. **錯誤處理**：所有API都應包含適當的錯誤處理和重試機制
4. **快取考量**：相同輸入的API調用結果應考慮快取，以提升效能
5. **批次處理**：建議通過FastAPI後端管理API調用，避免同時過多請求

---

