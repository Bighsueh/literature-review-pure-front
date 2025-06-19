# Backlog: BE-04 - 工作區管理 API

- **Epic:** 從匿名系統轉為多使用者工作區 API 架構
- **狀態:** To Do
- **優先級:** High
- **估算 (Story Points):** 3

---

### 使用者故事 (User Story)

**身為** 一位使用者，
**我想要** 能夠建立、檢視、重新命名和刪除我的工作區，
**以便** 有效地組織我的不同專案和研究主題，並在需要時切換工作環境。

---

### 驗收標準 (Acceptance Criteria)

1.  **工作區 CRUD 操作：**
    -   [ ] `POST /workspaces/` - 建立新工作區
    -   [ ] `GET /workspaces/` - 取得使用者的所有工作區列表
    -   [ ] `GET /workspaces/{workspace_id}` - 取得指定工作區詳細資訊
    -   [ ] `PATCH /workspaces/{workspace_id}` - 更新工作區（名稱等）
    -   [ ] `DELETE /workspaces/{workspace_id}` - 刪除工作區

2.  **工作區切換功能：**
    -   [ ] `POST /workspaces/{workspace_id}/activate` - 設定為當前工作區
    -   [ ] `GET /workspaces/current` - 取得當前工作區資訊
    -   [ ] 更新 JWT 中的 `default_workspace_id`

3.  **業務規則實施：**
    -   [ ] 使用者至少必須擁有一個工作區（不能刪除最後一個）
    -   [ ] 工作區名稱在同一使用者內必須唯一
    -   [ ] 新使用者註冊時自動建立「我的第一個工作區」

4.  **資料統計與摘要：**
    -   [ ] 每個工作區顯示包含的檔案數量、對話數量等統計資訊
    -   [ ] 工作區的最後活動時間記錄

---

### API 端點設計

#### **POST /workspaces/**
```json
// Request
{
  "name": "新專案研究",
  "description": "關於 AI 倫理的研究專案"
}

// Response  
{
  "id": "workspace_uuid",
  "name": "新專案研究", 
  "description": "關於 AI 倫理的研究專案",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z",
  "stats": {
    "papers_count": 0,
    "conversations_count": 0
  }
}
```

#### **GET /workspaces/**
```json
// Response
{
  "workspaces": [
    {
      "id": "workspace_uuid_1",
      "name": "我的第一個工作區",
      "description": null,
      "created_at": "2024-01-01T00:00:00Z", 
      "last_activity_at": "2024-01-02T10:30:00Z",
      "stats": {
        "papers_count": 5,
        "conversations_count": 12
      },
      "is_current": true
    },
    {
      "id": "workspace_uuid_2", 
      "name": "新專案研究",
      "description": "關於 AI 倫理的研究專案",
      "created_at": "2024-01-01T00:00:00Z",
      "last_activity_at": "2024-01-01T00:00:00Z", 
      "stats": {
        "papers_count": 0,
        "conversations_count": 0
      },
      "is_current": false
    }
  ],
  "total_count": 2
}
```

---

### 測試策略

#### **功能測試**
- [ ] 工作區建立、更新、刪除的完整流程
- [ ] 工作區名稱唯一性約束測試
- [ ] 最後一個工作區刪除保護測試
- [ ] 工作區切換與 JWT 更新測試

#### **安全測試**  
- [ ] 跨使用者工作區操作阻擋測試
- [ ] 權限檢查機制驗證
- [ ] 輸入驗證與清理測試

---

### 技術筆記 (Technical Notes)

-   **資料完整性**: 刪除工作區時必須連帶清理所有相關資料（papers, sentences, chat_histories 等）
-   **效能考量**: 工作區統計資訊可考慮快取機制，避免每次都即時計算
-   **JWT 更新**: 工作區切換後需要重新簽發 JWT 或使用 refresh token 機制
-   **依賴**: 需要 BE-01 到 BE-03 的認證與權限基礎設施完成 