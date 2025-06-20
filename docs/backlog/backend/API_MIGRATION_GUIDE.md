# API 遷移指南

**文檔版本**: v1.0  
**創建日期**: 2024-12-19  
**目標讀者**: 前端開發者、API 消費者  
**遷移時程**: 3 週內完成，6 個月過渡期

---

## 📋 遷移概覽

本指南詳細說明從舊有 API 端點遷移到新的工作區化 API 端點的過程。新的 API 架構實現了工作區多租戶隔離，提升了數據安全性和用戶體驗。

### 遷移原則
1. **向後兼容**: 舊端點將保留 6 個月過渡期
2. **漸進式遷移**: 可以逐步遷移，不需要一次性更改所有端點
3. **功能對等**: 新端點提供相同或更好的功能
4. **數據隔離**: 新端點實現完整的工作區數據隔離

---

## 🔄 端點遷移對照表

### **檔案上傳相關 API**

| 功能 | 舊端點 | 新端點 | 狀態 | 備註 |
|------|--------|--------|------|------|
| 檔案上傳 | `POST /api/upload` | `POST /api/workspaces/{workspace_id}/files` | 🔄 遷移中 | 需要工作區授權 |
| 批次上傳 | `POST /api/upload/batch` | `POST /api/workspaces/{workspace_id}/files/batch` | 🔄 遷移中 | 支援工作區隔離 |
| 上傳資訊 | `GET /api/upload/info` | `GET /api/workspaces/{workspace_id}/files/upload-info` | 🔄 遷移中 | 工作區特定配置 |
| 清理檔案 | `POST /api/upload/cleanup` | `POST /api/workspaces/{workspace_id}/files/cleanup` | 🔄 遷移中 | 限制工作區範圍 |
| 刪除檔案 | `DELETE /api/upload/{paper_id}` | `DELETE /api/workspaces/{workspace_id}/files/{file_id}` | 🔄 遷移中 | 工作區權限檢查 |

### **檔案管理相關 API**

| 功能 | 舊端點 | 新端點 | 狀態 | 備註 |
|------|--------|--------|------|------|
| 檔案列表 | `GET /api/papers` | `GET /api/workspaces/{workspace_id}/files` | 🔄 遷移中 | 支援分頁和過濾 |
| 檔案詳情 | `GET /api/papers/{id}` | `GET /api/workspaces/{workspace_id}/files/{id}` | 🔄 遷移中 | 工作區權限檢查 |
| 刪除檔案 | `DELETE /api/papers/{id}` | `DELETE /api/workspaces/{workspace_id}/files/{id}` | 🔄 遷移中 | 工作區範圍刪除 |
| 已選檔案 | `GET /api/papers/selected` | `GET /api/workspaces/{workspace_id}/files/selected` | 🔄 遷移中 | 工作區隔離 |
| 章節摘要 | `GET /api/papers/sections_summary` | `GET /api/workspaces/{workspace_id}/files/sections-summary` | 🔄 遷移中 | 工作區範圍統計 |
| 全選檔案 | `POST /api/papers/select_all` | `POST /api/workspaces/{workspace_id}/files/select-all` | 🔄 遷移中 | 限制工作區範圍 |
| 取消全選 | `POST /api/papers/deselect_all` | `POST /api/workspaces/{workspace_id}/files/deselect-all` | 🔄 遷移中 | 限制工作區範圍 |
| 批次選取 | `POST /api/papers/batch-select` | `POST /api/workspaces/{workspace_id}/files/batch-select` | 🔄 遷移中 | 工作區範圍操作 |

### **查詢相關 API**

| 功能 | 舊端點 | 新端點 | 狀態 | 備註 |
|------|--------|--------|------|------|
| 查詢處理 | `POST /api/papers/query/process` | `POST /api/workspaces/{workspace_id}/query` | 🔄 遷移中 | 限制工作區範圍 |
| 統一查詢 | `POST /api/papers/unified-query` | `POST /api/workspaces/{workspace_id}/query/unified` | 🔄 遷移中 | 工作區隔離查詢 |
| 測試查詢 | `POST /api/papers/test-unified-query` | `POST /api/workspaces/{workspace_id}/query/test` | 🔄 遷移中 | 開發環境使用 |

### **對話歷史 API**

| 功能 | 舊端點 | 新端點 | 狀態 | 備註 |
|------|--------|--------|------|------|
| 對話列表 | ❌ 不存在 | `GET /api/workspaces/{workspace_id}/chats` | ✅ 已完成 | 新功能，支援分頁 |
| 刪除對話 | ❌ 不存在 | `DELETE /api/workspaces/{workspace_id}/chats/{chat_id}` | ✅ 已完成 | 新功能 |
| 清空對話 | ❌ 不存在 | `DELETE /api/workspaces/{workspace_id}/chats` | ✅ 已完成 | 新功能 |

### **保持不變的 API**

| 功能 | 端點 | 狀態 | 備註 |
|------|------|------|------|
| 身份驗證 | `POST /api/auth/google/callback` | ✅ 無需更改 | 全域功能 |
| 令牌刷新 | `POST /api/auth/refresh` | ✅ 無需更改 | 全域功能 |
| 用戶資訊 | `GET /api/auth/me` | ✅ 無需更改 | 全域功能 |
| 工作區管理 | `GET /api/workspaces/` | ✅ 無需更改 | 已經工作區化 |
| 遺留資料 | `GET /api/legacy/papers` | ✅ 無需更改 | 新功能 |
| 健康檢查 | `GET /api/health` | ✅ 無需更改 | 系統功能 |

---

## 🔧 前端遷移步驟

### **第一步：安裝工作區狀態管理**

```typescript
// src/types/workspace.ts
export interface Workspace {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
}

// src/stores/workspaceStore.ts
import { create } from 'zustand';
import { Workspace } from '../types/workspace';

interface WorkspaceState {
  currentWorkspace: Workspace | null;
  workspaces: Workspace[];
  setCurrentWorkspace: (workspace: Workspace) => void;
  setWorkspaces: (workspaces: Workspace[]) => void;
}

export const useWorkspaceStore = create<WorkspaceState>((set) => ({
  currentWorkspace: null,
  workspaces: [],
  setCurrentWorkspace: (workspace) => set({ currentWorkspace: workspace }),
  setWorkspaces: (workspaces) => set({ workspaces }),
}));
```

### **第二步：更新 API 服務層**

```typescript
// src/services/api.ts - 更新檔案管理 API
class ApiService {
  // 新的工作區化端點
  async getWorkspaceFiles(workspaceId: string, params?: PaginationParams) {
    return this.get(`/api/workspaces/${workspaceId}/files`, { params });
  }

  async uploadFileToWorkspace(workspaceId: string, file: File) {
    const formData = new FormData();
    formData.append('file', file);
    return this.post(`/api/workspaces/${workspaceId}/files`, formData);
  }

  async queryInWorkspace(workspaceId: string, query: string) {
    return this.post(`/api/workspaces/${workspaceId}/query`, { query });
  }

  // 向後兼容的舊端點（標記為棄用）
  /** @deprecated 使用 getWorkspaceFiles 替代 */
  async getFiles() {
    console.warn('⚠️ getFiles() 已棄用，請使用 getWorkspaceFiles()');
    return this.get('/api/papers');
  }

  /** @deprecated 使用 uploadFileToWorkspace 替代 */
  async uploadFile(file: File) {
    console.warn('⚠️ uploadFile() 已棄用，請使用 uploadFileToWorkspace()');
    const formData = new FormData();
    formData.append('file', file);
    return this.post('/api/upload', formData);
  }
}
```

### **第三步：實現漸進式遷移**

```typescript
// src/services/apiMigration.ts - 遷移助手
export class ApiMigrationHelper {
  private static instance: ApiMigrationHelper;
  private isNewApiEnabled = true; // 功能旗標

  static getInstance() {
    if (!this.instance) {
      this.instance = new ApiMigrationHelper();
    }
    return this.instance;
  }

  // 智能路由：自動選擇新舊端點
  async getFiles(workspaceId?: string) {
    if (this.isNewApiEnabled && workspaceId) {
      return api.getWorkspaceFiles(workspaceId);
    } else {
      return api.getFiles(); // 回退到舊端點
    }
  }

  async uploadFile(file: File, workspaceId?: string) {
    try {
      if (this.isNewApiEnabled && workspaceId) {
        return await api.uploadFileToWorkspace(workspaceId, file);
      }
    } catch (error) {
      console.warn('新端點失敗，回退到舊端點:', error);
      return api.uploadFile(file);
    }
  }
}
```

### **第四步：更新 React 組件**

```tsx
// src/components/FileUpload.tsx - 檔案上傳組件更新
import { useWorkspaceStore } from '../stores/workspaceStore';

export const FileUpload: React.FC = () => {
  const { currentWorkspace } = useWorkspaceStore();
  const migrationHelper = ApiMigrationHelper.getInstance();

  const handleFileUpload = async (file: File) => {
    try {
      if (!currentWorkspace) {
        throw new Error('請選擇工作區');
      }

      const result = await migrationHelper.uploadFile(file, currentWorkspace.id);
      console.log('檔案上傳成功:', result);
    } catch (error) {
      console.error('檔案上傳失敗:', error);
    }
  };

  return (
    <div>
      {!currentWorkspace && (
        <div className="warning">⚠️ 請先選擇工作區</div>
      )}
      <input 
        type="file" 
        onChange={(e) => e.target.files?.[0] && handleFileUpload(e.target.files[0])}
        disabled={!currentWorkspace}
      />
    </div>
  );
};
```

---

## 🔐 授權機制變更

### **舊授權模式**
```http
# 舊方式：僅需要 JWT 令牌
Authorization: Bearer <jwt_token>
```

### **新授權模式**
```http
# 新方式：JWT 令牌 + 工作區權限檢查
Authorization: Bearer <jwt_token>
# 系統會自動驗證用戶對指定 workspace_id 的存取權限
```

### **權限檢查流程**
1. **JWT 驗證**: 驗證令牌有效性和用戶身份
2. **工作區驗證**: 檢查用戶是否擁有指定工作區的存取權限
3. **資源隔離**: 確保所有操作限制在用戶有權存取的工作區內

---

## 📊 回應格式變更

### **分頁回應格式**

```json
// 舊格式：簡單陣列
[
  { "id": "1", "name": "file1.pdf" },
  { "id": "2", "name": "file2.pdf" }
]

// 新格式：包含分頁中繼資料
{
  "items": [
    { "id": "1", "name": "file1.pdf", "workspace_id": "ws-123" },
    { "id": "2", "name": "file2.pdf", "workspace_id": "ws-123" }
  ],
  "meta": {
    "page": 1,
    "size": 50,
    "total": 120,
    "total_pages": 3,
    "has_next": true,
    "has_previous": false
  }
}
```

### **錯誤回應格式**

```json
// 新的標準化錯誤格式 (RFC 7807)
{
  "type": "https://api.example.com/errors/workspace-access-denied",
  "title": "Workspace Access Denied",
  "status": 403,
  "detail": "You don't have permission to access workspace ws-123",
  "instance": "/api/workspaces/ws-123/files",
  "error_code": "WORKSPACE_ACCESS_DENIED",
  "timestamp": "2024-12-19T10:30:00Z"
}
```

---

## ⚠️ 重要注意事項

### **破壞性變更**
1. **必需參數**: 所有新端點都需要 `workspace_id` 參數
2. **授權要求**: 需要同時具備 JWT 令牌和工作區存取權限
3. **分頁格式**: 列表端點回應格式已變更
4. **錯誤格式**: 錯誤回應採用 RFC 7807 標準格式

### **資料遷移**
- 現有檔案將自動關聯到用戶的預設工作區
- 遺留資料可通過 `/api/legacy/papers` 端點存取和導入
- 查詢歷史將保留，但需要重新關聯到工作區

### **性能考量**
- 新端點實現了更好的資料隔離，可能影響快取策略
- 分頁機制可提升大量資料的載入性能
- 工作區範圍的查詢可減少不必要的資料傳輸

---

## 📅 遷移時程表

### **第 1 週 (2024-12-19 - 2024-12-25)**
- [ ] 後端新端點開發完成
- [ ] 舊端點標記為棄用但保持功能
- [ ] 基本測試完成

### **第 2 週 (2024-12-26 - 2025-01-01)** 
- [ ] 前端 API 服務層更新
- [ ] 實現工作區狀態管理
- [ ] 漸進式遷移機制實現

### **第 3 週 (2025-01-02 - 2025-01-08)**
- [ ] React 組件更新完成
- [ ] 端到端測試通過
- [ ] 用戶驗收測試完成

### **第 4-26 週 (過渡期)**
- [ ] 監控舊端點使用情況
- [ ] 逐步引導用戶使用新端點
- [ ] 性能和穩定性監控

### **第 26 週後**
- [ ] 舊端點正式停用
- [ ] 清理舊代碼
- [ ] 完成文檔更新

---

## 🛠️ 開發工具和助手

### **VS Code 片段**
```json
// .vscode/snippets/api-migration.json
{
  "Workspace API Call": {
    "prefix": "wapi",
    "body": [
      "const result = await api.${1:method}(${2:workspaceId}, ${3:params});",
      "if (!result.success) {",
      "  console.error('API call failed:', result.error);",
      "  return;",
      "}",
      "console.log('API result:', result.data);"
    ],
    "description": "工作區 API 呼叫模板"
  }
}
```

### **TypeScript 類型定義**
```typescript
// src/types/api.ts
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: ApiError;
}

export interface PaginatedResponse<T> {
  items: T[];
  meta: PaginationMeta;
}

export interface PaginationMeta {
  page: number;
  size: number;
  total: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface ApiError {
  type: string;
  title: string;
  status: number;
  detail: string;
  error_code: string;
  timestamp: string;
}
```

---

## 📞 支援和協助

### **遷移支援**
- **技術支援**: [技術團隊聯絡方式]
- **文檔更新**: [文檔維護者聯絡方式]
- **緊急支援**: [緊急聯絡方式]

### **常見問題**
- **Q**: 如何獲取用戶的工作區列表？
- **A**: 使用 `GET /api/workspaces/` 端點

- **Q**: 工作區 ID 在哪裡獲取？
- **A**: 從工作區列表 API 或前端狀態管理中獲取

- **Q**: 舊端點什麼時候會停用？
- **A**: 預計 6 個月後（2025 年 6 月）正式停用

### **遷移檢查清單**
- [ ] 更新所有檔案上傳相關的 API 呼叫
- [ ] 更新所有檔案管理相關的 API 呼叫
- [ ] 更新所有查詢相關的 API 呼叫
- [ ] 實現工作區選擇器
- [ ] 添加工作區狀態管理
- [ ] 更新錯誤處理邏輯
- [ ] 測試所有功能在新端點下正常工作
- [ ] 移除舊端點的呼叫

---

**文檔更新記錄**:
- v1.0 (2024-12-19): 初始版本
- 下次審查日期: 2024-12-26 