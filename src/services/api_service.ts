/**
 * 統一 API 服務層 - 重構版本
 * 負責所有與後端 API 的通訊，完全整合工作區化系統
 * 
 * 狀態：REFACTORED - 移除緊急模式，完全使用工作區化 API
 */

export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

// 工作區相關類型定義
export interface Workspace {
  id: string;
  name: string;
  description?: string;
  created_at: string;
  updated_at: string;
  owner_id: string;
  is_active: boolean;
}

export interface WorkspaceFile {
  id: string;
  workspace_id: string;
  title: string;
  original_filename: string;
  file_path: string;
  file_hash: string;
  file_size: number;
  upload_time: string;
  processing_status: 'pending' | 'processing' | 'completed' | 'failed';
  selected: boolean;
  section_count: number;
  sentence_count: number;
}

// 重新命名舊的介面避免混淆
export interface LegacyPaperInfo {
  id: string;
  title: string;
  authors?: string[];
  file_path: string;
  file_hash: string;
  upload_time: string;
  processing_status: 'pending' | 'processing' | 'completed' | 'failed';
  selected: boolean;
  section_count: number;
  sentence_count: number;
}

export interface ProcessingStatus {
  current_stage: string;
  percentage: number;
  details: Record<string, unknown>;
  is_processing: boolean;
  error: string | null;
}

export interface TaskStatus {
  task_id: string;
  task_type: string;
  status: string;
  priority: string;
  progress: {
    current_step: number;
    total_steps: number;
    step_name: string;
    percentage: number;
    details: Record<string, unknown>;
  };
  created_at: string;
  started_at?: string;
  completed_at?: string;
  error_message?: string;
  retry_count: number;
  file_id?: string;
  result?: Record<string, unknown>;
}

export interface PaperProcessingStatus {
  paper_id: string;
  status: string;
  progress?: number;
  current_stage?: string;
  error_message?: string;
  can_retry?: boolean;
}

export interface QueryRequest {
  query: string;
  paper_ids?: string[];
  max_results?: number;
}

export interface QueryResponse {
  response: string;
  references: Array<{
    id: string;
    paper_name: string;
    section_type: string;
    page_num: number;
    content_snippet: string;
  }>;
  source_summary: {
    total_papers: number;
    papers_used: string[];
    sections_analyzed: string[];
    analysis_type: string;
  };
}

export interface UploadResponse {
  paper_id: string;
  task_id?: string;  
  message: string;
  duplicate?: boolean;
  filename?: string;
  original_filename?: string;
  file_size?: number;
  file_hash?: string;
}

export interface TaskStatusResponse {
  status: string;
  task_id: string;
  progress: {
    percentage: number;
    step_name: string;
    details?: unknown;
  } | null;
  error_message?: string;
}

export interface PaperStatusResponse {
  status: 'processing' | 'completed' | 'error' | 'queued';
  paper_id: string;
  progress: {
    percentage: number;
    step_name: string;
    details?: unknown;
  } | null;
  error_message?: string;
  task_id?: string;
}

// 保持向後相容性
export interface Paper {
  id: string;
  title: string;
  authors?: string[];
  file_path: string;
  file_hash: string;
  upload_time: string;
  processing_status: 'pending' | 'processing' | 'completed' | 'failed';
  selected: boolean;
  section_count: number;
  sentence_count: number;
}

import { API_CONFIG, getWebSocketUrl } from '../config/api.config';

class ApiService {
  private readonly baseUrl: string;
  private readonly timeout: number;

  constructor() {
    this.baseUrl = API_CONFIG.API_BASE_URL;
    this.timeout = API_CONFIG.API_TIMEOUT;
    
    console.info('✅ API Service initialized with workspace integration');
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseUrl}${endpoint}`;
    const defaultHeaders = {
      'Content-Type': 'application/json',
    };

    // 增加重試機制
    const maxRetries = 2;
    let lastError: string = '';
    
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.timeout);

        // 添加認證令牌
        const token = localStorage.getItem('jwt_token');
        const headers: Record<string, string> = {
          ...defaultHeaders,
          ...(options.headers as Record<string, string>),
        };
        if (token) {
          headers['Authorization'] = `Bearer ${token}`;
        }

        const response = await fetch(url, {
          ...options,
          headers,
          signal: controller.signal
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
          // 特殊處理不同的 HTTP 狀態碼
          let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
          
          try {
            const errorData = await response.json();
            if (errorData.detail) {
              errorMessage = errorData.detail;
            } else if (errorData.message) {
              errorMessage = errorData.message;
            }
          } catch {
            // 無法解析錯誤響應體，使用默認錯誤信息
          }
          
          // 404 錯誤的特殊處理
          if (response.status === 404) {
            console.warn(`API 404 for ${endpoint}:`, errorMessage);
            return {
              success: false,
              error: `請求的資源不存在或 API 路由配置錯誤: ${errorMessage}`
            };
          }
          
          // 500 錯誤的特殊處理
          if (response.status >= 500) {
            lastError = `伺服器內部錯誤: ${errorMessage}`;
            if (attempt < maxRetries) {
              console.warn(`Server error (attempt ${attempt + 1}/${maxRetries + 1}):`, lastError);
              await new Promise(resolve => setTimeout(resolve, 1000 * (attempt + 1))); // 遞增延遲
              continue;
            }
          }
          
          return {
            success: false,
            error: errorMessage
          };
        }

        const data = await response.json();
        return {
          success: true,
          data: data as T
        };

      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
        lastError = errorMessage;
        
        // 網路錯誤或超時的處理
        if (errorMessage.includes('aborted') || errorMessage.includes('timeout')) {
          if (attempt < maxRetries) {
            console.warn(`Request timeout (attempt ${attempt + 1}/${maxRetries + 1}) for ${endpoint}`);
            await new Promise(resolve => setTimeout(resolve, 2000 * (attempt + 1))); // 遞增延遲
            continue;
          }
          lastError = '請求超時，請檢查網路連接或稍後重試';
        } else if (errorMessage.includes('fetch')) {
          if (attempt < maxRetries) {
            console.warn(`Network error (attempt ${attempt + 1}/${maxRetries + 1}) for ${endpoint}:`, errorMessage);
            await new Promise(resolve => setTimeout(resolve, 1500 * (attempt + 1))); // 遞增延遲
            continue;
          }
          lastError = '網路連接錯誤，請檢查網路連接';
        }
        
        // 其他錯誤不重試
        break;
      }
    }

    return {
      success: false,
      error: lastError
    };
  }

  // ===== 工作區化檔案操作方法 =====

  /**
   * 檢查是否有當前工作區
   */
  private getCurrentWorkspaceId(): string | null {
    // 嘗試從 localStorage 獲取當前工作區
    return localStorage.getItem('current_workspace_id');
  }

  /**
   * 上傳檔案到當前工作區
   */
  async uploadFile(file: File): Promise<ApiResponse<UploadResponse>> {
    const workspaceId = this.getCurrentWorkspaceId();
    
    if (!workspaceId) {
      return {
        success: false,
        error: '請先選擇工作區以上傳檔案'
      };
    }

    const formData = new FormData();
    formData.append('file', file);

    return this.request<UploadResponse>(`/workspaces/${workspaceId}/files`, {
      method: 'POST',
      body: formData,
      headers: {} // 讓瀏覽器自動設定 Content-Type for FormData
    });
  }

  /**
   * 獲取當前工作區的論文列表
   */
  async getPapers(): Promise<ApiResponse<WorkspaceFile[]>> {
    const workspaceId = this.getCurrentWorkspaceId();
    
    if (!workspaceId) {
      return {
        success: false,
        error: '請先選擇工作區以查看檔案'
      };
    }

    const response = await this.request<{ items: WorkspaceFile[] }>(`/workspaces/${workspaceId}/files`);
    
    if (response.success && response.data) {
      return {
        success: true,
        data: response.data.items
      };
    }
    
    return {
      success: false,
      error: response.error || 'Failed to get papers'
    };
  }

  /**
   * 切換論文選取狀態
   */
  async togglePaperSelection(paperId: string, selected: boolean): Promise<ApiResponse<{ message: string }>> {
    const workspaceId = this.getCurrentWorkspaceId();
    
    if (!workspaceId) {
      return {
        success: false,
        error: '請先選擇工作區'
      };
    }

    return this.request<{ message: string }>(`/workspaces/${workspaceId}/files/${paperId}/selection`, {
      method: 'POST',
      body: JSON.stringify({ is_selected: selected })
    });
  }

  /**
   * 批次設定論文選取狀態
   */
  async setBatchPaperSelection(paperIds: string[], selected: boolean): Promise<ApiResponse<{ message: string }>> {
    const workspaceId = this.getCurrentWorkspaceId();
    
    if (!workspaceId) {
      return {
        success: false,
        error: '請先選擇工作區'
      };
    }

    return this.request<{ message: string }>(`/workspaces/${workspaceId}/selections/batch`, {
      method: 'POST',
      body: JSON.stringify({ 
        paper_ids: paperIds, 
        is_selected: selected 
      })
    });
  }

  /**
   * 刪除論文
   */
  async deletePaper(paperId: string): Promise<ApiResponse<{ message: string }>> {
    const workspaceId = this.getCurrentWorkspaceId();
    
    if (!workspaceId) {
      return {
        success: false,
        error: '請先選擇工作區'
      };
    }

    return this.request<{ message: string }>(`/workspaces/${workspaceId}/files/${paperId}`, {
      method: 'DELETE'
    });
  }

  /**
   * 在當前工作區執行查詢
   */
  async query(request: QueryRequest): Promise<ApiResponse<QueryResponse>> {
    const workspaceId = this.getCurrentWorkspaceId();
    
    if (!workspaceId) {
      return {
        success: false,
        error: '請先選擇工作區以進行查詢'
      };
    }

    return this.request<QueryResponse>(`/workspaces/${workspaceId}/query/unified`, {
      method: 'POST',
      body: JSON.stringify({
        query: request.query,
        search_scope: 'selected',
        max_results: request.max_results || 100
      })
    });
  }

  // ===== 向後相容方法 (將逐步移除) =====

  async getPaperSections(): Promise<ApiResponse<Record<string, unknown>>> {
    console.warn('⚠️ getPaperSections is deprecated, use workspace-specific queries instead');
    return {
      success: false,
      error: '此方法已棄用，請使用工作區化查詢功能'
    };
  }

  async getProcessingStatus(): Promise<ApiResponse<ProcessingStatus>> {
    const workspaceId = this.getCurrentWorkspaceId();
    
    if (!workspaceId) {
      return {
        success: false,
        error: '請先選擇工作區'
      };
    }

    return this.request<ProcessingStatus>(`/workspaces/${workspaceId}/processing/status`);
  }

  async getPaperProcessingStatus(paperId: string): Promise<ApiResponse<PaperProcessingStatus>> {
    const workspaceId = this.getCurrentWorkspaceId();
    
    if (!workspaceId) {
      return {
        success: false,
        error: '請先選擇工作區'
      };
    }

    return this.request<PaperProcessingStatus>(`/workspaces/${workspaceId}/files/${paperId}/status`);
  }

  async startProcessing(): Promise<ApiResponse<{ message: string }>> {
    const workspaceId = this.getCurrentWorkspaceId();
    
    if (!workspaceId) {
      return {
        success: false,
        error: '請先選擇工作區'
      };
    }

    return this.request<{ message: string }>(`/workspaces/${workspaceId}/processing/start`, {
      method: 'POST'
    });
  }

  async stopProcessing(): Promise<ApiResponse<{ message: string }>> {
    const workspaceId = this.getCurrentWorkspaceId();
    
    if (!workspaceId) {
      return {
        success: false,
        error: '請先選擇工作區'
      };
    }

    return this.request<{ message: string }>(`/workspaces/${workspaceId}/processing/stop`, {
      method: 'POST'
    });
  }

  // ===== 系統狀態檢查 =====

  async healthCheck(): Promise<ApiResponse<{ status: string; services: Record<string, boolean> }>> {
    return this.request<{ status: string; services: Record<string, boolean> }>('/health');
  }

  async getServiceStatus(): Promise<ApiResponse<{
    grobid: boolean;
    n8n: boolean;
    split_sentences: boolean;
    database: boolean;
  }>> {
    return this.request<{
      grobid: boolean;
      n8n: boolean;
      split_sentences: boolean;
      database: boolean;
    }>('/api/status');
  }

  // ===== WebSocket 支援 =====

  createProcessingWebSocket(onMessage: (data: unknown) => void, onError?: (error: Event) => void): WebSocket | null {
    const workspaceId = this.getCurrentWorkspaceId();
    
    if (!workspaceId) {
      console.error('Cannot create WebSocket: No workspace selected');
      return null;
    }

    try {
      const wsUrl = getWebSocketUrl(`/ws/workspaces/${workspaceId}/processing`);
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log('✅ Processing WebSocket connected for workspace:', workspaceId);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onMessage(data);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        onError?.(error);
      };

      ws.onclose = () => {
        console.log('Processing WebSocket disconnected');
      };

      return ws;
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      onError?.(error as Event);
      return null;
    }
  }

  // ===== 保持相容性的方法 =====

  async getPaperStatus(paperId: string): Promise<ApiResponse<PaperStatusResponse>> {
    const processingResponse = await this.getPaperProcessingStatus(paperId);
    
    if (!processingResponse.success) {
      return processingResponse as unknown as ApiResponse<PaperStatusResponse>;
    }

    // 轉換類型以符合舊介面
    const processingData = processingResponse.data!;
    const statusResponse: PaperStatusResponse = {
      status: processingData.status as 'processing' | 'completed' | 'error' | 'queued',
      paper_id: processingData.paper_id,
      progress: processingData.progress ? {
        percentage: processingData.progress,
        step_name: processingData.current_stage || 'Unknown',
        details: undefined
      } : null,
      error_message: processingData.error_message,
      task_id: undefined
    };

    return {
      success: true,
      data: statusResponse
    };
  }

  async getPaperSentences(paperId: string): Promise<ApiResponse<{
    paper_id: string;
    sentences: Array<{
      id: string;
      content: string;
      type: string;
      reason?: string;
      pageNumber?: number;
      fileName: string;
      fileId: string;
      sentenceOrder?: number;
      sectionId?: string;
      confidence?: number;
      wordCount?: number;
    }>;
    total_count: number;
    processing_status: string;
  }>> {
    const workspaceId = this.getCurrentWorkspaceId();
    
    if (!workspaceId) {
      return {
        success: false,
        error: '請先選擇工作區'
      };
    }

    return this.request(`/workspaces/${workspaceId}/files/${paperId}/sentences`);
  }

  async getAllSelectedPapersSentences(): Promise<ApiResponse<{
    sentences: Array<{
      id: string;
      content: string;
      type: string;
      reason?: string;
      pageNumber?: number;
      fileName: string;
      fileId: string;
      sentenceOrder?: number;
      sectionId?: string;
      confidence?: number;
      wordCount?: number;
    }>;
    total_sentences: number;
    total_papers: number;
    papers: Array<{
      id: string;
      fileName: string;
      processing_status: string;
    }>;
  }>> {
    const workspaceId = this.getCurrentWorkspaceId();
    
    if (!workspaceId) {
      return {
        success: false,
        error: '請先選擇工作區'
      };
    }

    return this.request(`/workspaces/${workspaceId}/files/selected-sentences`);
  }

  async getTaskStatus(taskId: string): Promise<ApiResponse<TaskStatus>> {
    return this.request<TaskStatus>(`/tasks/${taskId}/status`);
  }

  // ===== 設定工作區 (由外部組件調用) =====

  setCurrentWorkspace(workspaceId: string): void {
    localStorage.setItem('current_workspace_id', workspaceId);
    console.info('✅ Current workspace set to:', workspaceId);
  }

  clearCurrentWorkspace(): void {
    localStorage.removeItem('current_workspace_id');
    console.info('✅ Current workspace cleared');
  }
}

export const apiService = new ApiService();