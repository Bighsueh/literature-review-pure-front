# Backlog: DB-04 - 隔離核心資料實體

- **Epic:** 會員系統與多工作區功能導入
- **狀態:** To Do
- **優先級:** High
- **估算 (Story Points):** 5

---

### 使用者故事 (User Story)

**身為** 一位系統架構師，
**我想要** 將章節 (`sections`)、句子 (`sentences`) 和檔案選取 (`selections`) 等核心資料實體直接與工作區關聯，
**以便** 確保資料的完整性，避免跨工作區的資料查詢，並提升按工作區篩選資料時的查詢效能。

---

### 驗收標準 (Acceptance Criteria)

1.  **`paper_sections` 表格已更新：**
    -   [ ] 已新增 `workspace_id` 欄位 (FK to `workspaces.id`, `ON DELETE CASCADE`, `NOT NULL`)。

2.  **`sentences` 表格已更新：**
    -   [ ] 已新增 `workspace_id` 欄位 (FK to `workspaces.id`, `ON DELETE CASCADE`, `NOT NULL`)。

3.  **`paper_selections` 表格已重構：**
    -   [ ] 已新增 `workspace_id` 欄位 (FK to `workspaces.id`, `ON DELETE CASCADE`, `NOT NULL`)。
    -   [ ] 原有的 `paper_id` 欄位上的 `UNIQUE` 約束已被移除。
    -   [ ] 已建立一個新的複合唯一性約束在 `(workspace_id, paper_id)` 上，以允許多個工作區選取同一份檔案。

4.  **後端模型已更新：**
    -   [ ] 所有對應的 SQLAlchemy 模型 (`PaperSection`, `Sentence`, `PaperSelection`) 都已更新，加入了 `workspace_id` 屬性與相應的 ORM 關聯。

---

### 技術筆記 (Technical Notes)

-   這是一次較大規模的「反正規化」優化。雖然增加了儲存冗餘，但可以極大地簡化後續的查詢邏輯，避免大量的 `JOIN` 操作。
-   `paper_selections` 的重構是本次改造的關鍵，使其從一個全域狀態表轉變為真正的工作區級別的功能表。
-   依賴於 `DB-01` 和 `DB-03` 的完成。 