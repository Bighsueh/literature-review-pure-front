# Backlog: BE-03 - 工作區權限檢查機制

- **Epic:** 從匿名系統轉為多使用者工作區 API 架構
- **狀態:** To Do
- **優先級:** Highest
- **估算 (Story Points):** 5

---

### 使用者故事 (User Story)

**身為** 一位系統安全工程師，
**我想要** 建立一套嚴格的工作區權限檢查機制，
**以便** 確保每個使用者只能存取和操作自己擁有的工作區和其中的資料，防止跨使用者的資料洩漏或誤操作。

---

### 驗收標準 (Acceptance Criteria)

1.  **工作區存取權限驗證：**
    -   [ ] 使用者只能存取自己擁有的工作區（`workspaces.user_id = current_user.user_id`）。
    -   [ ] 嘗試存取他人工作區時回傳 `403 Forbidden`。
    -   [ ] 工作區不存在時回傳 `404 Not Found`。

2.  **依賴注入機制：**
    -   [ ] 建立 `get_user_workspace()` 依賴注入函數。
    -   [ ] 自動從路由參數中提取 `workspace_id` 並驗證權限。
    -   [ ] 回傳驗證過的 `Workspace` 物件供後續業務邏輯使用。

3.  **當前工作區管理：**
    -   [ ] 支援從 JWT 中取得使用者的「當前工作區」。
    -   [ ] 提供 `get_current_workspace()` 函數（不需要路由參數）。
    -   [ ] 允許使用者切換當前工作區。

4.  **資料隔離強制執行：**
    -   [ ] 所有與工作區相關的資料查詢都必須加入 `workspace_id` 過濾條件。
    -   [ ] 建立輔助函數確保資料庫查詢的安全性。
    -   [ ] 防範 SQL 注入和權限提升攻擊。

5.  **錯誤處理與日誌：**
    -   [ ] 記錄所有權限檢查失敗的嘗試（用於安全稽核）。
    -   [ ] 提供清晰的錯誤訊息，但不洩漏敏感資訊。
    -   [ ] 支援開發模式的詳細除錯資訊。

---

### 技術規格 (Technical Specifications)

#### **核心依賴注入函數**
```python
async def get_user_workspace(
    workspace_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Workspace:
    """
    驗證使用者對指定工作區的存取權限
    """
    # 1. 檢查工作區是否存在
    # 2. 驗證使用者擁有權
    # 3. 回傳 Workspace 物件
    pass

async def get_current_workspace(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Workspace:
    """
    取得使用者的當前工作區
    """
    # 從 JWT 中的 default_workspace_id 載入工作區
    pass
```

#### **Workspace 模型擴充**
```python
@dataclass
class WorkspaceContext:
    workspace: Workspace
    user: CurrentUser
    
    def ensure_workspace_access(self, resource_workspace_id: str) -> None:
        """確保資源屬於當前工作區"""
        if resource_workspace_id != self.workspace.id:
            raise PermissionDenied("資源不屬於當前工作區")
```

#### **安全查詢輔助函數**
```python
class WorkspaceSecureQuery:
    def __init__(self, workspace_id: str):
        self.workspace_id = workspace_id
    
    def filter_papers(self, query):
        """安全的論文查詢過濾"""
        return query.filter(Paper.workspace_id == self.workspace_id)
    
    def filter_sentences(self, query):
        """安全的句子查詢過濾"""  
        return query.filter(Sentence.workspace_id == self.workspace_id)
```

---

### API 整合範例

#### **工作區限定的端點**
```python
@router.get("/workspaces/{workspace_id}/papers/")
async def get_workspace_papers(
    workspace: Workspace = Depends(get_user_workspace),
    db: AsyncSession = Depends(get_db)
):
    # workspace 已經過權限驗證，可安全使用
    secure_query = WorkspaceSecureQuery(workspace.id)
    papers_query = secure_query.filter_papers(
        db.query(Paper)
    )
    return await papers_query.all()
```

#### **當前工作區的端點**
```python
@router.get("/my/papers/")
async def get_my_papers(
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db)
):
    # 使用使用者的預設/當前工作區
    secure_query = WorkspaceSecureQuery(workspace.id)
    # ... 查詢邏輯
```

#### **工作區切換端點**
```python
@router.post("/my/workspace/switch")
async def switch_workspace(
    target_workspace_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 驗證目標工作區權限並更新使用者的當前工作區
    pass
```

---

### 安全策略

#### **權限檢查層級**
1. **路由層級**: 透過 `get_user_workspace` 依賴注入
2. **查詢層級**: 透過 `WorkspaceSecureQuery` 強制過濾
3. **業務邏輯層級**: 透過 `WorkspaceContext.ensure_workspace_access`

#### **錯誤回應格式**
```json
{
  "error": "workspace_access_denied",
  "message": "您沒有權限存取此工作區",
  "details": {
    "workspace_id": "requested_workspace_id",
    "user_id": "current_user_id"
  }
}
```

#### **安全日誌格式**
```json
{
  "event": "workspace_access_denied",
  "user_id": "user_uuid",
  "requested_workspace_id": "workspace_uuid", 
  "user_workspaces": ["workspace1", "workspace2"],
  "timestamp": "2024-01-01T00:00:00Z",
  "ip_address": "127.0.0.1"
}
```

---

### 測試策略

#### **安全測試**
- [ ] 跨使用者工作區存取測試（應失敗）
- [ ] 不存在工作區存取測試（應 404）
- [ ] SQL 注入嘗試測試
- [ ] 權限提升嘗試測試

#### **功能測試**
- [ ] 正常工作區存取測試
- [ ] 工作區切換功能測試
- [ ] 多工作區使用者的權限管理
- [ ] 當前工作區的正確性測試

#### **效能測試**
- [ ] 權限檢查的效能開銷測試
- [ ] 大量工作區使用者的查詢效能
- [ ] 資料庫查詢最佳化驗證

---

### 實作階段

1. **階段 1**: 基礎權限檢查邏輯
2. **階段 2**: FastAPI 依賴注入整合  
3. **階段 3**: 安全查詢輔助函數
4. **階段 4**: 安全日誌與監控機制

---

### 技術筆記 (Technical Notes)

-   **零信任原則**: 所有資料存取都必須經過明確的權限檢查，不假設任何請求的安全性。
-   **效能考量**: 權限檢查應該儘量與業務查詢合併，避免額外的資料庫查詢。
-   **錯誤處理**: 權限錯誤和資源不存在錯誤應該有所區別，避免資訊洩漏。
-   **依賴關係**: 此功能依賴於 BE-01 (OAuth) 和 BE-02 (JWT) 的完成。
-   **資料庫**: 需要第一階段的資料庫模型（`workspaces` 表）已經部署完成。 