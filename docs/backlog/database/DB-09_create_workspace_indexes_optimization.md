# Backlog: DB-09 - 建立工作區相關索引優化策略

- **Epic:** 會員系統與多工作區功能導入
- **狀態:** To Do
- **優先級:** High
- **估算 (Story Points):** 3

---

### 使用者故事 (User Story)

**身為** 一位後端效能工程師，
**我想要** 確保所有新增的 `workspace_id` 欄位都有適當的資料庫索引，
**以便** 系統在生產環境中進行按工作區查詢時，能夠維持高效能，避免全表掃描 (Full Table Scan) 導致的效能問題。

---

### 驗收標準 (Acceptance Criteria)

1.  **核心表格索引已建立：**
    -   [ ] `papers` 表已建立 `workspace_id` 索引。
    -   [ ] `sentences` 表已建立 `workspace_id` 索引。
    -   [ ] `paper_sections` 表已建立 `workspace_id` 索引。
    -   [ ] `paper_selections` 表已建立 `(workspace_id, paper_id)` 複合索引。

2.  **對話相關索引已建立：**
    -   [ ] `chat_histories` 表已建立 `(workspace_id, created_at)` 複合索引，支援時間序列查詢。

3.  **處理任務相關索引已建立：**
    -   [ ] `processing_queue` 表已建立 `(workspace_id, status)` 複合索引。
    -   [ ] `processing_tasks` 表已建立 `workspace_id` 索引。

4.  **效能驗證通過：**
    -   [ ] 透過 Docker 測試環境，驗證所有按工作區查詢的 SQL 都使用索引（非 Seq Scan）。
    -   [ ] 查詢執行計畫 (EXPLAIN) 顯示合理的成本估算。

---

### 技術筆記 (Technical Notes)

-   所有索引的建立應在 Alembic 遷移腳本中完成，確保部署的一致性。
-   索引建立可能需要相當時間，在大型表上尤其如此。建議使用 `CONCURRENTLY` 選項（如果 PostgreSQL 支援）。
-   透過 `docker logs` 監控索引建立進度，確保不會導致長時間的資料庫鎖定。
-   依賴於 `DB-01` 到 `DB-05` 的表格結構變更。 