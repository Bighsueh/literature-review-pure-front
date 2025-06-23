# Backlog: BE-09 - 建立 API 效能優化與分頁機制

- **Epic:** 後端 API 改造
- **狀態:** To Do
- **優先級:** Medium
- **估算 (Story Points):** 5

---

### 使用者故事 (User Story)

**身為** 一位擁有大量檔案和對話紀錄的使用者，
**我想要** 系統能夠快速載入我的工作區內容，即使我有數百個檔案或數千條對話紀錄，
**以便** 我能夠流暢地使用系統，不會因為載入時間過長而影響工作效率。

---

### 驗收標準 (Acceptance Criteria)

1.  **分頁機制已實施：**
    -   [ ] `GET /api/workspaces/{id}/files` 支援 `page`, `size`, `sort`, `order` 查詢參數。
    -   [ ] `GET /api/workspaces/{id}/chats` 支援分頁，預設每頁載入最近 50 條對話。
    -   [ ] 所有分頁 API 返回統一的分頁元資料：`total`, `page`, `size`, `total_pages`。

2.  **排序與過濾功能：**
    -   [ ] 檔案列表支援按 `upload_timestamp`, `file_name`, `file_size` 排序。
    -   [ ] 檔案列表支援按 `processing_status` 進行過濾。
    -   [ ] 對話歷史支援按時間範圍過濾 (`start_date`, `end_date`)。

3.  **快取策略已實施：**
    -   [ ] 工作區基本資訊（名稱、建立時間等）使用 Redis 快取，TTL 為 30 分鐘。
    -   [ ] 檔案列表的第一頁結果快取 5 分鐘。
    -   [ ] 實作快取失效機制，當資料更新時自動清除相關快取。

4.  **效能監控：**
    -   [ ] 已實作 API 回應時間監控，目標：90% 的請求在 500ms 內完成。
    -   [ ] 資料庫查詢時間監控，識別慢查詢並進行優化。
    -   [ ] 已建立效能基準測試，模擬高負載情況。

---

### 技術筆記 (Technical Notes)

-   建議使用 Redis 作為快取層，需要在 `docker-compose.yml` 中添加 Redis 服務，並啟用 **AOF 持久化**，避免資料遺失。
-   分頁實作應使用資料庫層面的 `LIMIT` 和 `OFFSET`，而非應用層面的篩選；預設 `size`（每頁筆數）可由環境變數 `DEFAULT_PAGE_SIZE` 變動，預設 50。
-   -   // FE NOTE: 檔案與對話列表 API 回傳分頁元資料 (`total_pages`, `page`)，前端需依此實作無限滾動/分頁。
-   快取鍵的設計應考慮工作區隔離，例如：`workspace:{id}:files:page:{page}`。
-   效能監控可以使用 FastAPI 的 middleware 實現。
-   依賴於 `BE-04` (檔案管理) 和 `BE-05` (對話 API) 的基本功能已實現。 