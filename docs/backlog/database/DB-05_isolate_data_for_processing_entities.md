# Backlog: DB-05 - 隔離背景處理相關實體

- **Epic:** 會員系統與多工作區功能導入
- **狀態:** To Do
- **優先級:** Medium
- **估算 (Story Points):** 5

---

### 使用者故事 (User Story)

**身為** 一位後端開發者，
**我想要** 所有的背景處理任務、佇列項目、錯誤紀錄和進度事件都能夠與其來源的工作區進行關聯，
**以便** 我能夠在系統出現問題時，快速地篩選、定位到特定工作區的處理流程，從而進行有效的監控和除錯。

---

### 驗收標準 (Acceptance Criteria)

1.  **`processing_queue` 表格已更新：**
    -   [ ] 已新增 `workspace_id` 欄位 (FK to `workspaces.id`, `ON DELETE CASCADE`, `NOT NULL`)。

2.  **`processing_tasks` 表格已更新：**
    -   [ ] 已新增 `workspace_id` 欄位 (FK to `workspaces.id`, `ON DELETE CASCADE`, `NOT NULL`)。
    -   [ ] 對於現存的 `user_id` (VARCHAR) 欄位，已完成評估並制定處理計畫（例如：標記為棄用，或在後續任務中移除）。

3.  **`processing_errors` 表格已更新：**
    -   [ ] 已新增 `workspace_id` 欄位 (FK to `workspaces.id`, `ON DELETE CASCADE`, `NOT NULL`)。

4.  **`processing_events` 表格已更新：**
    -   [ ] 已新增 `workspace_id` 欄位 (FK to `workspaces.id`, `ON DELETE CASCADE`, `NOT NULL`)。

5.  **後端模型已更新：**
    -   [ ] 所有對應的 SQLAlchemy 模型均已更新，加入了 `workspace_id` 屬性。

---

### 技術筆記 (Technical Notes)

-   雖然這些表格的查詢頻率可能不如核心實體高，但加入 `workspace_id` 對於維護一個清晰、可追溯的非同步處理系統至關重要。
-   `processing_tasks` 中的舊 `user_id` 欄位需要特別注意，應避免在未來的新邏輯中繼續使用它，逐步過渡到以 `workspace` 為中心的架構。
-   依賴於 `DB-01` 的完成。 