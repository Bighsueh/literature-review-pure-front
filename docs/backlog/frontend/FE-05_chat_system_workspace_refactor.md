# Backlog: FE-05 - 對話系統工作區化重構

- **Epic:** 前端 UX 重構
- **狀態:** To Do
- **優先級:** High
- **估算 (Story Points):** 8
- **依賴:** FE-02 (多工作區狀態管理), BE-05 (對話API已重構)

---

### 使用者故事 (User Story)

**身為** 一位研究人員，
**我想要** 在每個工作區中擁有獨立的AI對話歷史，能夠基於該工作區的檔案進行查詢和分析，
**以便** 我可以為每個研究專案維持專門的對話脈絡，並且不同專案的對話內容不會混淆。

---

### 驗收標準 (Acceptance Criteria)

#### 1. **工作區化對話狀態管理：**
- [ ] 對話狀態完全工作區隔離：
  ```typescript
  interface WorkspaceChatState {
    conversations: Record<string, Conversation[]>; // 按工作區ID分組
    currentConversation: Record<string, string | null>; // 每個工作區的當前對話
    isLoading: Record<string, boolean>;
    
    createConversation: (workspaceId: string, title?: string) => string;
    switchConversation: (workspaceId: string, conversationId: string) => void;
    sendMessage: (workspaceId: string, conversationId: string, message: string) => Promise<void>;
    deleteConversation: (workspaceId: string, conversationId: string) => void;
  }
  ```
- [ ] 對話歷史持久化：
  - 使用工作區範圍的本地儲存 keys
  - 工作區切換時自動載入對應的對話歷史
  - 對話資料的增量同步和快取策略

#### 2. **工作區範圍的AI查詢：**
- [ ] 查詢功能整合工作區：
  - 使用新的 API 端點：`POST /api/workspaces/{id}/query`
  - 查詢自動限制在當前工作區的檔案範圍內
  - 查詢結果和引用來源都限制在工作區內
- [ ] 智慧查詢建議：
  - 基於工作區檔案內容提供查詢建議
  - 顯示可查詢的主題和概念
  - 工作區檔案變更時更新查詢建議
- [ ] 查詢結果優化：
  - 引用來源顯示檔案所屬工作區
  - 支援在工作區內的跨文檔查詢
  - 查詢歷史記錄按工作區分組

#### 3. **對話界面重構：**
- [ ] 對話列表組件改造：
  ```typescript
  interface WorkspaceConversationListProps {
    workspaceId: string;
    conversations: Conversation[];
    currentConversationId: string | null;
    onConversationSelect: (conversationId: string) => void;
    onConversationCreate: () => void;
    onConversationDelete: (conversationId: string) => void;
  }
  ```
- [ ] 訊息組件增強：
  - 支援工作區範圍的引用顯示
  - 訊息中的檔案引用點擊跳轉到該檔案
  - 支援訊息的書籤和標註功能
- [ ] 對話搜尋功能：
  - 在當前工作區內搜尋對話歷史
  - 支援按時間、關鍵字、引用檔案篩選
  - 快速定位相關對話和訊息

#### 4. **對話管理功能：**
- [ ] 對話組織功能：
  - 對話重新命名和分類
  - 對話標籤和顏色標記
  - 對話導出和分享
- [ ] 對話模板系統：
  - 預設查詢模板（文獻回顧、比較分析等）
  - 工作區特定的查詢模板
  - 自定義模板創建和管理
- [ ] 對話統計和分析：
  - 顯示對話次數和使用時間
  - 分析最常討論的主題
  - 查詢效果和滿意度統計

---

### 技術實作細節

#### 重構的組件：
- `src/components/chat/ChatMessageList/ChatMessageList.tsx` - 工作區化訊息列表
- `src/components/chat/ChatInput/ChatInput.tsx` - 工作區化輸入組件
- `src/components/chat/MessageBubble/MessageBubble.tsx` - 增強引用顯示
- `src/components/chat/SourceSummary/SourceSummary.tsx` - 工作區範圍引用

#### 新增組件：
- `src/components/chat/WorkspaceConversationList.tsx` - 工作區對話列表
- `src/components/chat/ConversationSearch.tsx` - 對話搜尋組件
- `src/components/chat/QueryTemplates.tsx` - 查詢模板組件
- `src/components/chat/ConversationStats.tsx` - 對話統計組件

#### 重構的 Store：
- `src/stores/chatStore.ts` - 完全重構為工作區化
- `src/hooks/useQueryProcessor.ts` - 適配工作區化API

#### 核心功能實現：

1. **工作區化對話管理**：
   ```typescript
   const useWorkspaceChat = (workspaceId: string) => {
     const [conversations, setConversations] = useState<Conversation[]>([]);
     const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
     
     const createConversation = useCallback((title?: string) => {
       const newConversation: Conversation = {
         id: generateId(),
         workspaceId,
         title: title || `對話 ${conversations.length + 1}`,
         messages: [],
         createdAt: new Date(),
         updatedAt: new Date()
       };
       
       setConversations(prev => [...prev, newConversation]);
       setCurrentConversationId(newConversation.id);
       
       return newConversation.id;
     }, [workspaceId, conversations.length]);
     
     return {
       conversations,
       currentConversationId,
       createConversation,
       // ... 其他方法
     };
   };
   ```

2. **智慧查詢系統**：
   ```typescript
   const useWorkspaceQuery = (workspaceId: string) => {
     const [isQuerying, setIsQuerying] = useState(false);
     const [suggestions, setSuggestions] = useState<string[]>([]);
     
     const executeQuery = useCallback(async (query: string, conversationId: string) => {
       setIsQuerying(true);
       try {
         const response = await apiService.queryWorkspace(workspaceId, {
           query,
           conversationId,
           includeHistory: true
         });
         
         return response;
       } finally {
         setIsQuerying(false);
       }
     }, [workspaceId]);
     
     return { executeQuery, isQuerying, suggestions };
   };
   ```

3. **對話同步機制**：
   ```typescript
   const useConversationSync = (workspaceId: string) => {
     const { data: conversations, mutate } = useSWR(
       ['workspace-conversations', workspaceId],
       () => apiService.getWorkspaceConversations(workspaceId),
       {
         revalidateOnFocus: false,
         revalidateOnReconnect: true,
         dedupingInterval: 5000
       }
     );
     
     const syncConversation = useCallback(async (conversationId: string) => {
       await mutate();
     }, [mutate]);
     
     return { conversations, syncConversation };
   };
   ```

---

### 與後端API整合

#### API端點映射：
- `GET /api/workspaces/{id}/chats` - 獲取工作區對話列表
- `POST /api/workspaces/{id}/chats` - 創建新對話
- `GET /api/workspaces/{id}/chats/{chatId}` - 獲取對話詳情
- `POST /api/workspaces/{id}/query` - 工作區範圍查詢
- `DELETE /api/workspaces/{id}/chats/{chatId}` - 刪除對話

#### 即時通訊支援：
- [ ] WebSocket 連接管理（按工作區分組）
- [ ] 查詢進度的即時回饋
- [ ] 對話狀態的即時同步
- [ ] 連線中斷時的自動重連機制

---

### UI/UX 設計優化

#### 對話體驗改進：
- [ ] **串流式回應**：AI回應的逐字顯示
- [ ] **輸入增強**：自動完成、建議查詢、快捷指令
- [ ] **引用互動**：點擊引用跳轉到原文、引用預覽
- [ ] **對話導航**：對話摘要、快速跳轉、相關對話推薦

#### 響應式設計：
- [ ] **桌面端**：分欄對話界面，支援並排顯示
- [ ] **平板端**：滑動切換對話，觸控優化
- [ ] **手機端**：全屏對話，簡化的操作界面

#### 可用性增強：
- [ ] **鍵盤快捷鍵**：快速發送、新對話、搜尋等
- [ ] **無障礙支援**：螢幕閱讀器友善、鍵盤導航
- [ ] **多語言支援**：界面本地化、智慧語言檢測

---

### 效能優化

#### 對話載入優化：
- [ ] **虛擬滾動**：處理長對話歷史
- [ ] **分頁載入**：按需載入對話訊息
- [ ] **智慧預載入**：預載入相關對話

#### 記憶體管理：
- [ ] **對話清理**：自動清理舊對話的快取
- [ ] **資料壓縮**：壓縮對話歷史儲存
- [ ] **懶載入**：延遲載入非當前對話

---

### 測試要求

#### 單元測試：
- [ ] 對話狀態管理邏輯
- [ ] 查詢處理和結果解析
- [ ] 工作區隔離機制
- [ ] 本地儲存同步邏輯

#### 整合測試：
- [ ] 完整的查詢對話流程
- [ ] 工作區切換時的對話隔離
- [ ] 即時通訊功能測試

#### 使用者體驗測試：
- [ ] 對話流暢度測試
- [ ] 查詢回應時間測試
- [ ] 多工作區使用情境測試

---

### 完成標準 (Definition of Done)

- [ ] 所有驗收標準已達成並通過測試
- [ ] 對話功能在多工作區環境下完全隔離
- [ ] AI查詢限制在工作區範圍內且結果準確
- [ ] 對話界面在所有支援裝置上流暢運作
- [ ] 效能指標符合要求（查詢回應 < 3s，對話載入 < 1s）
- [ ] 程式碼覆蓋率 > 80%
- [ ] TypeScript 嚴格模式檢查通過
- [ ] 對話功能文檔已更新

---

### 風險與緩解策略

| 風險項目 | 風險等級 | 緩解策略 |
|:---|:---:|:---|
| 對話歷史資料遷移 | 中 | 建立完整的資料遷移和備份策略 |
| AI查詢回應時間 | 中 | 實施查詢快取和回應優化 |
| 工作區間資料洩漏 | 高 | 嚴格的隔離測試和安全審查 |
| 即時通訊穩定性 | 中 | 建立可靠的重連機制和錯誤處理 |

---

此任務完成後，使用者將擁有功能完整的工作區化AI對話系統，能夠在每個工作區中進行專門的研究討論，維持清晰的對話脈絡，大幅提升研究工作的組織性和效率。 