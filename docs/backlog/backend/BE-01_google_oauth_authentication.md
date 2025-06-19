# Backlog: BE-01 - Google OAuth 2.0 認證系統

- **Epic:** 從匿名系統轉為多使用者工作區 API 架構
- **狀態:** To Do
- **優先級:** Highest
- **估算 (Story Points):** 8

---

### 使用者故事 (User Story)

**身為** 一位使用者，
**我想要** 能夠使用我的 Google 帳號安全地登入系統，
**以便** 存取我個人的工作區和資料，而不需要記住額外的密碼或帳號資訊。

---

### 驗收標準 (Acceptance Criteria)

1.  **Google OAuth 2.0 整合完成：**
    -   [ ] 系統能夠重新導向使用者到 Google 授權頁面。
    -   [ ] 成功處理 Google 授權後的回調 (callback)。
    -   [ ] 能夠取得使用者的基本資訊（ID、Email、名稱、頭像）。

2.  **認證端點已建立：**
    -   [ ] `GET /auth/google` - 初始化 OAuth 流程
    -   [ ] `GET /auth/google/callback` - 處理 Google 回調
    -   [ ] `POST /auth/logout` - 登出端點
    -   [ ] `GET /auth/me` - 取得當前使用者資訊

3.  **使用者自動註冊機制：**
    -   [ ] 首次登入的使用者會自動在 `users` 表中建立記錄。
    -   [ ] 自動為新使用者建立一個預設工作區。
    -   [ ] 重複登入的使用者資訊會被更新（名稱、頭像等）。

4.  **JWT Token 簽發：**
    -   [ ] 成功認證後簽發包含使用者資訊的 JWT。
    -   [ ] JWT 包含 `user_id`、`email`、`default_workspace_id` 等資訊。
    -   [ ] Token 有適當的過期時間（建議 24 小時）。

5.  **錯誤處理與安全性：**
    -   [ ] 處理 Google OAuth 錯誤（使用者拒絕授權、網路錯誤等）。
    -   [ ] 防範 CSRF 攻擊（使用 state 參數）。
    -   [ ] 敏感資訊（Client Secret）安全儲存在環境變數中。

---

### 技術規格 (Technical Specifications)

#### **OAuth 設定**
- **Scopes**: `openid`, `email`, `profile`
- **Flow Type**: Authorization Code Flow
- **Client Type**: Web Application

#### **JWT 設計**
```json
{
  "sub": "user_id",
  "email": "user@example.com", 
  "name": "使用者名稱",
  "default_workspace_id": "workspace_uuid",
  "iat": 1234567890,
  "exp": 1234654290
}
```

#### **環境變數需求**
- `GOOGLE_CLIENT_ID`: Google OAuth Client ID
- `GOOGLE_CLIENT_SECRET`: Google OAuth Client Secret  
- `JWT_SECRET_KEY`: JWT 簽名密鑰
- `OAUTH_REDIRECT_URI`: OAuth 回調 URL

#### **依賴套件**
- `authlib`: OAuth 2.0 客戶端實作
- `python-jose`: JWT 處理
- `httpx`: HTTP 客戶端（與 Google API 通訊）

---

### API 端點設計

#### **GET /auth/google**
```python
# 重新導向到 Google OAuth 授權頁面
# Query Parameters:
#   - redirect_url (optional): 認證成功後的重導向目標
# Response: 302 Redirect
```

#### **GET /auth/google/callback**
```python
# 處理 Google OAuth 回調
# Query Parameters:
#   - code: 授權碼
#   - state: CSRF 防護狀態
# Response: 
#   - 成功: 302 重導向至前端 + JWT Cookie
#   - 失敗: 400/500 錯誤頁面
```

#### **POST /auth/logout**
```python
# 登出使用者
# Response: {"success": true, "message": "登出成功"}
```

#### **GET /auth/me**
```python
# 取得當前使用者資訊
# Headers: Authorization: Bearer <JWT>
# Response: {
#   "user_id": "uuid",
#   "email": "user@example.com",
#   "name": "使用者名稱", 
#   "picture_url": "https://...",
#   "workspaces": [...]
# }
```

---

### 測試策略

#### **單元測試**
- [ ] JWT 簽發與驗證邏輯
- [ ] 使用者自動註冊流程
- [ ] 錯誤處理情境

#### **整合測試**
- [ ] 完整 OAuth 流程（使用 Mock Google API）
- [ ] 資料庫使用者建立與更新
- [ ] JWT 與資料庫資料一致性

---

### 技術筆記 (Technical Notes)

-   **安全考量**: 所有敏感資訊必須透過環境變數管理，絕不能硬編碼在程式中。
-   **Session 管理**: 系統採用 Stateless 設計，不在伺服器端儲存 Session 資訊。
-   **Error Handling**: 需要優雅地處理 Google API 的各種錯誤狀況，並提供使用者友善的錯誤訊息。
-   **前端整合**: JWT 可透過 HTTP-Only Cookie 或 Authorization Header 傳遞，需與前端團隊協調。
-   這是整個多使用者系統的基石，後續所有 API 都將依賴此認證機制。 