# Backlog: DB-03 - 將檔案 (papers) 與工作區關聯

- **Epic:** 會員系統與多工作區功能導入
- **狀態:** To Do
- **優先級:** Highest
- **估算 (Story Points):** 3

---

### 使用者故事 (User Story)

**身為** 一位使用者，
**我想要** 我上傳的檔案只出現在我當前的工作區內，
**以便** 保護我的資料隱私，並讓我能針對不同專案管理不同的檔案集合。

---

### 驗收標準 (Acceptance Criteria)

1.  **`papers` 資料表已更新：**
    -   [ ] `papers` 表格中已新增一個 `workspace_id` 欄位。
    -   [ ] `workspace_id` 欄位為 `NOT NULL`，且有外鍵約束指向 `workspaces.id`。
    -   [ ] 此外鍵設定了 `ON DELETE CASCADE`。

2.  **唯一性約束已調整：**
    -   [ ] 原有的 `file_hash` 欄位上的 `UNIQUE` 約束已被移除。
    -   [ ] 已建立一個新的複合唯一性約束 (composite unique constraint) 在 `(workspace_id, file_hash)` 上，以允許多個工作區上傳內容相同的檔案。

3.  **後端模型已更新：**
    -   [ ] `backend/models/paper.py` 中的 `Paper` 模型已更新，加入了 `workspace_id` 屬性以及與 `Workspace` 模型的關聯。

---

### 技術筆記 (Technical Notes)

-   修改唯一性約束是此任務的關鍵，需要 Alembic 腳本正確地先 `drop_constraint` 再 `create_constraint`。
-   此變更會影響到檔案上傳、查詢檔案列表等核心功能的後端邏輯，後續階段需要調整相關 API。
-   依賴於 `DB-01` 的完成。 