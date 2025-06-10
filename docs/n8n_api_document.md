# n8n Workflow API 文件

## 1. check od/cd

**描述：** 這個 workflow 接收一個句子，並判斷其是否為**操作型定義 (Operational Definition, OD)** 或是**概念型定義 (Conceptual Definition, CD)**。

**觸發方式：**

* **類型：** Webhook
* **HTTP 方法：** `POST`
* **路徑：** `/webhook/check-od-cd`

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
  https://n8n.hsueh.tw/webhook/check-od-cd
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
* **路徑：** `/webhook/keyword-extraction`

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
  https://n8n.hsueh.tw/webhook/keyword-extraction
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

## 3. intelligent section selection (**新增**)

**描述：** 這個 workflow 接收查詢語句和所有可用論文的section摘要，智能選擇相關的sections並決定分析重點。

**觸發方式：**

* **類型：** Webhook  
* **HTTP 方法：** `POST`
* **路徑：** `/webhook/intelligent-section-selection` (**待建立**)

**輸入 (Request Body - `application/json`)：**

```json
{
  "query": "string",
  "available_papers": [
    {
      "file_name": "string",
      "sections": [
        {
          "section_type": "string",
          "page_num": "number",
          "word_count": "number",
          "brief_content": "string",
          "od_count": "number",
          "cd_count": "number", 
          "total_sentences": "number"
        }
      ]
    }
  ]
}
```

| 欄位名稱           | 型別             | 描述                                       | 範例                                         |
| :----------------- | :--------------- | :----------------------------------------- | :------------------------------------------- |
| `query`            | `string`         | 使用者查詢語句                              | `"Compare adaptive expertise definitions"`    |
| `available_papers` | `array`          | 可用論文及其section摘要列表                  | 見上方JSON結構                               |

**輸出 (Response Body - `application/json`)：**

```json
{
  "selected_sections": [
    {
      "paper_name": "string",
      "section_type": "string", 
      "focus_type": "string",
      "keywords": ["string"],
      "selection_reason": "string"
    }
  ],
  "analysis_focus": "string",
  "suggested_approach": "string"
}
```

| 欄位                   | 型別         | 描述                   | 允許值／範例                                                 |
| -------------------- | ---------- | -------------------- | ------------------------------------------------------ |
| `selected_sections`  | `array`    | 被挑選用來回答查詢的 sections  | —                                                      |
|   `paper_name`       | `string`   | 檔名或論文標題              | `"smith2023.pdf"`                                      |
|   `section_type`     | `string`   | IMRaD 章節或自訂類別        | `"method"`                                             |
|   `focus_type`       | `string`   | 建議在該 section 執行的操作   | `key_sentences` · `deep_summary` · `cross_table` (可擴充) |
|   `keywords`         | `string[]` | 用於篩選的關鍵詞             | `["measurement","adaptive expertise"]`                 |
|   `selection_reason` | `string`   | 為何選此 section         | —                                                      |
| `analysis_focus`     | `string`   | **分析重點** <br>（下表七選一） | `"cross_paper"`                                        |
| `suggested_approach` | `string`   | 建議的分析方式              | `"Generate comparison table across papers"`            |

#### `analysis_focus` 允許值

| 代號                                      | 對應需求類別      | 適用情境                      |
| --------------------------------------- | ----------- | ------------------------- |
| `locate_info` (或 `retrieval`)           | A 資訊定位與檢索   | 使用者要「找到原文句／段、章節或頁碼」。      |
| `understand_content` (或 `deep_reading`) | B 內容理解與深度閱讀 | 深入解析單篇論文的定義、量測方法、研究動機…    |
| `cross_paper` (或 `integration`)         | C 跨文獻比較與整合  | 需生成跨篇比較表、整合 research gap… |
| `definitions`                           | B 細分        | 著重「概念／操作定義」的差異與演進。        |
| `methods`                               | B 細分        | 著重方法論、量測工具的比較。            |
| `results`                               | C 細分        | 著重主要發現、統計結果的差異。           |
| `comparison`                            | C 細分        | 著重理論框架或研究觀點的對照。           |

---

### 🛠 範例呼叫

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{
    "query": "Locate the original sentences that define adaptive expertise operationally",
    "available_papers": [
      {
        "file_name": "smith2023.pdf",
        "sections": [
          {
            "section_type": "introduction",
            "page_num": 2,
            "word_count": 950,
            "brief_content": "Adaptive expertise is defined as the ability to...",
            "od_count": 2,
            "cd_count": 1,
            "total_sentences": 38
          },
          {
            "section_type": "method",
            "page_num": 5,
            "word_count": 1200,
            "brief_content": "We measured adaptive expertise using a problem-solving task...",
            "od_count": 3,
            "cd_count": 0,
            "total_sentences": 45
          }
        ]
      }
    ]
  }' \
  https://n8n.hsueh.tw/webhook/intelligent-section-selection
```

### 📝 範例回應

```json
{
  "selected_sections": [
    {
      "paper_name": "smith2023.pdf",
      "section_type": "method",
      "focus_type": "key_sentences",
      "keywords": ["operational definition", "adaptive expertise"],
      "selection_reason": "Contains explicit operational definitions of adaptive expertise and related measurement descriptions"
    }
  ],
  "analysis_focus": "locate_info",
  "suggested_approach": "Return the exact sentences with page numbers and [[ref:id]] tags"
}
```

---

> **備註**
>
> * 若之後想擴充其他 analysis\_focus，只需在此文件與對應 n8n Function Node 的 `switch` 分支中補上說明即可。

## 4. unified content analysis (**新增**)

**描述：** 這個 workflow 接收查詢語句和LLM選中的section內容，進行統一的多論文內容分析，產生整合回應。

**觸發方式：**

* **類型：** Webhook
* **HTTP 方法：** `POST`
* **路徑：** `/webhook/unified-content-analysis` (**待建立**)

**輸入 (Request Body - `application/json`)：**

```json
{
  "query": "string",
  "selected_content": [
    {
      "paper_name": "string",
      "section_type": "string",
      "content_type": "string",
      "content": "object"
    }
  ],
  "analysis_focus": "string"
}
```

| 欄位名稱         | 型別     | 描述                                | 範例                                         |
| :--------------- | :------- | :---------------------------------- | :------------------------------------------- |
| `query`          | `string` | 原始查詢語句                         | `"How do different papers define adaptive expertise?"` |
| `selected_content` | `array` | LLM選中的section內容                | 見上方JSON結構                               |
| `analysis_focus` | `string` | 分析重點類型                         | `"definitions"`, `"methods"`, `"comparison"` |

**輸出 (Response Body - `application/json`)：**

```json
{
  "response": "string",
  "references": [
    {
      "id": "string",
      "paper_name": "string", 
      "section_type": "string",
      "page_num": "number",
      "content_snippet": "string"
    }
  ],
  "source_summary": {
    "total_papers": "number",
    "papers_used": ["string"],
    "sections_analyzed": ["string"],
    "analysis_type": "string"
  }
}
```

| 欄位名稱        | 型別     | 描述                                   | 範例                                                        |
| :-------------- | :------- | :------------------------------------- | :---------------------------------------------------------- |
| `response`      | `string` | AI 整理後的回覆文本，包含 [[ref:id]] 標記 | `"根據多篇文獻分析 [[ref:abc123]]，adaptive expertise的定義..."` |
| `references`    | `array`  | 引用來源列表                            | 見上方JSON結構 |
| `source_summary`| `object` | 來源摘要資訊                            | `{"total_papers": 3, "analysis_type": "definition_comparison"}` |

**範例呼叫：**

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{
    "query": "How do different papers define adaptive expertise?",
    "selected_content": [
      {
        "paper_name": "smith2023.pdf",
        "section_type": "introduction",
        "content_type": "definitions",
        "content": [
          {
            "text": "Adaptive expertise is the ability to flexibly apply knowledge.",
            "type": "CD",
            "page_num": 2
          }
        ]
      }
    ],
    "analysis_focus": "definitions"
  }' \
  https://n8n.hsueh.tw/webhook/unified-content-analysis
```

**範例回應：**

```json
{
  "response": "根據文獻分析，adaptive expertise 的定義呈現不同觀點 [[ref:smith2023_intro_2]]...",
  "references": [
    {
      "id": "smith2023_intro_2",
      "paper_name": "smith2023.pdf",
      "section_type": "introduction", 
      "page_num": 2,
      "content_snippet": "Adaptive expertise is the ability to flexibly apply knowledge."
    }
  ],
  "source_summary": {
    "total_papers": 1,
    "papers_used": ["smith2023.pdf"],
    "sections_analyzed": ["introduction"],
    "analysis_type": "definition_comparison"
  }
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

