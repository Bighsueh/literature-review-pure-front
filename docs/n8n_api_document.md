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

## 4. unified content analysis (**更新**)

**描述：**
此 workflow 接收「使用者查詢」與 **LLM 已挑選之 section 內容**，依 `analysis_focus` 執行**統一的多論文內容分析**，回傳整合後的回答、引用清單與來源統計。

> ⚡ `analysis_focus` 現支援 **八種**：`locate_info`、`understand_content`、`cross_paper`、`definitions`、`methods`、`results`、`comparison`、`other`。
>
> * 其中前三種對應 A‒C 三大核心需求（資訊定位／深度閱讀／跨文獻整合）。
> * 中間四種為較細緻的主題分析。
> * `other` 為彈性分析類別，處理非標準化或客製化需求。

---

### 🔗 Webhook 設定

| 項目          | 內容                                  |
| ----------- | ----------------------------------- |
| **HTTP 方法** | `POST`                              |
| **路徑**      | `/webhook/unified-content-analysis` |

---

### 📥 輸入（Request Body — `application/json`）

```jsonc
{
  "query": "string",
  "selected_content": [
    {
      "paper_name": "string",
      "section_type": "string",
      "content_type": "string",
      "content": {}          // 結構取決於 content_type
    }
  ],
  "analysis_focus": "string"
}
```

| 欄位                 | 型別       | 描述                          | 範例／允許值                                                                                                                          |
| ------------------ | -------- | --------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `query`            | `string` | 使用者原始查詢                     | `"Locate operational definitions of adaptive expertise"`                                                                        |
| `selected_content` | `array`  | 由前序節點選出的 section 內容         | —                                                                                                                               |
|   `paper_name`     | `string` | 檔名或論文標題                     | `"smith2023.pdf"`                                                                                                               |
|   `section_type`   | `string` | IMRaD 章節或自訂分類               | `"method"`                                                                                                                      |
|   `content_type`   | `string` | section 的資料型別<sup>＊</sup>   | `"raw_text"` · `"definitions"` · `"methods"` · `"results"` · `"key_sentences"` …                                                |
|   `content`        | `object` | 內容本體（格式依 `content_type` 而異） | 例如 definitions 會是句子陣列、raw\_text 則是全文字串                                                                                          |
| `analysis_focus`   | `string` | **分析重點**                    | `locate_info` · `understand_content` · `cross_paper` · `definitions` · `methods` · `results` · `comparison` · `other` |

> **＊content\_type 說明**
>
> * `raw_text`：整段原文 (string)
> * `definitions`／`methods`…：已按類別拆出的句子陣列
> * `key_sentences`：模型挑選的精選句 (array)
> * 可視需求擴充

---

### 📤 輸出（Response Body — `application/json`）

```jsonc
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

| 欄位                                 | 型別         | 描述                                                                                                                                                                                        | 備註                      |
| ---------------------------------- | ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------- |
| `response`                         | `string`   | **AI 統整後回覆**，含 `[[ref:id]]` 引用標記。內容格式因 `analysis_focus` 而異：<br> - `locate_info` → Bullet / quote 句子清單<br> - `understand_content` → 條列摘要<br> - `cross_paper` → 可能含 Markdown 表格<br> - `other` → 依使用者需求客製化格式 | —                       |
| `references`                       | `array`    | 依序列出所有引用來源                                                                                                                                                                                | `id` 應與 `[[ref:id]]` 對應 |
| `source_summary.total_papers`      | `number`   | 參考之論文總數                                                                                                                                                                                   | —                       |
| `source_summary.papers_used`       | `string[]` | 實際被引用的檔名                                                                                                                                                                                  | —                       |
| `source_summary.sections_analyzed` | `string[]` | 分析過的章節種類                                                                                                                                                                                  | —                       |
| `source_summary.analysis_type`     | `string`   | 內部標記：<br>`locate_info` · `deep_reading` · `cross_paper` · `definition_comparison` · `method_review` · `other_analysis` · …                                                                 | 可供前端顯示或後續紀錄             |

---

### 🛠 範例呼叫：`locate_info`（A 類需求）

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{
    "query": "Locate the original sentences that define adaptive expertise operationally",
    "selected_content": [
      {
        "paper_name": "smith2023.pdf",
        "section_type": "method",
        "content_type": "key_sentences",
        "content": [
          {
            "text": "We operationally define adaptive expertise as the capacity to...",
            "page_num": 5,
            "id": "smith2023_method_5"
          }
        ]
      }
    ],
    "analysis_focus": "locate_info"
  }' \
  https://n8n.hsueh.tw/webhook/unified-content-analysis
```

#### 可能回應

```json
{
  "response": "• We operationally define adaptive expertise as the capacity to... [[ref:smith2023_method_5]]",
  "references": [
    {
      "id": "smith2023_method_5",
      "paper_name": "smith2023.pdf",
      "section_type": "method",
      "page_num": 5,
      "content_snippet": "We operationally define adaptive expertise as the capacity to..."
    }
  ],
  "source_summary": {
    "total_papers": 1,
    "papers_used": ["smith2023.pdf"],
    "sections_analyzed": ["method"],
    "analysis_type": "locate_info"
  }
}
```

### 🛠 範例呼叫：`cross_paper`（C 類需求）

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{
    "query": "Compare measurement tools for adaptive expertise across studies",
    "selected_content": [
      {
        "paper_name": "smith2023.pdf",
        "section_type": "method",
        "content_type": "methods",
        "content": [
          { "tool": "Problem-solving task", "page_num": 5, "id": "smith2023_method_tool" }
        ]
      },
      {
        "paper_name": "lee2024.pdf",
        "section_type": "method",
        "content_type": "methods",
        "content": [
          { "tool": "Situational judgement test", "page_num": 6, "id": "lee2024_method_tool" }
        ]
      }
    ],
    "analysis_focus": "cross_paper"
  }' \
  https://n8n.hsueh.tw/webhook/unified-content-analysis
```

### 🛠 範例呼叫：`other`（彈性分析需求）

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{
    "query": "請從創新理論的角度分析這些研究的貢獻，並評估其對未來研究方向的啟示",
    "selected_content": [
      {
        "paper_name": "smith2023.pdf",
        "section_type": "discussion",
        "content_type": "raw_text",
        "content": "Our findings contribute to the theoretical understanding of adaptive expertise by demonstrating..."
      },
      {
        "paper_name": "lee2024.pdf",
        "section_type": "conclusion",
        "content_type": "key_sentences",
        "content": [
          {
            "text": "Future research should explore the intersection of adaptive expertise and technology integration.",
            "page_num": 15,
            "id": "lee2024_conclusion_15"
          }
        ]
      }
    ],
    "analysis_focus": "other"
  }' \
  https://n8n.hsueh.tw/webhook/unified-content-analysis
```

#### 可能回應

```json
{
  "response": "從創新理論的角度分析，這些研究展現了三個重要貢獻：\n\n**理論創新層面**\n這些研究透過實證方法驗證了適應性專業知識的理論架構 [[ref:smith2023_discussion]]，為既有理論提供了新的實證基礎...\n\n**方法論突破**\n研究採用了跨領域的測量工具，為後續研究提供了方法論上的創新範例...\n\n**未來研究啟示**\n如 Lee et al. (2024) 所指出，未來研究應探索適應性專業知識與技術整合的交集 [[ref:lee2024_conclusion_15]]，這為該領域開啟了新的研究方向...",
  "references": [
    {
      "id": "smith2023_discussion",
      "paper_name": "smith2023.pdf",
      "section_type": "discussion",
      "page_num": 12,
      "content_snippet": "Our findings contribute to the theoretical understanding of adaptive expertise by demonstrating..."
    },
    {
      "id": "lee2024_conclusion_15",
      "paper_name": "lee2024.pdf",
      "section_type": "conclusion",
      "page_num": 15,
      "content_snippet": "Future research should explore the intersection of adaptive expertise and technology integration."
    }
  ],
  "source_summary": {
    "total_papers": 2,
    "papers_used": ["smith2023.pdf", "lee2024.pdf"],
    "sections_analyzed": ["discussion", "conclusion"],
    "analysis_type": "other_analysis"
  }
}
```

---

> **備註**
>
> * `analysis_focus` 決定 LLM 在下游節點應用哪段 `analysisInstruction`。
> * 若未傳入合法值，系統將 fallback 至 `default` 綜合分析邏輯。
> * `other` 類別適用於需要特殊分析視角或非標準化問題的情境，系統會根據使用者查詢的特性進行彈性分析。

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