# 剩餘後端 Backlog 摘要 (BE-06 ~ BE-11)

---

## BE-06: 論文管理 API 改造
- **優先級:** High | **估算:** 8 SP
- **核心任務:** 將現有的 `/papers/` 端點群組改造為工作區限定版本
- **重點端點:**
  - `GET /workspaces/{workspace_id}/papers/` - 工作區論文列表
  - `GET /workspaces/{workspace_id}/papers/selected` - 工作區內選取論文
  - `POST /workspaces/{workspace_id}/papers/{paper_id}/select` - 工作區內論文選取切換
  - `GET /workspaces/{workspace_id}/papers/{paper_id}/sentences` - 工作區論文句子
- **技術要點:**
  - 所有查詢都必須加入 `workspace_id` 過濾
  - 論文選取狀態限定在工作區內
  - 保持現有 API 回應格式的一致性
  - 批次操作（全選/取消全選）限定在工作區範圍

---

## BE-07: 查詢處理 API 改造  
- **優先級:** High | **估算:** 8 SP
- **核心任務:** 改造查詢分析功能，確保只在工作區範圍內進行分析
- **重點端點:**
  - `POST /workspaces/{workspace_id}/query/process` - 工作區查詢分析
  - `POST /workspaces/{workspace_id}/unified-query` - 統一查詢介面
  - `GET /workspaces/{workspace_id}/papers/sections-summary` - 工作區章節摘要
- **技術要點:**
  - 查詢分析只能使用工作區內的已選取論文
  - N8N 服務呼叫需要傳遞工作區上下文
  - 結果快取按工作區隔離
  - 查詢歷史記錄到對話系統

---

## BE-08: 對話歷史 API
- **優先級:** High | **估算:** 5 SP  
- **核心任務:** 實作全新的對話歷史功能，支援工作區內的對話管理
- **重點端點:**
  - `GET /workspaces/{workspace_id}/conversations/` - 對話列表
  - `POST /workspaces/{workspace_id}/conversations/` - 建立新對話
  - `GET /workspaces/{workspace_id}/conversations/{conversation_id}` - 對話詳情
  - `POST /workspaces/{workspace_id}/conversations/{conversation_id}/messages` - 新增訊息
- **技術要點:**
  - 對話與 `chat_histories` 表格整合
  - 支援對話的重新命名、刪除
  - 訊息類型支援 `user` 和 `assistant`
  - 訊息可包含引用的來源資訊（metadata）

---

## BE-09: 統一錯誤處理與回應格式
- **優先級:** Medium | **估算:** 3 SP
- **核心任務:** 建立統一的錯誤處理機制，確保所有 API 回應格式一致
- **重點功能:**
  - 標準化的錯誤回應格式
  - 認證/授權錯誤的統一處理
  - 資源不存在錯誤的統一處理
  - 驗證錯誤的統一處理
- **技術要點:**
  - 使用 FastAPI 的異常處理器
  - 記錄結構化錯誤日誌
  - 國際化錯誤訊息支援
  - 開發/生產模式的錯誤詳細程度差異

---

## BE-10: API 版本管理與舊端點棄用
- **優先級:** Medium | **估算:** 5 SP
- **核心任務:** 管理新舊 API 的共存，並規劃舊端點的棄用策略
- **重點功能:**
  - API 版本路由機制 (`/v1/`, `/v2/`)
  - 舊端點的棄用警告與時程
  - 新舊端點的流量監控與分析
  - 平滑遷移工具與文件
- **技術要點:**
  - 使用 FastAPI 的路由前綴機制
  - 在 Response Header 中加入棄用警告
  - 建立 API 使用情況監控儀表板
  - 提供前端遷移指南

---

## BE-11: API 文件與測試更新
- **優先級:** Medium | **估算:** 3 SP
- **核心任務:** 更新所有 API 文件，建立完整的測試套件
- **重點功能:**
  - OpenAPI/Swagger 規格完整性更新
  - 新增認證相關的文件說明
  - 工作區概念的詳細說明
  - 完整的 API 使用範例
- **技術要點:**
  - 使用 FastAPI 的自動文件生成
  - 建立 Postman/Insomnia 測試集合
  - 撰寫 API 遷移指南
  - 整合測試的覆蓋率 > 80%

---

## 實作優先順序總結

### **Sprint 1: 認證基礎 (18 SP)**
- BE-01: Google OAuth (8 SP)
- BE-02: JWT 中介軟體 (5 SP)  
- BE-03: 工作區權限檢查 (5 SP)

### **Sprint 2: 工作區與檔案 (11 SP)**
- BE-04: 工作區管理 API (3 SP)
- BE-05: 檔案上傳 API 改造 (5 SP)
- BE-09: 統一錯誤處理 (3 SP)

### **Sprint 3: 核心功能 (16 SP)**
- BE-06: 論文管理 API 改造 (8 SP)
- BE-07: 查詢處理 API 改造 (8 SP)

### **Sprint 4: 對話與收尾 (13 SP)**
- BE-08: 對話歷史 API (5 SP)
- BE-10: API 版本管理 (5 SP)
- BE-11: 文件更新 (3 SP)

---

## 關鍵風險與依賴

### **高風險項目**
1. **BE-01 (OAuth)**: Google API 整合複雜度
2. **BE-06/BE-07**: 現有 API 邏輯複雜，改造影響面大
3. **BE-10**: 新舊 API 共存期的維護複雜度

### **關鍵依賴**
- 第一階段資料庫模型必須完全部署
- 前端團隊需要配合 API 改造進行相應調整
- 測試環境需要支援多使用者情境測試

### **成功標準**
- [ ] 所有現有功能在新架構下完全可用
- [ ] API 回應時間增加 < 20%
- [ ] 使用者資料完全隔離，無洩漏風險
- [ ] 向後相容期至少維持 4 週
- [ ] 測試覆蓋率 > 80% 