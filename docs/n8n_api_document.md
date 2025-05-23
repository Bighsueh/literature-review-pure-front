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

## 3. organize\_via\_prompt\_template

**描述：** 這個 workflow 接收操作型定義 (Operational Definition) 和概念型定義 (Conceptual Definition) 的列表，以及一個使用者查詢 (query)，透過 AI 整理後返回一個回覆。

**觸發方式：**

* **類型：** Webhook
* **HTTP 方法：** `POST`
* **路徑：** `/webhook/1394997a-36ab-46eb-9247-8b987eca91fc`

**輸入 (Request Body - `application/json`)：**

```json
[
  {
    "operational definition": ["string", "string", ...],
    "conceptual definition": ["string", "string", ...],
    "query": "string"
  }
]
```

| 欄位名稱                | 型別                 | 描述                                                                 | 是否必填 | 範例                                                                 |
| :---------------------- | :------------------- | :------------------------------------------------------------------- | :------- | :------------------------------------------------------------------- |
| `operational definition` | `array` of `string`  | 包含操作型定義句子的列表。                                             | 是       | `["Measure the length using a ruler.", "Time taken to complete a task."]` |
| `conceptual definition`  | `array` of `string`  | 包含概念型定義句子的列表。                                             | 是       | `["Learning is acquiring new knowledge.", "Intelligence is the ability to understand."]` |
| `query`                 | `string`             | 使用者的查詢語句，用於引導 AI 的整理。                                | 是       | `"Summarize the key differences."`                                   |

**輸出 (Response Body - `application/json`)：**

```json
[
  {
    "output": {
      "response": "string"
    }
  }
]
```

| 欄位名稱   | 型別     | 描述                                   | 範例                                                        |
| :--------- | :------- | :------------------------------------- | :---------------------------------------------------------- |
| `output`   | `object` | 包含 AI 回覆的物件。                     | `{"response": "以下為針對「學習」的概念定義..."}` |
| `response` | `string` | 在 `output` 物件內，AI 整理後的回覆文本。 | `"以下為針對「學習」的概念定義..."`     |

**範例呼叫：**

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '[{
    "operational definition": ["Measure the length using a ruler."],
    "conceptual definition": ["Learning is acquiring new knowledge."],
    "query": "Summarize the key differences."
  }]' \
  https://n8n.hsueh.tw/webhook/1394997a-36ab-46eb-9247-8b987eca91fc
```

**範例回應：**

```json
[
  {
    "output": {
      "response": "以下為針對「學習」的概念定義（概念性定義：學習是獲取新知識）與操作性定義（測量長度使用尺）的分析報告，並回應您的提問「總結主要差異」。\n\n**第一部分：概念性定義分析**\n\n*   **核心共通性：** 概念性定義的核心在於學習涉及知識的獲取。這強調了學習是一個增進理解和掌握信息的过程。\n*   **顯著差異與變化：** 由於概念性定義本身具有廣泛性，不同學者對"知識"的定義可能不同，因此學習的定義也會有所差異。例如，有些定義可能強調知識的應用，有些則更注重知識的儲存。\n*   **潛在歧義或衝突：** "知識"本身是一個複雜的概念，其定義可能涉及真理、信念、技能等多個方面。這可能導致對學習的理解存在歧義。\n\n**第二部分：操作性定義分析**\n\n*   **核心共通性：** 操作性定義"測量長度使用尺" 是一個非常簡單且具體的方法，它強調了精確的測量。\n*   **顯著差異與變化：** 此操作性定義與學習的概念完全不相關。尺的測量方法適用於物理長度，而學習是一個抽象的概念。\n*   **對特異性和可複製性的評估：** 此操作性定義極其特異，但與學習的概念無關，因此無法評估其可複製性。"
    }
  }
]
```

**注意事項：** 
- 此 API 需要較長處理時間，建議在呼叫時設置較長的超時時間（至少 180 秒）
- 範例呼叫可以使用 `--max-time 180` 參數：`curl --max-time 180 -X POST...`
- 回應內容通常較長且包含格式化的 Markdown 標記（\n, *, **等），使用時需在前端進行適當的渲染
- 回應內容會根據提供的定義和查詢而有很大差異
- 回應通常包含多個部分的分析，包括概念性定義分析、操作性定義分析、關係分析等

---

