# Backlog: DB-02 - 建立對話歷史紀錄表格

- **Epic:** 會員系統與多工作區功能導入
- **狀態:** To Do
- **優先級:** High
- **估算 (Story Points):** 2

---

### 使用者故事 (User Story)

**身為** 一位使用者，
**我想要** 我在一個工作區內的對話能夠被安全地保存下來，
**以便** 我可以隨時回來檢視、接續先前的討論，並確保我的對話內容不會與其他工作區混淆。

---

### 驗收標準 (Acceptance Criteria)

1.  **`chat_histories` 資料表已成功建立：**
    -   [ ] 包含 `id` (PK), `workspace_id` (FK), `role`, `content`, `created_at`, `metadata` (JSONB) 等欄位。
    -   [ ] 欄位資料類型與約束符合設計規格。
    -   [ ] `role` 欄位應有約束，僅能為 'user' 或 'assistant'。

2.  **關聯已正確設定：**
    -   [ ] `chat_histories.workspace_id` 欄位有外鍵 (Foreign Key) 約束，指向 `workspaces.id`。
    -   [ ] 此外鍵設定了 `ON DELETE CASCADE`，確保當工作區被刪除時，其內部的所有對話紀錄也會被一併清除。

3.  **後端模型已建立：**
    -   [ ] 在 `backend/models/` 路徑下，已建立對應的 SQLAlchemy 模型 `ChatHistory`。
    -   [ ] 模型定義與資料庫表格結構完全一致。

---

### 技術筆記 (Technical Notes)

-   `content` 欄位應使用 `TEXT` 類型以容納較長的對話內容。
-   `metadata` 欄位可用於未來擴充，例如儲存對話引用的來源句子 ID 列表。
-   這是一個獨立的新增功能，依賴於 `DB-01` 的完成。 