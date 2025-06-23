# Backlog: BE-02 - 建立工作區管理 (CRUD) API

- **Epic:** 後端 API 改造
- **狀態:** To Do
- **優先級:** High
- **估算 (Story Points):** 5

---

### 使用者故事 (User Story)

**身為** 一位已登入的使用者，
**我想要** 能夠建立、檢視、及刪除我自己的「對話工作區 (Notebooks)」，
**以便** 我可以組織管理我不同專案或研究主題的資料。

---

### 驗收標準 (Acceptance Criteria)

1.  **建立工作區 API (`POST /api/workspaces`) 已實現：**
    -   [ ] 此端點需要身份驗證 (依賴 `get_current_user`)。
    -   [ ] 接受一個包含 `name` 的請求 Body。
    -   [ ] `name` 必須在使用者範圍內唯一，若重複返回 `409 Conflict`。
    -   [ ] 成功在 `workspaces` 資料表中建立一筆新紀錄，其 `user_id` 關聯到當前登入的使用者。
    -   [ ] 返回新建工作區的完整資訊，狀態碼為 `201 Created`。

2.  **獲取工作區列表 API (`GET /api/workspaces`) 已實現：**
    -   [ ] 此端點需要身份驗證。
    -   [ ] 返回一個屬於**當前登入使用者**的工作區列表。
    -   [ ] 不應返回其他使用者的工作區。如果使用者沒有任何工作區，返回空列表 `[]`。

3.  **刪除工作區 API (`DELETE /api/workspaces/{workspace_id}`) 已實現：**
    -   [ ] 此端點需要身份驗證。
    -   [ ] 在執行刪除前，必須驗證該 `workspace_id` 屬於當前登入的使用者。若不屬於，返回 `403 Forbidden`。
    -   [ ] 成功刪除後，返回 `204 No Content`。
    -   [ ] 由於資料庫設定了 `ON DELETE CASCADE`，與此工作區關聯的所有資料（檔案、對話等）應被一併自動刪除。
    -   [ ] 建議採用「軟刪除」欄位 `deleted_at`，並以背景排程清理硬刪除。
    -   [ ] // FE NOTE: 新增 `deleted` 與 `name` 唯一性相關錯誤碼 (409) ，請前端顯示對應提示。

4.  **服務層邏輯已分離：**
    -   [ ] 相關的資料庫操作邏輯被封裝在 `backend/services/db_service.py` 或新建的 `workspace_service.py` 中，而不是直接寫在 API 路由函式裡。

---

### 技術筆記 (Technical Notes)

-   需要為工作區建立 Pydantic Schema (e.g., `WorkspaceCreate`, `WorkspaceOut`)。
-   `DELETE` 操作的授權檢查是此任務的關鍵，必須嚴格執行，防止使用者誤刪他人資料。
-   -   建議採用「軟刪除」欄位 `deleted_at`，並以背景排程清理硬刪除。
-   -   // FE NOTE: 新增 `deleted` 與 `name` 唯一性相關錯誤碼 (409) ，請前端顯示對應提示。
-   此任務依賴於 `