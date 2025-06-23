# HI-01: API 契約與前端實作對齊修復指南

## 📋 修復任務概述

- **修復ID**: HI-01
- **優先級**: High 🟡
- **預估工期**: 3-4 天
- **負責團隊**: 前端團隊
- **影響範圍**: 工作區 CRUD 操作、檔案管理、API 服務層

## 🎯 問題定義

### 問題描述
後端已實作完整的工作區 API 端點，但前端尚未完全使用這些新端點，仍在使用舊的非工作區範圍的 API，導致新功能無法正常運作。

### 根本原因分析
1. **API 服務層滯後**: 前端 API 服務層未更新到新的工作區範圍端點
2. **組件依賴舊 API**: 現有組件仍調用舊的 API 端點
3. **類型定義不一致**: TypeScript 類型定義與新 API 格式不匹配
4. **錯誤處理不完整**: 新 API 的錯誤格式和處理邏輯未同步

### API 對齊狀況分析

#### ✅ 後端已實作的 API 端點
```
POST   /api/workspaces/                    # 建立工作區
GET    /api/workspaces/                    # 獲取工作區列表
GET    /api/workspaces/{id}                # 獲取特定工作區
DELETE /api/workspaces/{id}                # 刪除工作區
POST   /api/workspaces/{id}/files/         # 工作區檔案上傳
GET    /api/workspaces/{id}/files/         # 獲取工作區檔案
POST   /api/workspaces/{id}/query/         # 工作區查詢
GET    /api/workspaces/{id}/chats/         # 獲取工作區對話
```

#### ❌ 前端仍使用的舊端點
```
POST   /api/upload                         # 舊檔案上傳
GET    /api/papers                         # 舊檔案列表
POST   /api/query                          # 舊查詢端點
```

## 🔧 詳細修復步驟

### 步驟 1: 更新 TypeScript 類型定義 (1 天)

#### 1.1 建立工作區 API 類型定義

**新檔案**: `src/types/workspace.ts`

```typescript
/**
 * 工作區相關的 TypeScript 類型定義
 */

// 基礎工作區類型
export interface Workspace {
  id: string;
  user_id: string;
  name: string;
  created_at: string;
  updated_at: string;
}

// 工作區建立請求
export interface CreateWorkspaceRequest {
  name: string;
}

// 工作區更新請求
export interface UpdateWorkspaceRequest {
  name?: string;
}

// 工作區統計資訊
export interface WorkspaceStats {
  file_count: number;
  chat_count: number;
  last_activity: string | null;
}

// 工作區詳細資訊
export interface WorkspaceDetail extends Workspace {
  stats: WorkspaceStats;
}

// 工作區檔案類型
export interface WorkspaceFile {
  id: string;
  workspace_id: string;
  filename: string;
  file_size: number;
  upload_date: string;
  processing_status: 'uploading' | 'processing' | 'completed' | 'error';
  file_hash: string;
  selected: boolean;
}

// 檔案上傳回應
export interface FileUploadResponse {
  paper_id: string;
  task_id: string;
  filename: string;
  message: string;
}

// 工作區查詢請求
export interface WorkspaceQueryRequest {
  query: string;
  selected_papers?: string[];
}

// 工作區查詢回應
export interface WorkspaceQueryResponse {
  response: string;
  sources?: Array<{
    paper_id: string;
    filename: string;
    page_number?: number;
    section_type?: string;
  }>;
  chat_id?: string;
}

// 工作區對話類型
export interface WorkspaceChat {
  id: string;
  workspace_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

// API 回應包裝類型
export interface ApiResponse<T> {
  data: T;
  message?: string;
  status: 'success' | 'error';
}

// 錯誤回應類型
export interface ApiError {
  detail: string;
  error_code?: string;
  field_errors?: Record<string, string[]>;
}
```

#### 1.2 更新現有 API 類型

**檔案**: `src/types/api.ts`

```typescript
// 更新現有的 API 類型，加入工作區支援
import { Workspace, WorkspaceFile, WorkspaceChat } from './workspace';

// 更新 User 類型，加入工作區關聯
export interface User {
  id: string;
  google_id: string;
  email: string;
  name: string;
  picture_url?: string;
  created_at: string;
  updated_at: string;
  // 新增工作區關聯
  workspaces?: Workspace[];
}

// 更新檔案類型，支援工作區範圍
export interface PaperFile extends WorkspaceFile {
  // 保持向後相容性
  paper_id: string; // 別名 for id
}

// 更新查詢類型，支援工作區範圍
export interface QueryRequest extends WorkspaceQueryRequest {
  // 保持向後相容性
}

export interface QueryResponse extends WorkspaceQueryResponse {
  // 保持向後相容性
}
```

### 步驟 2: 建立新的工作區 API 服務 (1.5 天)

#### 2.1 建立工作區管理 API 服務

**新檔案**: `src/services/workspaceApiService.ts`

```typescript
/**
 * 工作區管理 API 服務
 */
import { 
  Workspace, 
  CreateWorkspaceRequest, 
  UpdateWorkspaceRequest,
  WorkspaceDetail,
  ApiResponse,
  ApiError 
} from '../types/workspace';
import { apiService } from './api_service';

export class WorkspaceApiService {
  private readonly baseUrl = '/api/workspaces';

  /**
   * 獲取用戶所有工作區
   */
  async getWorkspaces(): Promise<Workspace[]> {
    try {
      const response = await apiService.get<ApiResponse<Workspace[]>>(this.baseUrl);
      return response.data.data;
    } catch (error) {
      console.error('Failed to fetch workspaces:', error);
      throw this.handleApiError(error);
    }
  }

  /**
   * 獲取特定工作區詳細資訊
   */
  async getWorkspace(workspaceId: string): Promise<WorkspaceDetail> {
    try {
      const response = await apiService.get<ApiResponse<WorkspaceDetail>>(
        `${this.baseUrl}/${workspaceId}`
      );
      return response.data.data;
    } catch (error) {
      console.error(`Failed to fetch workspace ${workspaceId}:`, error);
      throw this.handleApiError(error);
    }
  }

  /**
   * 建立新工作區
   */
  async createWorkspace(data: CreateWorkspaceRequest): Promise<Workspace> {
    try {
      const response = await apiService.post<ApiResponse<Workspace>>(
        this.baseUrl,
        data
      );
      return response.data.data;
    } catch (error) {
      console.error('Failed to create workspace:', error);
      throw this.handleApiError(error);
    }
  }

  /**
   * 更新工作區
   */
  async updateWorkspace(
    workspaceId: string, 
    data: UpdateWorkspaceRequest
  ): Promise<Workspace> {
    try {
      const response = await apiService.put<ApiResponse<Workspace>>(
        `${this.baseUrl}/${workspaceId}`,
        data
      );
      return response.data.data;
    } catch (error) {
      console.error(`Failed to update workspace ${workspaceId}:`, error);
      throw this.handleApiError(error);
    }
  }

  /**
   * 刪除工作區
   */
  async deleteWorkspace(workspaceId: string): Promise<void> {
    try {
      await apiService.delete(`${this.baseUrl}/${workspaceId}`);
    } catch (error) {
      console.error(`Failed to delete workspace ${workspaceId}:`, error);
      throw this.handleApiError(error);
    }
  }

  /**
   * 處理 API 錯誤
   */
  private handleApiError(error: any): Error {
    if (error.response?.data) {
      const apiError: ApiError = error.response.data;
      
      // 處理特定錯誤碼
      if (apiError.error_code === 'WORKSPACE_NAME_EXISTS') {
        return new Error('工作區名稱已存在，請選擇其他名稱');
      }
      
      if (apiError.error_code === 'WORKSPACE_NOT_FOUND') {
        return new Error('工作區不存在或您沒有存取權限');
      }
      
      if (apiError.field_errors) {
        const fieldErrors = Object.entries(apiError.field_errors)
          .map(([field, errors]) => `${field}: ${errors.join(', ')}`)
          .join('; ');
        return new Error(`驗證錯誤：${fieldErrors}`);
      }
      
      return new Error(apiError.detail || '工作區操作失敗');
    }
    
    return new Error('網路錯誤，請檢查連線後重試');
  }
}

export const workspaceApiService = new WorkspaceApiService();
```

#### 2.2 建立工作區檔案 API 服務

**新檔案**: `src/services/workspaceFileApiService.ts`

```typescript
/**
 * 工作區檔案管理 API 服務
 */
import { 
  WorkspaceFile, 
  FileUploadResponse,
  ApiResponse 
} from '../types/workspace';
import { apiService } from './api_service';

export interface FileUploadOptions {
  onProgress?: (progress: number) => void;
  onStatusUpdate?: (status: string) => void;
}

export class WorkspaceFileApiService {
  /**
   * 上傳檔案到工作區
   */
  async uploadFile(
    workspaceId: string,
    file: File,
    options?: FileUploadOptions
  ): Promise<FileUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await apiService.post<ApiResponse<FileUploadResponse>>(
        `/api/workspaces/${workspaceId}/files/`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          onUploadProgress: (progressEvent: ProgressEvent) => {
            if (options?.onProgress && progressEvent.total) {
              const progress = Math.round(
                (progressEvent.loaded * 100) / progressEvent.total
              );
              options.onProgress(progress);
            }
          },
        }
      );

      return response.data.data;
    } catch (error) {
      console.error('File upload failed:', error);
      throw this.handleFileError(error);
    }
  }

  /**
   * 獲取工作區檔案列表
   */
  async getFiles(workspaceId: string): Promise<WorkspaceFile[]> {
    try {
      const response = await apiService.get<ApiResponse<WorkspaceFile[]>>(
        `/api/workspaces/${workspaceId}/files/`
      );
      return response.data.data;
    } catch (error) {
      console.error('Failed to fetch files:', error);
      throw this.handleFileError(error);
    }
  }

  /**
   * 選擇/取消選擇檔案
   */
  async selectFiles(workspaceId: string, fileIds: string[]): Promise<void> {
    try {
      await apiService.post(
        `/api/workspaces/${workspaceId}/files/select`,
        { paper_ids: fileIds }
      );
    } catch (error) {
      console.error('Failed to select files:', error);
      throw this.handleFileError(error);
    }
  }

  /**
   * 刪除檔案
   */
  async deleteFile(workspaceId: string, fileId: string): Promise<void> {
    try {
      await apiService.delete(
        `/api/workspaces/${workspaceId}/files/${fileId}`
      );
    } catch (error) {
      console.error('Failed to delete file:', error);
      throw this.handleFileError(error);
    }
  }

  /**
   * 獲取檔案處理狀態
   */
  async getFileStatus(workspaceId: string, fileId: string): Promise<any> {
    try {
      const response = await apiService.get(
        `/api/workspaces/${workspaceId}/files/${fileId}/status`
      );
      return response.data;
    } catch (error) {
      console.error('Failed to get file status:', error);
      throw this.handleFileError(error);
    }
  }

  /**
   * 批次上傳檔案
   */
  async uploadFiles(
    workspaceId: string,
    files: File[],
    options?: FileUploadOptions
  ): Promise<FileUploadResponse[]> {
    const results: FileUploadResponse[] = [];
    
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      
      // 更新整體進度
      if (options?.onStatusUpdate) {
        options.onStatusUpdate(`正在上傳 ${file.name} (${i + 1}/${files.length})`);
      }

      try {
        const result = await this.uploadFile(workspaceId, file, {
          onProgress: (fileProgress) => {
            // 計算整體進度
            const overallProgress = ((i / files.length) * 100) + (fileProgress / files.length);
            options?.onProgress?.(Math.round(overallProgress));
          }
        });
        
        results.push(result);
      } catch (error) {
        console.error(`Failed to upload ${file.name}:`, error);
        // 繼續上傳其他檔案，但記錄錯誤
        throw error;
      }
    }

    return results;
  }

  /**
   * 處理檔案相關錯誤
   */
  private handleFileError(error: any): Error {
    if (error.response?.data?.detail) {
      const detail = error.response.data.detail;
      
      if (detail.includes('file size')) {
        return new Error('檔案大小超過限制（最大 50MB）');
      }
      
      if (detail.includes('file type')) {
        return new Error('檔案格式不支援，請上傳 PDF 檔案');
      }
      
      if (detail.includes('duplicate')) {
        return new Error('檔案已存在於此工作區中');
      }
      
      return new Error(detail);
    }
    
    return new Error('檔案操作失敗，請重試');
  }
}

export const workspaceFileApiService = new WorkspaceFileApiService();
```

### 步驟 3: 更新現有組件使用新 API (1.5 天)

#### 3.1 更新檔案上傳組件

**檔案**: `src/components/file/WorkspaceFileUpload.tsx`

```typescript
/**
 * 更新檔案上傳組件使用新的工作區 API
 */
import React, { useState, useCallback } from 'react';
import { useWorkspaceContext } from '../../contexts/WorkspaceContext';
import { workspaceFileApiService } from '../../services/workspaceFileApiService';
import { FileUploadZone } from './FileUploadZone';
import { ProgressBar } from '../common/ProgressBar';
import { ErrorMessage } from '../common/ErrorMessage';

export const WorkspaceFileUpload: React.FC = () => {
  const { currentWorkspace, refreshWorkspaceFiles } = useWorkspaceContext();
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  const handleFileUpload = useCallback(async (files: File[]) => {
    if (!currentWorkspace) {
      setError('請先選擇工作區');
      return;
    }

    setUploading(true);
    setError(null);
    setProgress(0);

    try {
      if (files.length === 1) {
        // 單檔上傳
        await workspaceFileApiService.uploadFile(
          currentWorkspace.id,
          files[0],
          {
            onProgress: setProgress,
            onStatusUpdate: setStatus
          }
        );
      } else {
        // 批次上傳
        await workspaceFileApiService.uploadFiles(
          currentWorkspace.id,
          files,
          {
            onProgress: setProgress,
            onStatusUpdate: setStatus
          }
        );
      }

      // 上傳成功，刷新檔案列表
      await refreshWorkspaceFiles();
      setStatus('上傳完成！');
      
    } catch (err) {
      console.error('Upload failed:', err);
      setError(err instanceof Error ? err.message : '上傳失敗');
    } finally {
      setUploading(false);
      // 3秒後清除狀態
      setTimeout(() => {
        setProgress(0);
        setStatus('');
      }, 3000);
    }
  }, [currentWorkspace, refreshWorkspaceFiles]);

  if (!currentWorkspace) {
    return (
      <div className="text-center p-8 text-gray-500">
        <p>請先選擇工作區</p>
      </div>
    );
  }

  return (
    <div className="workspace-file-upload">
      <div className="mb-4">
        <h3 className="text-lg font-medium text-gray-900">
          上傳檔案到「{currentWorkspace.name}」
        </h3>
        <p className="text-sm text-gray-600 mt-1">
          支援 PDF 格式，單檔最大 50MB
        </p>
      </div>

      <FileUploadZone
        onFilesSelected={handleFileUpload}
        disabled={uploading}
        multiple={true}
        acceptedTypes={['.pdf']}
        maxFileSize={50 * 1024 * 1024}
      />

      {uploading && (
        <div className="mt-4">
          <ProgressBar progress={progress} />
          {status && (
            <p className="text-sm text-gray-600 mt-2">{status}</p>
          )}
        </div>
      )}

      {error && (
        <div className="mt-4">
          <ErrorMessage 
            message={error} 
            onDismiss={() => setError(null)}
          />
        </div>
      )}
    </div>
  );
};
```

#### 3.2 更新檔案列表組件

**檔案**: `src/components/file/WorkspaceFileList.tsx`

```typescript
/**
 * 更新檔案列表組件使用新的工作區 API
 */
import React, { useEffect, useState, useCallback } from 'react';
import { useWorkspaceContext } from '../../contexts/WorkspaceContext';
import { workspaceFileApiService } from '../../services/workspaceFileApiService';
import { WorkspaceFile } from '../../types/workspace';

export const WorkspaceFileList: React.FC = () => {
  const { currentWorkspace } = useWorkspaceContext();
  const [files, setFiles] = useState<WorkspaceFile[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedFiles, setSelectedFiles] = useState<string[]>([]);

  // 載入檔案列表
  const loadFiles = useCallback(async () => {
    if (!currentWorkspace) return;

    setLoading(true);
    setError(null);

    try {
      const fileList = await workspaceFileApiService.getFiles(currentWorkspace.id);
      setFiles(fileList);
      
      // 設定已選擇的檔案
      const selected = fileList
        .filter(file => file.selected)
        .map(file => file.id);
      setSelectedFiles(selected);
      
    } catch (err) {
      console.error('Failed to load files:', err);
      setError(err instanceof Error ? err.message : '載入檔案失敗');
    } finally {
      setLoading(false);
    }
  }, [currentWorkspace]);

  // 工作區變更時重新載入
  useEffect(() => {
    loadFiles();
  }, [loadFiles]);

  // 檔案選擇處理
  const handleFileSelection = useCallback(async (fileIds: string[]) => {
    if (!currentWorkspace) return;

    try {
      await workspaceFileApiService.selectFiles(currentWorkspace.id, fileIds);
      setSelectedFiles(fileIds);
      
      // 更新本地狀態
      setFiles(prev => prev.map(file => ({
        ...file,
        selected: fileIds.includes(file.id)
      })));
      
    } catch (err) {
      console.error('Failed to select files:', err);
      setError(err instanceof Error ? err.message : '選擇檔案失敗');
    }
  }, [currentWorkspace]);

  // 刪除檔案
  const handleDeleteFile = useCallback(async (fileId: string) => {
    if (!currentWorkspace) return;

    if (!confirm('確定要刪除此檔案嗎？')) return;

    try {
      await workspaceFileApiService.deleteFile(currentWorkspace.id, fileId);
      
      // 更新本地狀態
      setFiles(prev => prev.filter(file => file.id !== fileId));
      setSelectedFiles(prev => prev.filter(id => id !== fileId));
      
    } catch (err) {
      console.error('Failed to delete file:', err);
      setError(err instanceof Error ? err.message : '刪除檔案失敗');
    }
  }, [currentWorkspace]);

  if (!currentWorkspace) {
    return (
      <div className="text-center p-8 text-gray-500">
        <p>請先選擇工作區</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="text-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
        <p className="text-gray-600 mt-2">載入檔案中...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center p-8">
        <p className="text-red-600 mb-4">{error}</p>
        <button 
          onClick={loadFiles}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          重試
        </button>
      </div>
    );
  }

  return (
    <div className="workspace-file-list">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-medium text-gray-900">
          檔案列表 ({files.length})
        </h3>
        <button 
          onClick={loadFiles}
          className="text-sm text-blue-600 hover:text-blue-800"
        >
          重新整理
        </button>
      </div>

      {files.length === 0 ? (
        <div className="text-center p-8 text-gray-500">
          <p>此工作區尚無檔案</p>
          <p className="text-sm mt-1">請上傳 PDF 檔案開始分析</p>
        </div>
      ) : (
        <FileListTable
          files={files}
          selectedFiles={selectedFiles}
          onSelectionChange={handleFileSelection}
          onDeleteFile={handleDeleteFile}
        />
      )}
    </div>
  );
};
```

### 步驟 4: 建立 API 遷移層 (0.5 天)

#### 4.1 建立向後相容性適配器

**新檔案**: `src/services/apiMigrationAdapter.ts`

```typescript
/**
 * API 遷移適配器
 * 提供舊 API 到新 API 的平滑遷移
 */
import { workspaceFileApiService } from './workspaceFileApiService';
import { workspaceQueryApiService } from './workspaceQueryApiService';
import { useWorkspaceContext } from '../contexts/WorkspaceContext';

/**
 * 舊 API 適配器
 * 將舊的 API 調用轉換為新的工作區範圍 API
 */
export class LegacyApiAdapter {
  private getCurrentWorkspaceId(): string {
    const { currentWorkspace } = useWorkspaceContext();
    if (!currentWorkspace) {
      throw new Error('No workspace selected. Please select a workspace first.');
    }
    return currentWorkspace.id;
  }

  // 適配舊的檔案上傳 API
  async uploadFile(file: File, onProgress?: (progress: number) => void) {
    const workspaceId = this.getCurrentWorkspaceId();
    return workspaceFileApiService.uploadFile(workspaceId, file, { onProgress });
  }

  // 適配舊的檔案列表 API
  async getPapers() {
    const workspaceId = this.getCurrentWorkspaceId();
    return workspaceFileApiService.getFiles(workspaceId);
  }

  // 適配舊的查詢 API
  async submitQuery(query: string) {
    const workspaceId = this.getCurrentWorkspaceId();
    return workspaceQueryApiService.submitQuery(workspaceId, { query });
  }

  // 適配舊的檔案選擇 API
  async selectPapers(paperIds: string[]) {
    const workspaceId = this.getCurrentWorkspaceId();
    return workspaceFileApiService.selectFiles(workspaceId, paperIds);
  }
}

export const legacyApiAdapter = new LegacyApiAdapter();

/**
 * 漸進式遷移 Hook
 * 允許組件逐步從舊 API 遷移到新 API
 */
export const useMigratedApi = () => {
  const { currentWorkspace } = useWorkspaceContext();
  
  return {
    // 檔案相關 API
    uploadFile: (file: File, options?: any) => {
      if (!currentWorkspace) throw new Error('No workspace selected');
      return workspaceFileApiService.uploadFile(currentWorkspace.id, file, options);
    },
    
    getFiles: () => {
      if (!currentWorkspace) throw new Error('No workspace selected');
      return workspaceFileApiService.getFiles(currentWorkspace.id);
    },
    
    selectFiles: (fileIds: string[]) => {
      if (!currentWorkspace) throw new Error('No workspace selected');
      return workspaceFileApiService.selectFiles(currentWorkspace.id, fileIds);
    },
    
    deleteFile: (fileId: string) => {
      if (!currentWorkspace) throw new Error('No workspace selected');
      return workspaceFileApiService.deleteFile(currentWorkspace.id, fileId);
    },
    
    // 查詢相關 API
    submitQuery: (query: string) => {
      if (!currentWorkspace) throw new Error('No workspace selected');
      return workspaceQueryApiService.submitQuery(currentWorkspace.id, { query });
    },
    
    // 工作區資訊
    currentWorkspaceId: currentWorkspace?.id || null,
    hasWorkspace: !!currentWorkspace
  };
};
```

## 🧪 測試驗證計劃

### 單元測試

#### API 服務測試
```typescript
// src/__tests__/services/workspaceApiService.test.ts
describe('WorkspaceApiService', () => {
  test('should create workspace successfully', async () => {
    const mockWorkspace = { name: 'Test Workspace' };
    const result = await workspaceApiService.createWorkspace(mockWorkspace);
    expect(result.name).toBe('Test Workspace');
  });

  test('should handle duplicate name error', async () => {
    // 測試重複名稱錯誤處理
  });
});
```

#### 檔案 API 服務測試
```typescript
// src/__tests__/services/workspaceFileApiService.test.ts
describe('WorkspaceFileApiService', () => {
  test('should upload file to workspace', async () => {
    const mockFile = new File(['test'], 'test.pdf', { type: 'application/pdf' });
    const result = await workspaceFileApiService.uploadFile('workspace-id', mockFile);
    expect(result.filename).toBe('test.pdf');
  });
});
```

### 整合測試

#### API 對齊測試
```typescript
// src/__tests__/integration/apiAlignment.test.ts
describe('API Alignment', () => {
  test('should use new workspace APIs instead of legacy APIs', async () => {
    // 驗證新組件使用正確的 API 端點
  });

  test('should handle workspace context correctly', async () => {
    // 驗證工作區上下文的正確使用
  });
});
```

### 端到端測試

```typescript
// cypress/integration/api-migration.spec.ts
describe('API Migration', () => {
  it('should use workspace-scoped APIs', () => {
    cy.login();
    cy.selectWorkspace('Test Workspace');
    
    // 檔案上傳應使用新 API
    cy.intercept('POST', '/api/workspaces/*/files/', { fixture: 'upload-success.json' }).as('uploadFile');
    
    cy.uploadFile('test.pdf');
    cy.wait('@uploadFile');
    
    // 檔案列表應使用新 API
    cy.intercept('GET', '/api/workspaces/*/files/', { fixture: 'files.json' }).as('getFiles');
    cy.wait('@getFiles');
  });
});
```

## 📋 驗收標準

### 功能驗收
- [ ] 所有檔案操作使用工作區範圍的 API
- [ ] 查詢操作使用工作區範圍的 API
- [ ] 工作區管理功能完整可用
- [ ] 錯誤處理友善且準確
- [ ] 向後相容性適配器正常運作

### 技術驗收
- [ ] TypeScript 類型完整且正確
- [ ] API 服務層架構清晰
- [ ] 錯誤處理統一且健全
- [ ] 單元測試覆蓋率 > 85%
- [ ] 無使用舊的 API 端點

### 效能驗收
- [ ] API 回應時間在可接受範圍
- [ ] 批次操作效能良好
- [ ] 記憶體使用正常
- [ ] 網路錯誤恢復機制有效

## 📅 實施時程

### Day 1: 類型定義與基礎服務
- 建立 TypeScript 類型定義
- 創建工作區 API 服務基礎結構

### Day 2: 檔案 API 服務
- 完成檔案管理 API 服務
- 單元測試

### Day 3: 組件更新
- 更新檔案上傳和列表組件
- 整合測試

### Day 4: 適配器與測試
- 建立向後相容性適配器
- 端到端測試和優化

## 🔗 相關文檔
- [BE-02: 建立工作區管理 API](../backlog/backend/BE-02_create_workspace_crud_api.md)
- [CI-01: 核心業務流程整合修復指南](./CI-01_核心業務流程整合修復指南.md)

## 📋 檢查清單

### 開發前準備
- [ ] 確認後端 API 端點的完整性和穩定性
- [ ] 準備測試數據和模擬回應
- [ ] 設定 API 測試環境

### 開發中檢查
- [ ] 定期測試 API 服務功能
- [ ] 驗證 TypeScript 類型正確性
- [ ] 檢查錯誤處理路徑
- [ ] 確認與工作區上下文的正確整合

### 完成後驗證
- [ ] 所有新 API 服務通過測試
- [ ] 組件成功遷移到新 API
- [ ] 向後相容性適配器運作正常
- [ ] 端到端流程測試通過 