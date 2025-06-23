# Backlog: DB-08 - 更新資料庫設計文件

- **Epic:** 會員系統與多工作區功能導入
- **狀態:** To Do
- **優先級:** Medium
- **估算 (Story Points):** 3

---

### 使用者故事 (User Story)

**身為** 一位初次接觸這個專案的開發者，
**我想要** 查閱一份與當前系統實現完全同步的資料庫結構文件 (Schema) 和實體關係圖 (ER Diagram)，
**以便** 我能快速地理解多工作區架構下的新資料模型，從而高效地投入開發工作，而不會被過時的資訊誤導。

---

### 驗收標準 (Acceptance Criteria)

1.  **`docs/database_schema.md` 文件已更新：**
    -   [ ] 文件中已新增 `users`, `workspaces`, 和 `chat_histories` 三張新表的完整定義。
    -   [ ] 所有被修改過的表格（如 `papers`, `sentences` 等）的定義都已更新，清楚地標示出新增的 `workspace_id` 欄位及其外鍵關係。
    -   [ ] 對於被調整過的約束（如 `papers.file_hash`），文件中有對應的說明。

2.  **`docs/database_er_diagram.md` 文件已更新：**
    -   [ ] 實體關係圖（ERD）已被重新產生或繪製，準確地反映了所有新的表格和關係。
    -   [ ] 從圖中可以清晰地看出 `users`, `workspaces` 和其他核心實體之間的層級關聯。

---

### 技術筆記 (Technical Notes)

-   此任務是確保專案長期可維護性的關鍵一步。
-   建議使用工具（如 Mermaid.js 語法）來產生 ER 圖，方便未來持續更新。
-   此任務應在所有資料庫模型與遷移腳本都穩定後執行，以確保文件內容的最終正確性。
-   依賴於 `DB-01` 至 `DB-07` 的完成。 