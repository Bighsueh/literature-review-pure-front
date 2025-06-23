# Backlog: BE-04 - 改造檔案管理 API 以支援工作區

- **Epic:** 後端 API 改造
- **狀態:** To Do
- **優先級:** High
- **估算 (Story Points):** 5

---

### 使用者故事 (User Story)

**身為** 一位在特定工作區內的使用者，
**我想要** 檢視、選取或刪除檔案時，所有的操作都只會影響到我目前工作區內的檔案，
**以便** 我可以安全地管理我的專案資料，而不用擔心影響到其他工作區。

---

### 驗收標準 (Acceptance Criteria)

1.  **檔案列表 API 已重構：**
    -   [ ] 原有的 `GET /api/papers` 已被修改為 `GET /api/workspaces/{workspace_id}/files`。
    -   [ ] 此端點需要授權檢查，確保使用者能存取該 `workspace_id`。
    -   [ ] `backend/services/db_service.py` 中的 `get_papers` 查詢邏輯已更新，現在會使用 `workspace_id` 作為過濾條件。
    -   [ ] 返回的檔案列表僅包含屬於指定工作區的檔案。

2.  **檔案刪除 API 已重構：**
    -   [ ] 原有的 `DELETE /api/papers/{paper_id}` 已被修改為 `DELETE /api/workspaces/{workspace_id}/files/{paper_id}`。
    -   [ ] 此端點需要授權檢查。
    -   [ ] 服務層在執行刪除前，必須額外驗證該 `paper_id` 確實屬於傳入的 `workspace_id`，防止路徑竄改攻擊。

3.  **檔案選取 API (`paper_selections`) 已重構：**
    -   [ ] 所有與 `paper_selections` 相關的 API (e.g., `POST /api/papers/select`) 都已工作區化，例如 `POST /api/workspaces/{workspace_id}/selections`。
    -   [ ] 服務層邏輯已更新，選取或取消選取檔案時，操作的是與 `workspace_id` 關聯的 `paper_selections` 記錄。

---

### 技術筆記 (Technical Notes)

-   API 變更需更新前端檔案管理元件以加入 `workspace_id` 查詢參數。
-   -   // FE NOTE: 檔案列表分頁、排序與 `processing_status` 過濾將影響前端 `FileList` 組件。
-   需要在資料庫層面建立 `(workspace_id, file_hash)` 的複合唯一索引，以避免重複上傳同一檔案。
-   本次改造的核心在於**服務層 (Service Layer)** 的查詢邏輯變更。幾乎所有 `db_service` 中的函式都需要增加 `workspace_id` 作為必要的參數。
-   對於 `DELETE` 這類具破壞性的操作，**雙重驗證** (`workspace` 歸屬權 和 `paper` 在 `workspace` 中的歸屬權) 是確保安全的最佳實踐。
-   依賴於 `BE-01` (身份驗證) 和 `BE-03` (檔案已與工作區關聯)。 