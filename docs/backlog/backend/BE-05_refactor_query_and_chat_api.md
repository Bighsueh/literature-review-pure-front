# Backlog: BE-05 - 改造查詢與對話 API 以支援工作區

- **Epic:** 後端 API 改造
- **狀態:** To Do
- **優先級:** High
- **估算 (Story Points):** 8

---

### 使用者故事 (User Story)

**身為** 一位在特定工作區內的使用者，
**我想要** 我提出的問題只會基於當前工作區的檔案來回答，並且對話紀錄會被獨立保存，
**以便** 我可以針對不同專案進行專注且連貫的深入探討。

---

### 驗收標準 (Acceptance Criteria)

1.  **查詢 API 已重構：**
    -   [ ] 原有的查詢端點 (假設為 `POST /api/query`) 已被修改為 `POST /api/workspaces/{workspace_id}/query`。
    -   [ ] 此端點需要授權檢查，確保使用者能存取該 `workspace_id`。
    -   [ ] `backend/services/unified_query_service.py` (或相關服務) 的邏輯已更新，在檢索資料來源 (e.g., `sentences`) 時，必須使用 `workspace_id` 進行嚴格過濾。

2.  **對話歷史記錄功能已實現：**
    -   [ ] 在 `/query` 請求處理完成後，使用者的問題和 AI 的回答會被保存到 `chat_histories` 資料表中。
    -   [ ] 保存時，必須將 `workspace_id` 一併寫入，確保對話紀錄與工作區關聯。

3.  **對話歷史查詢 API 已建立：**
    -   [ ] 已建立新的端點 `GET /api/workspaces/{workspace_id}/chats`。
    -   [ ] 此端點需要授權檢查。
    -   [ ] 返回屬於指定 `workspace_id` 的完整對話歷史，並按時間順序排序。

---

### 技術筆記 (Technical Notes)

-   **前置條件：** 依賴資料庫階段 `DB-02` (chat_histories 表) 和 `DB-04` (sentences 工作區隔離) 已完成。
-   這是對系統核心價值的直接改造，對 `unified_query_service.py` 的修改是本任務的關鍵和難點。
-   需要確保傳遞給語言模型的上下文 (Context) 完全來自於指定的 `workspace_id`，這是防止資料外洩的關鍵安全點。
-   -   必須限制 LLM Prompt 長度 (e.g., max 4,096 tokens)；超過時應分段查詢。
-   -   需實作對 User Prompt 的 **Prompt Injection** 檢測，排除潛在攻擊字串。
-   對話歷史的儲存和查詢是全新功能，需要定義對應的 Pydantic Schema。
-   -   // FE NOTE: 新增 `/chats` 分頁端點，前端 `ChatMessageList` 需支援分頁載入。
-   依賴於 `BE-01`, `BE-04` 的完成。 