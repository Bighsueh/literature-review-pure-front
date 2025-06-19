# Backlog: BE-02 - JWT 認證中介軟體

- **Epic:** 從匿名系統轉為多使用者工作區 API 架構
- **狀態:** To Do
- **優先級:** Highest
- **估算 (Story Points):** 5

---

### 使用者故事 (User Story)

**身為** 一位後端開發者，
**我想要** 建立一個統一的 JWT 認證中介軟體系統，
**以便** 所有需要認證的 API 端點都能自動驗證使用者身份，並將使用者資訊注入到請求上下文中，簡化後續的業務邏輯開發。

---

### 驗收標準 (Acceptance Criteria)

1.  **JWT 驗證中介軟體已實作：**
    -   [ ] 自動解析 Authorization Header 或 Cookie 中的 JWT。
    -   [ ] 驗證 JWT 的簽名有效性和過期時間。
    -   [ ] 解析 JWT 中的使用者資訊並注入到 FastAPI 的依賴注入系統中。

2.  **使用者上下文管理：**
    -   [ ] 建立 `CurrentUser` 依賴注入類別，包含 `user_id`、`email`、`name` 等資訊。
    -   [ ] 提供 `get_current_user()` 函數供其他 API 端點使用。
    -   [ ] 支援可選認證（某些端點可以不要求登入）。

3.  **錯誤處理機制：**
    -   [ ] JWT 無效時回傳 `401 Unauthorized`。
    -   [ ] JWT 過期時回傳 `401 Unauthorized` 並提示重新登入。
    -   [ ] 缺少 JWT 時回傳 `401 Unauthorized`。

4.  **FastAPI 整合：**
    -   [ ] 使用 FastAPI 的 `Depends` 機制實作依賴注入。
    -   [ ] 支援路由層級和全域的認證要求。
    -   [ ] 與 FastAPI 的 OpenAPI 文件自動整合。

5.  **效能最佳化：**
    -   [ ] JWT 驗證過程的時間開銷控制在 5ms 以內。
    -   [ ] 避免每次請求都查詢資料庫（使用 JWT 中的資訊）。
    -   [ ] 支援 JWT 快取機制（可選）。

---

### 技術規格 (Technical Specifications)

#### **中介軟體架構**
```python
# 核心依賴注入函數
async def get_current_user(token: str = Depends(oauth2_scheme)) -> CurrentUser:
    # JWT 驗證邏輯
    pass

async def get_current_user_optional(token: str = Depends(oauth2_scheme_optional)) -> CurrentUser | None:
    # 可選認證邏輯
    pass
```

#### **CurrentUser 模型**
```python
@dataclass
class CurrentUser:
    user_id: str
    email: str
    name: str
    picture_url: Optional[str]
    default_workspace_id: str
    
    def has_workspace_access(self, workspace_id: str) -> bool:
        # 工作區權限檢查邏輯
        pass
```

#### **JWT Token 位置**
- **優先級 1**: `Authorization: Bearer <token>` header
- **優先級 2**: `auth_token` HTTP-Only cookie
- **回退**: 查詢參數 `?token=<token>`（僅用於特殊情況）

---

### API 整合範例

#### **必須認證的端點**
```python
@router.get("/papers/")
async def get_papers(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 已認證的使用者，可直接使用 current_user
    pass
```

#### **可選認證的端點**
```python
@router.get("/public-info/")
async def get_public_info(
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional)
):
    # 可能有認證，也可能沒有
    if current_user:
        # 個人化內容
        pass
    else:
        # 公開內容
        pass
```

---

### 錯誤回應格式

#### **401 Unauthorized**
```json
{
  "error": "unauthorized",
  "message": "認證失敗，請重新登入",
  "details": {
    "reason": "token_expired" | "token_invalid" | "token_missing"
  }
}
```

#### **403 Forbidden**
```json
{
  "error": "forbidden", 
  "message": "權限不足",
  "details": {
    "required_permission": "workspace_access",
    "resource_id": "workspace_uuid"
  }
}
```

---

### 測試策略

#### **單元測試**
- [ ] JWT 解析與驗證邏輯
- [ ] 錯誤情境處理（過期、無效、缺失 token）
- [ ] CurrentUser 物件建立與方法

#### **整合測試**
- [ ] 完整的認證流程（從登入到 API 呼叫）
- [ ] 不同 token 傳遞方式的相容性
- [ ] FastAPI 依賴注入的正確性

#### **效能測試**
- [ ] 大量併發請求下的認證效能
- [ ] JWT 驗證的記憶體使用量
- [ ] 認證快取機制的有效性

---

### 實作順序

1. **階段 1**: 基礎 JWT 驗證邏輯
2. **階段 2**: FastAPI 依賴注入整合
3. **階段 3**: 錯誤處理與安全性強化
4. **階段 4**: 效能最佳化與快取機制

---

### 技術筆記 (Technical Notes)

-   **安全性**: JWT 驗證必須嚴格檢查簽名和過期時間，避免安全漏洞。
-   **向後相容**: 初期可能需要支援「認證 + 非認證」的混合模式，方便逐步遷移。
-   **錯誤處理**: 所有認證相關的錯誤都應該統一處理，避免洩漏系統內部資訊。
-   **依賴**: 此任務必須在 BE-01 (Google OAuth) 完成後才能開始。
-   **整合**: 與後續的 BE-03 (工作區權限檢查) 緊密整合。 