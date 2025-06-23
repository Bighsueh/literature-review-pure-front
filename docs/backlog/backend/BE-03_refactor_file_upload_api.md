# Backlog: BE-03 - 改造檔案上傳 API 以支援工作區

- **Epic:** 後端 API 改造
- **狀態:** To Do
- **優先級:** High
- **估算 (Story Points):** 5

---

### 使用者故事 (User Story)

**身為** 一位在特定工作區內的使用者，
**我想要** 我上傳的檔案能夠被正確地歸類到我目前正在使用的工作區，
**以便** 這個檔案只對當前工作區可見，且不會與我其他的專案混淆。

---

### 驗收標準 (Acceptance Criteria)

1.  **API 端點已重構：**
    -   [ ] 原有的 `POST /api/upload` 端點（在 `backend/api/upload.py` 中）已被修改或替換為 `POST /api/workspaces/{workspace_id}/files`。
    -   [ ] 新的端點路徑參數 `workspace_id` 用於指定檔案上傳的目標工作區。

2.  **授權檢查已實施：**
    -   [ ] 此端點需要身份驗證 (依賴 `get_current_user`)。
    -   [ ] 必須驗證路徑中的 `workspace_id` 屬於當前登入的使用者。若不屬於，應返回 `403 Forbidden`。
    -   [ ] **(推薦)** 建立一個可重用的 `get_workspace_for_user` 授權依賴項來處理此項檢查 (此依賴已在 **BE-06** 定義)。

3.  **服務層邏輯已更新：**
    -   [ ] `backend/services/file_service.py`（或相關服務）中的檔案處理邏輯已被更新。
    -   [ ] 在 `papers` 資料表中建立新紀錄時，必須將傳入的 `workspace_id` 一併存入。
    -   [ ] `file_hash` 的唯一性檢查邏輯已更新，現在是檢查 `(workspace_id, file_hash)` 的複合唯一性。

4.  **背景處理任務已關聯：**
    -   [ ] 檔案上傳後觸發的背景處理任務 (e.g., in `processing_queue`)，在建立時也必須被關聯到正確的 `workspace_id`。
    -   [ ] 檔案大小超過 100MB 時必須使用 **斷點續傳** 機制；Server 需回傳 `upload_session_id` 供前端分段續傳。
    -   [ ] 上傳後必須執行 **病毒掃描** (ClamAV 或同級)；若偵測到威脅，返回 `422 Unprocessable Entity` 並中止處理。

---

### 技術筆記 (Technical Notes)

-   前端 `src/` 也需要相應修改，在上傳檔案時，需從當前的應用狀態中獲取 `workspace_id` 並包含在 API 請求路徑中。
-   -   // FE NOTE: 上傳 API 路徑與斷點續傳機制已變動，需適配 `upload_session_id` 與分段邏輯。
-   這個改造是資料隔離的核心，授權檢查的實作必須嚴謹。
-   依賴於 `BE-01` (身份驗證) 和 `BE-02` (工作區存在)。 