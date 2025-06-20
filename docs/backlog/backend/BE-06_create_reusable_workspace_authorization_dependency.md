# Backlog: BE-06 - 建立可重用的工作區授權依賴項

- **Epic:** 後端 API 改造
- **狀態:** To Do
- **優先級:** High
- **估算 (Story Points):** 3

---

### 使用者故事 (User Story)

**身為** 一位後端開發者，
**我想要** 建立一個集中式的 FastAPI 依賴項，專門用來驗證當前使用者是否有權存取請求路徑中指定的工作區，
**以便** 我在開發新的 API 端點時，可以輕鬆地重用這個授權邏輯，而無需在每個路由函式中重複編寫相同的驗證程式碼，從而提高開發效率和系統安全性。

---

### 驗收標準 (Acceptance Criteria)

1.  **授權依賴項函式已建立：**
    -   [ ] 在 `backend/api/dependencies.py` (或類似位置) 中，已建立一個名為 `get_workspace_for_user` 的函式。
    -   [ ] 此函式接受 `workspace_id: UUID` (來自路徑) 和 `current_user: User = Depends(get_current_user)` 作為參數。
    -   [ ] 函式內部會查詢 `workspaces` 表，找到對應的 `workspace`。
    -   [ ] 如果找不到 `workspace`，應返回 `404 Not Found`。
    -   [ ] 如果 `workspace.user_id` 與 `current_user.id` 不匹配，應返回 `403 Forbidden`。
    -   [ ] 如果驗證通過，函式應返回該 `workspace` 的模型對象。

2.  **現有 API 已重構以使用新依賴項：**
    -   [ ] `BE-03` (檔案上傳)、`BE-04` (檔案管理)、`BE-05` (查詢) 等故事中涉及的 API 端點，都已改為使用這個新的 `Depends(get_workspace_for_user)`。
    -   [ ] 路由函式中原有的手動授權檢查邏輯已被移除，程式碼變得更簡潔。

---

### 技術筆記 (Technical Notes)

-   這是典型的 FastAPI 依賴注入系統的應用，是寫出乾淨、可維護的 FastAPI 應用的關鍵實踐。
-   這個故事本身不提供新的使用者功能，但它極大地提升了程式碼品質和開發者體驗，屬於重要的**技術投資**。
-   應優先於其他需要授權的 API 改造任務（`BE-03`, `BE-04`, `BE-05`）之前或之中完成，以便它們能直接受益。
-   -   // FE NOTE: 此 Story 不影響 API 路徑結構，但授權失敗將返回 `403`，前端需統一錯誤處理。 