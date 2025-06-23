# Backlog: FE-02 - 多工作區狀態管理重構

- **Epic:** 前端 UX 重構
- **狀態:** To Do
- **優先級:** Highest
- **估算 (Story Points):** 8
- **依賴:** FE-01 (身份驗證完成), BE-02 (工作區API已完成)

---

### 使用者故事 (User Story)

**身為** 一位已登入的使用者，
**我想要** 能夠創建、切換和管理多個獨立的工作區，每個工作區有自己的檔案和對話歷史，
**以便** 我可以為不同的研究項目組織資料，並且各工作區的資料不會互相混淆。

---

### 驗收標準 (Acceptance Criteria)

#### 1. **工作區狀態架構已建立：**
- [ ] 重構現有的狀態管理，支援多工作區命名空間：
  ```typescript
  interface WorkspaceState {
    // 工作區列表與當前工作區
    workspaces: Workspace[];
    currentWorkspaceId: string | null;
    isLoading: boolean;
    
    // 工作區特定的狀態（命名空間隔離）
    workspaceData: Record<string, {
      files: FileData[];
      conversations: Conversation[];
      activeTasks: ActiveTask[];
      selectedReferences: ProcessedSentence[];
      ui: WorkspaceUIState;
    }>;
    
    // 工作區管理動作
    createWorkspace: (name: string) => Promise<void>;
    switchWorkspace: (workspaceId: string) => Promise<void>;
    updateWorkspace: (workspaceId: string, updates: Partial<Workspace>) => Promise<void>;
    deleteWorkspace: (workspaceId: string) => Promise<void>;
    
    // 資料載入與清理
    loadWorkspaceData: (workspaceId: string) => Promise<void>;
    clearWorkspaceData: (workspaceId: string) => void;
  }
  ```
- [ ] 每個工作區維護獨立的檔案列表、對話歷史和UI狀態
- [ ] 支援懶載入：只載入當前工作區的資料，切換時清理舊資料

#### 2. **工作區基本管理功能：**
- [ ] 工作區創建功能：
  - 提供簡潔的創建工作區介面
  - 驗證工作區名稱（非空、長度限制、特殊字符檢查）
  - 創建成功後自動切換到新工作區
- [ ] 工作區列表顯示：
  - 顯示所有使用者擁有的工作區
  - 顯示每個工作區的基本資訊（名稱、建立時間、檔案數量）
  - 提供快速搜尋和篩選功能
- [ ] 工作區切換功能：
  - 快速工作區切換器（下拉選單或側邊欄）
  - 切換時顯示載入狀態
  - 切換完成後更新瀏覽器 URL（如 `/workspace/abc123`）

#### 3. **狀態隔離與資料管理：**
- [ ] 工作區間的完全資料隔離：
  - 檔案列表、對話歷史、進度狀態在工作區間不混淆
  - 切換工作區時清除前一個工作區的記憶體狀態
  - UI 狀態（面板寬度、選中項目等）按工作區獨立儲存
- [ ] 本地儲存策略：
  - 使用 workspace-scoped keys 儲存狀態
  - 只持久化當前工作區的重要狀態
  - 提供清理機制，避免儲存空間無限增長
- [ ] React Query 整合：
  - 為每個工作區建立獨立的 query cache
  - 工作區切換時清理舊的 cache
  - 實現 workspace-scoped 的資料預取

#### 4. **使用者體驗優化：**
- [ ] 工作區初始化體驗：
  - 新使用者首次登入時自動創建預設工作區
  - 提供工作區設定導覽（onboarding）
  - 工作區為空時的友善提示和引導
- [ ] 工作區切換體驗：
  - 平滑的切換動畫和過渡效果
  - 載入狀態的視覺回饋
  - 錯誤狀態的處理（工作區不存在、網路錯誤等）
- [ ] 工作區管理介面：
  - 工作區設定頁面（重新命名、刪除等）
  - 工作區統計資訊（檔案數量、對話次數、使用時間等）
  - 工作區分享或協作功能的基礎結構

---

### 技術實作細節

#### 新增檔案：
- `src/stores/workspaceStore.ts` - 核心工作區狀態管理
- `src/components/workspace/WorkspaceSwitcher.tsx` - 工作區切換器
- `src/components/workspace/WorkspaceCreateModal.tsx` - 創建工作區對話框
- `src/components/workspace/WorkspaceSettings.tsx` - 工作區設定頁面
- `src/hooks/useWorkspace.ts` - 工作區管理 Hook
- `src/hooks/useWorkspaceData.ts` - 工作區資料管理 Hook
- `src/contexts/WorkspaceContext.tsx` - 工作區上下文提供者
- `src/types/workspace.ts` - 工作區相關類型定義

#### 修改檔案：
- `src/stores/appStore.ts` - 與工作區狀態整合
- `src/stores/fileStore.ts` - 重構為支援多工作區
- `src/stores/chatStore.ts` - 重構為支援多工作區
- `src/App.tsx` - 添加工作區上下文提供者
- `src/components/ResponsiveMainLayout.tsx` - 整合工作區切換器

#### 核心架構設計：

1. **狀態命名空間模式**：
   ```typescript
   // 為每個工作區創建獨立的狀態切片
   const createWorkspaceSlice = (workspaceId: string) => ({
     files: createFileSlice(workspaceId),
     chats: createChatSlice(workspaceId),
     progress: createProgressSlice(workspaceId),
     ui: createUISlice(workspaceId)
   });
   ```

2. **Context Provider 模式**：
   ```typescript
   export const WorkspaceProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
     const currentWorkspace = useCurrentWorkspace();
     
     return (
       <WorkspaceContext.Provider value={currentWorkspace}>
         {children}
       </WorkspaceContext.Provider>
     );
   };
   ```

3. **懶載入資料管理**：
   ```typescript
   const useWorkspaceData = (workspaceId: string) => {
     return useQuery({
       queryKey: ['workspace', workspaceId],
       queryFn: () => loadWorkspaceData(workspaceId),
       enabled: !!workspaceId,
       staleTime: 5 * 60 * 1000, // 5 minutes
     });
   };
   ```

---

### 效能考量

#### 記憶體管理：
- [ ] **工作區資料清理**: 切換工作區時自動清理前一個工作區的資料
- [ ] **懶載入策略**: 只在需要時載入工作區資料，避免一次載入所有工作區
- [ ] **資料預取**: 預取使用者最常使用的工作區資料

#### 儲存優化：
- [ ] **選擇性持久化**: 只儲存重要的狀態，避免儲存過多暫時性資料
- [ ] **資料壓縮**: 對大型狀態物件進行壓縮儲存
- [ ] **過期清理**: 定期清理過期的工作區快取資料

---

### 遷移策略

#### 舊狀態相容性：
- [ ] **向後相容**: 支援現有的單一全域狀態模式，逐步遷移
- [ ] **資料遷移**: 將現有的檔案和對話資料遷移到預設工作區
- [ ] **Feature Flag**: 使用功能開關控制新舊狀態管理的切換

#### 元件適配：
- [ ] **漸進式重構**: 現有元件透過適配器使用新的狀態管理
- [ ] **HOC 包裝**: 為舊元件提供工作區上下文包裝器
- [ ] **型別安全**: 確保新舊 API 的型別一致性

---

### 測試要求

#### 單元測試：
- [ ] 工作區狀態管理的所有動作（創建、切換、更新、刪除）
- [ ] 狀態隔離邏輯測試（工作區間資料不互相影響）
- [ ] 本地儲存的序列化和反序列化測試

#### 整合測試：
- [ ] 工作區切換的完整流程測試
- [ ] 多工作區間的資料隔離測試
- [ ] React Query 快取管理測試

#### 效能測試：
- [ ] 大量工作區的效能測試（> 50 個工作區）
- [ ] 記憶體洩漏檢測
- [ ] 工作區切換的回應時間測試

---

### 完成標準 (Definition of Done)

- [ ] 所有驗收標準已達成並通過測試
- [ ] 工作區狀態管理完全隔離，無資料混淆
- [ ] 工作區切換體驗流暢，載入時間 < 1 秒
- [ ] 現有功能在新架構下正常運作
- [ ] 程式碼覆蓋率 > 85%，特別是狀態管理邏輯
- [ ] TypeScript 嚴格模式檢查通過
- [ ] 效能指標符合要求（記憶體使用、切換時間）
- [ ] 遷移文檔和 API 文檔已更新

---

### 風險與緩解策略

| 風險項目 | 風險等級 | 緩解策略 |
|:---|:---:|:---|
| 狀態管理複雜度過高 | 高 | 採用漸進式重構，保持向後相容 |
| 記憶體洩漏問題 | 中 | 建立嚴格的資料清理機制和測試 |
| 資料遷移失敗 | 中 | 建立完整的備份和回滾策略 |
| 效能下降 | 中 | 實施懶載入和預取策略，持續監控效能 |
| 使用者體驗中斷 | 低 | 提供平滑的切換動畫和載入狀態 |

---

此任務完成後，前端將具備完整的多工作區支援能力，為使用者提供類似 Google NotebookLM 的個人化工作空間體驗，並為後續功能的工作區化改造奠定堅實基礎。 