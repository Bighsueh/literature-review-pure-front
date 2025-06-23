# Backlog: FE-04 - 改造檔案列表以支援分頁與篩選

- **Epic:** 前端 UX 重構
- **狀態:** To Do
- **優先級:** High
- **估算 (Story Points):** 5

---

### 使用者故事 (User Story)

**身為** 一位擁有大量檔案的使用者，
**我想要** 檔案列表能夠分頁載入、按狀態篩選和快速搜尋，
**以便** 我能夠快速找到需要的檔案，即使工作區內有數百個檔案也不會影響載入速度。

---

### 驗收標準 (Acceptance Criteria)

1.  **分頁載入已實現：**
    -   [ ] 檔案列表默認每頁顯示 20 個檔案，支援無限滾動或分頁器導航。
    -   [ ] 呼叫 `GET /api/workspaces/{id}/files?page=1&size=20` 獲取分頁資料。
    -   [ ] 正確處理分頁元資料 (`total`, `page`, `total_pages`)，並在 UI 中顯示。

2.  **篩選與排序功能：**
    -   [ ] 提供按處理狀態篩選：全部 / 處理中 / 已完成 / 失敗。
    -   [ ] 支援按上傳時間、檔名、檔案大小排序 (升序/降序)。
    -   [ ] 實現檔案搜尋功能：可按檔名進行即時搜尋。
    -   [ ] 篩選和排序條件會反映在 URL 查詢參數中，支援書籤和分享。

3.  **效能優化已實施：**
    -   [ ] 實現虛擬滾動 (Virtual Scrolling)，大量檔案時只渲染可見的項目。
    -   [ ] 檔案縮圖使用懶載入 (Lazy Loading)，提升初始載入速度。
    -   [ ] 實現樂觀更新：檔案操作 (如刪除) 先更新 UI，再發送 API 請求。

4.  **使用者體驗改善：**
    -   [ ] 新增骨架屏 (Skeleton Loading)，改善載入體驗。
    -   [ ] 空狀態設計：當沒有檔案時，引導使用者上傳第一個檔案。
    -   [ ] 錯誤狀態處理：API 失敗時顯示重試按鈕和錯誤訊息。

---

### 技術筆記 (Technical Notes)

-   **主要修改檔案**: `components/file/FileList/FileList.tsx`, `hooks/useFileProcessor.ts`
-   **新增組件**: `components/file/FileFilters.tsx`, `components/file/VirtualFileList.tsx`
-   需要與後端 **BE-04** 和 **BE-09** 的分頁 API 對應
-   虛擬滾動可考慮使用 `react-window` 或 `@tanstack/react-virtual` 函式庫
-   依賴 **FE-03** 的新狀態管理架構來正確處理工作區範疇的檔案狀態 