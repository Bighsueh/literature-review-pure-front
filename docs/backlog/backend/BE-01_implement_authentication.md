# Backlog: BE-01 - 實現 Google OAuth 與 JWT 身份驗證

- **Epic:** 後端 API 改造
- **狀態:** To Do
- **優先級:** Highest
- **估算 (Story Points):** 8

---

### 使用者故事 (User Story)

**身為** 一位新訪客，
**我想要** 透過我的 Google 帳號安全地登入系統，並取得一個臨時的身份憑證，
**以便** 系統能夠識別我的身份，為我提供個人化的工作區服務。

---

### 驗收標準 (Acceptance Criteria)

1.  **新的 OAuth 認證流程已建立：**
    -   [ ] `backend/api` 中已新增 `auth.py`，包含 `/api/auth/google` 端點，能將使用者重導向至 Google 授權頁面。
    -   [ ] 包含 `/api/auth/google/callback` 端點，能處理來自 Google 的回調請求，並成功交換到使用者資訊。
    -   [ ] 首次登入的使用者，其資訊會被自動寫入 `users` 資料表。

2.  **JWT 簽發與驗證機制已實作：**
    -   [ ] 在 `callback` 端點成功驗證使用者後，系統能簽發一個包含 `user_id` 的 JWT (JSON Web Token)。
    -   [ ] JWT 應設定合理的過期時間 (e.g., 24 小時)。
    -   [ ] 在 `backend/core` 中已建立 `security.py`，提供 `create_access_token` 和 `verify_token` 的功能。

3.  **FastAPI 安全依賴項已建立：**
    -   [ ] 已建立一個可重複使用的 FastAPI 依賴項 (e.g., `get_current_user`)。
    -   [ ] 此依賴項能從請求的 `Authorization` 標頭中解析 JWT，驗證其有效性，並返回對應的 `User` 模型對象。
    -   [ ] 如果 Token 無效、過期或不存在，應返回 `401 Unauthorized` 錯誤。

---

### 技術筆記 (Technical Notes)

-   **前置條件：** 依賴資料庫階段 `DB-01` (users & workspaces 表) 已完成。
-   此任務需要處理的環境變數：`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `JWT_SECRET_KEY`, `JWT_ALGORITHM`。
-   OAuth 流程會涉及跨域 (CORS) 問題，需要在 FastAPI 中間件中正確設定。
-   建議使用 `python-jose` 函式庫來處理 JWT。
-   -   需支援 OAuth PKCE Flow：前端取得 `code_verifier`/`code_challenge`，後端於 callback 驗證。
-   -   Token Refresh Strategy：使用 `refresh_token` 交換新的 JWT；過期時提示前端重新登入。
-   -   OpenAPI 規格需包含 `/api/auth/*` 路徑與 401/403 回應樣本，方便前端產生型別。
-   -   // FE NOTE: 登入流程與 Token 存取方式 (Authorization: Bearer) 已確立，前端整合時請按照 OpenAPI 規格實作。
-   這是後續所有需要授權的 API 的**前置依賴**。 