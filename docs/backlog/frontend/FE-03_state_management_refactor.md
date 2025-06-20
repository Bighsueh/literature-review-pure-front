# Backlog: FE-03 - 重構核心狀態管理以支援多工作區

- **Epic:** 前端 UX 重構
- **狀態:** To Do
- **優先級:** Highest
- **估算 (Story Points):** 13

---

### 技術故事 (Technical Story)

**身為** 一位前端開發者，
**我想要** 將現有的全域 `Zustand` Stores (`fileStore`, `chatStore`) 重構為一個**命名空間式的單一 Store**，以 `workspaceId` 為鍵值進行狀態隔離，
**以便** 每個工作區都能擁有獨立的狀態分支，同時維持型別安全和調試便利性，避免動態 Store 創建的複雜性。

---

### 驗收標準 (Acceptance Criteria)

1.  **命名空間式 Store 已建立：**
    -   [ ] 重構 `appStore` 為統一的狀態容器，結構為 `{ workspaces: { [workspaceId]: { files: [], chats: [], ui: {} } } }`。
    -   [ ] 當使用者首次訪問某個工作區時，會為該 `workspaceId` 初始化對應的狀態分支。
    -   [ ] 保持完整的 TypeScript 型別推斷，避免 `any` 或複雜的型別體操。

2.  **狀態存取機制已更新：**
    -   [ ] 建立選擇器 Hook `useWorkspaceData(workspaceId)` 和 `useCurrentWorkspace()`，提供型別安全的狀態存取。
    -   [ ] 重構所有元件，從直接使用 `useFileStore()` 改為使用新的選擇器 Hook。
    -   [ ] 實現狀態更新的 action creators，確保每個操作都正確更新對應工作區的狀態。

3.  **狀態生命週期管理已實現：**
    -   [ ] 實現簡單的 LRU 快取策略：最多保留最近使用的 5 個工作區狀態在記憶體中。
    -   [ ] 超過快取限制時，自動清除最久未使用的工作區狀態，避免記憶體膨脹。
    -   [ ] 提供狀態序列化功能，支援將工作區狀態持久化到 localStorage。

4.  **漸進式遷移機制：**
    -   [ ] 實現 Feature Flag 系統，可在新舊狀態管理間切換，確保遷移安全性。
    -   [ ] 建立狀態遷移函式，將既有全域狀態轉換為命名空間格式。
    -   [ ] 所有關鍵操作都有完整的錯誤邊界和回滾機制。

---

### 技術筆記 (Technical Notes)

-   **主要修改檔案**: `stores/appStore.ts` (統一狀態容器), `hooks/useWorkspace.ts` (選擇器 Hook)。
-   **新增檔案**: `utils/stateCache.ts` (LRU 快取), `utils/featureFlags.ts` (Feature Flag 系統)。
-   採用**命名空間模式**而非動態 Store 創建，降低複雜度和記憶體洩漏風險。
-   **依賴**: 需要 `FE-00` 的型別定義，確保狀態結構與 API 回應格式一致。
-   **風險控制**: 透過 Feature Flag 實現漸進式遷移，可隨時回滾到舊版狀態管理。 

# Backlog: FE-03 - 工作區管理界面開發

- **Epic:** 前端 UX 重構
- **狀態:** To Do
- **優先級:** High
- **估算 (Story Points):** 5
- **依賴:** FE-02 (多工作區狀態管理完成)

---

### 使用者故事 (User Story)

**身為** 一位已登入的使用者，
**我想要** 擁有直觀易用的工作區管理界面，能夠方便地創建、切換、重新命名和刪除工作區，
**以便** 我可以有效地組織我的研究項目，並快速在不同工作區間導航。

---

### 驗收標準 (Acceptance Criteria)

#### 1. **工作區切換器組件已實現：**
- [ ] 主導航欄中的工作區切換器：
  - 顯示當前工作區名稱和圖示
  - 點擊後展開工作區選單
  - 支援鍵盤導航（方向鍵、Enter、Escape）
  - 顯示每個工作區的基本統計（檔案數、最後使用時間）
- [ ] 工作區選單功能：
  - 列出所有使用者擁有的工作區
  - 即時搜尋和篩選功能
  - 支援按名稱、創建時間、使用頻率排序
  - 無障礙功能支援（ARIA labels、screen reader 友善）

#### 2. **工作區創建流程已完成：**
- [ ] 創建工作區對話框：
  - 簡潔的 Modal 設計，包含工作區名稱輸入欄
  - 即時驗證工作區名稱（長度、特殊字符、重複檢查）
  - 提供工作區模板選擇（空白、研究論文、課程筆記等）
  - 支援快捷鍵操作（Ctrl+N 創建、Enter 確認、Escape 取消）
- [ ] 創建後的用戶引導：
  - 自動切換到新創建的工作區
  - 展示歡迎訊息和使用提示
  - 提供快速開始選項（上傳檔案、開始對話等）

#### 3. **工作區設定與管理：**
- [ ] 工作區設定頁面：
  ```typescript
  interface WorkspaceSettingsProps {
    workspace: Workspace;
    onUpdate: (updates: Partial<Workspace>) => void;
    onDelete: () => void;
  }
  ```
  - 重新命名工作區功能
  - 工作區描述和標籤設定
  - 工作區顏色主題選擇
  - 工作區圖示自定義
- [ ] 工作區統計資訊：
  - 檔案數量和總大小
  - 對話次數和總時長
  - 建立時間和最後使用時間
  - 使用頻率統計圖表
- [ ] 工作區操作功能：
  - 複製工作區（復製檔案和設定，不含對話歷史）
  - 匯出工作區資料
  - 刪除工作區（含確認對話框和資料備份選項）

#### 4. **響應式設計與行動端優化：**
- [ ] 桌面端體驗：
  - 側邊欄式工作區選單
  - 支援拖拽排序工作區
  - 支援多選操作（批量刪除、移動等）
- [ ] 平板端體驗：
  - 適應觸控操作的按鈕大小
  - 滑動手勢支援（左滑顯示操作選單）
- [ ] 手機端體驗：
  - 底部標籤式工作區切換器
  - 下拉重新整理支援
  - 簡化的工作區管理選單

---

### 技術實作細節

#### 新增組件：
- `src/components/workspace/WorkspaceSwitcher.tsx` - 主工作區切換器
- `src/components/workspace/WorkspaceDropdown.tsx` - 工作區下拉選單
- `src/components/workspace/CreateWorkspaceModal.tsx` - 創建工作區對話框
- `src/components/workspace/WorkspaceSettings.tsx` - 工作區設定頁面
- `src/components/workspace/WorkspaceCard.tsx` - 工作區卡片組件
- `src/components/workspace/WorkspaceStats.tsx` - 工作區統計組件
- `src/components/workspace/WorkspaceSearch.tsx` - 工作區搜尋組件

#### 新增頁面：
- `src/pages/WorkspaceManagement.tsx` - 工作區管理頁面
- `src/pages/WorkspaceSettings.tsx` - 工作區設定頁面

#### 核心功能實現：

1. **工作區切換器設計**：
   ```typescript
   interface WorkspaceSwitcherProps {
     currentWorkspace: Workspace | null;
     workspaces: Workspace[];
     onWorkspaceSwitch: (workspaceId: string) => void;
     onCreateWorkspace: () => void;
   }
   
   const WorkspaceSwitcher: React.FC<WorkspaceSwitcherProps> = ({
     currentWorkspace,
     workspaces,
     onWorkspaceSwitch,
     onCreateWorkspace
   }) => {
     // 實現工作區切換邏輯
   };
   ```

2. **搜尋和篩選功能**：
   ```typescript
   const useWorkspaceSearch = () => {
     const [searchTerm, setSearchTerm] = useState('');
     const [sortBy, setSortBy] = useState<'name' | 'created' | 'used'>('name');
     
     const filteredWorkspaces = useMemo(() => {
       return workspaces
         .filter(ws => ws.name.toLowerCase().includes(searchTerm.toLowerCase()))
         .sort((a, b) => sortWorkspaces(a, b, sortBy));
     }, [workspaces, searchTerm, sortBy]);
     
     return { searchTerm, setSearchTerm, sortBy, setSortBy, filteredWorkspaces };
   };
   ```

3. **快捷鍵支援**：
   ```typescript
   const useWorkspaceHotkeys = () => {
     useEffect(() => {
       const handleKeyDown = (event: KeyboardEvent) => {
         if (event.ctrlKey || event.metaKey) {
           switch (event.key) {
             case 'n':
               event.preventDefault();
               openCreateWorkspaceModal();
               break;
             case '1':
             case '2':
             // ... 數字鍵快速切換工作區
           }
         }
       };
       
       document.addEventListener('keydown', handleKeyDown);
       return () => document.removeEventListener('keydown', handleKeyDown);
     }, []);
   };
   ```

---

### UI/UX 設計規範

#### 視覺設計：
- [ ] **一致的設計語言**：使用統一的顏色、字體和間距
- [ ] **清晰的視覺層次**：重要資訊突出顯示
- [ ] **直觀的圖示系統**：為不同類型的工作區提供識別圖示
- [ ] **狀態指示**：載入、錯誤、成功狀態的視覺回饋

#### 互動設計：
- [ ] **流暢的動畫**：工作區切換的過渡動畫
- [ ] **即時回饋**：操作結果的即時顯示
- [ ] **錯誤處理**：友善的錯誤訊息和恢復選項
- [ ] **載入狀態**：所有異步操作的載入指示

#### 無障礙設計：
- [ ] **鍵盤導航**：所有功能都可透過鍵盤操作
- [ ] **螢幕閱讀器支援**：適當的 ARIA 標籤和描述
- [ ] **色彩對比**：符合 WCAG 2.1 AA 標準
- [ ] **焦點管理**：清晰的焦點指示和邏輯順序

---

### 效能要求

- [ ] **初始渲染時間**：工作區切換器載入 < 200ms
- [ ] **切換回應時間**：工作區切換操作回饋 < 100ms
- [ ] **搜尋回應時間**：搜尋結果顯示 < 150ms
- [ ] **記憶體使用**：工作區列表組件 < 2MB

---

### 測試要求

#### 單元測試：
- [ ] 工作區切換器組件的所有互動功能
- [ ] 搜尋和篩選邏輯的正確性
- [ ] 快捷鍵處理的準確性
- [ ] 表單驗證邏輯的完整性

#### 整合測試：
- [ ] 工作區創建到切換的完整流程
- [ ] 工作區設定修改的端到端測試
- [ ] 響應式設計在不同裝置上的表現

#### 可用性測試：
- [ ] 新使用者的工作區創建流程測試
- [ ] 多工作區管理的效率測試
- [ ] 無障礙功能的可用性測試

---

### 完成標準 (Definition of Done)

- [ ] 所有驗收標準已達成並通過測試
- [ ] 工作區管理界面在所有支援裝置上正常運作
- [ ] 響應式設計在不同螢幕尺寸下表現良好
- [ ] 無障礙功能通過相關標準檢測
- [ ] 效能指標符合要求
- [ ] UI/UX 設計符合產品設計規範
- [ ] 程式碼覆蓋率 > 80%
- [ ] TypeScript 嚴格模式檢查通過
- [ ] 組件文檔和使用範例已完成

---

### 風險與緩解策略

| 風險項目 | 風險等級 | 緩解策略 |
|:---|:---:|:---|
| 設計複雜度過高 | 中 | 採用漸進式設計，優先實現核心功能 |
| 效能問題 | 中 | 實施虛擬化和懶載入，優化大量工作區的顯示 |
| 無障礙需求 | 低 | 從設計階段開始考慮無障礙需求 |
| 跨瀏覽器相容性 | 低 | 建立完整的瀏覽器測試矩陣 |

---

此任務完成後，使用者將擁有完整且直觀的工作區管理界面，能夠輕鬆地創建、組織和切換工作區，為多工作區工作流程提供良好的使用者體驗基礎。 