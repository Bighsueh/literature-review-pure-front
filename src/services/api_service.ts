/**
 * 統一 API 服務層 - 緊急修復版本
 * 負責所有與後端 API 的通訊，移除直接資料庫存取
 * 
 * 修復狀態：EMERGENCY FIX - 硬編碼工作區支援
 * 下一步：實現真正的工作區管理和認證
 */
// import { errorHandler } from '@/utils/error_handler';

export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

// 新增工作區相關類型定義
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
  
  // 緊急修復：硬編碼一個預設工作區ID
  // TODO: 這需要在第二階段實現真正的工作區管理
  private readonly EMERGENCY_WORKSPACE_ID = 'temp-workspace-id';

  constructor() {
    this.baseUrl = API_CONFIG.API_BASE_URL;
    this.timeout = API_CONFIG.API_TIMEOUT;
    
    console.warn('🚨 API Service running in EMERGENCY MODE');
    console.warn('🚨 Using hardcoded workspace ID:', this.EMERGENCY_WORKSPACE_ID);
    console.warn('🚨 This MUST be fixed in the next iteration');
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    try {
      const url = `${this.baseUrl}${endpoint}`;
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.timeout);

      // 預設標頭
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        ...(options.headers as Record<string, string>),
      };

      // 如果是檔案上傳，讓瀏覽器自動設定 Content-Type
      if (options.body instanceof FormData) {
        delete headers['Content-Type'];
      }

      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
        headers,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const errorMessage = errorData.detail?.message || errorData.detail || `HTTP ${response.status}: ${response.statusText}`;
        
        let error: Error;
        if (response.status >= 500) {
          error = new Error(errorMessage);
          error.name = 'ServerError';
        } else if (response.status === 429) {
          error = new Error(errorMessage);
          error.name = 'RateLimitError';
        } else if (response.status >= 400) {
          error = new Error(errorMessage);
          error.name = 'ClientError';
        } else {
          error = new Error(errorMessage);
        }
        
        throw error;
      }

      const data = await response.json();
      return {
        success: true,
        data,
      };

    } catch (error) {
      console.error('API request failed:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  // ===== 緊急修復：工作區化的檔案管理 API =====

  /**
   * 上傳檔案到當前工作區 (緊急修復版本)
   */
  async uploadFile(file: File): Promise<ApiResponse<UploadResponse>> {
    const formData = new FormData();
    formData.append('file', file);

    console.warn('🚨 Emergency upload to workspace:', this.EMERGENCY_WORKSPACE_ID);
    
    return this.request(`/workspaces/${this.EMERGENCY_WORKSPACE_ID}/files/`, {
      method: 'POST',
      body: formData,
      headers: {}, 
    });
  }

  /**
   * 獲取當前工作區的檔案列表 (緊急修復版本)
   */
  async getPapers(): Promise<ApiResponse<WorkspaceFile[]>> {
    console.warn('🚨 Emergency get files from workspace:', this.EMERGENCY_WORKSPACE_ID);
    
    return this.request(`/workspaces/${this.EMERGENCY_WORKSPACE_ID}/files/`);
  }

  /**
   * 切換檔案選取狀態 (緊急修復版本)
   */
  async togglePaperSelection(paperId: string, selected: boolean): Promise<ApiResponse<{ message: string }>> {
    console.warn('🚨 Emergency toggle file selection in workspace:', this.EMERGENCY_WORKSPACE_ID);
    
    return this.request(`/workspaces/${this.EMERGENCY_WORKSPACE_ID}/files/batch-select`, {
      method: 'POST',
      body: JSON.stringify({ file_ids: [paperId], selected }),
    });
  }

  /**
   * 批次設置檔案選取狀態 (緊急修復版本)
   */
  async setBatchPaperSelection(paperIds: string[], selected: boolean): Promise<ApiResponse<{ message: string }>> {
    console.warn('🚨 Emergency batch select files in workspace:', this.EMERGENCY_WORKSPACE_ID);
    
    return this.request(`/workspaces/${this.EMERGENCY_WORKSPACE_ID}/files/batch-select`, {
      method: 'POST',
      body: JSON.stringify({ file_ids: paperIds, selected }),
    });
  }

  /**
   * 刪除檔案 (緊急修復版本)
   */
  async deletePaper(paperId: string): Promise<ApiResponse<{ message: string }>> {
    console.warn('🚨 Emergency delete file from workspace:', this.EMERGENCY_WORKSPACE_ID);
    
    return this.request(`/workspaces/${this.EMERGENCY_WORKSPACE_ID}/files/${paperId}`, {
      method: 'DELETE',
    });
  }

  // ===== 緊急修復：工作區化的查詢 API =====

  /**
   * 執行智能查詢 (緊急修復版本)
   */
  async query(request: QueryRequest): Promise<ApiResponse<QueryResponse>> {
    console.warn('🚨 Emergency query in workspace:', this.EMERGENCY_WORKSPACE_ID);
    
    return this.request(`/workspaces/${this.EMERGENCY_WORKSPACE_ID}/query/`, {
      method: 'POST',
      body: JSON.stringify({ query: request.query }),
    });
  }

  /**
   * 獲取檔案章節摘要 (緊急修復版本)
   */
  async getPaperSections(): Promise<ApiResponse<Record<string, unknown>>> {
    console.warn('🚨 Emergency get sections from workspace:', this.EMERGENCY_WORKSPACE_ID);
    
    return this.request(`/workspaces/${this.EMERGENCY_WORKSPACE_ID}/files/sections-summary`);
  }

  // ===== 保持舊的方法以維持相容性 =====

  async getProcessingStatus(): Promise<ApiResponse<ProcessingStatus>> {
    return this.request('/processing/queue/status');
  }

  async getPaperProcessingStatus(paperId: string): Promise<ApiResponse<PaperProcessingStatus>> {
    return this.request(`/papers/${paperId}/status`);
  }

  async startProcessing(): Promise<ApiResponse<{ message: string }>> {
    return this.request('/processing/start', {
      method: 'POST',
    });
  }

  async stopProcessing(): Promise<ApiResponse<{ message: string }>> {
    return this.request('/processing/stop', {
      method: 'POST',
    });
  }

  async healthCheck(): Promise<ApiResponse<{ status: string; services: Record<string, boolean> }>> {
    return this.request('/health');
  }

  async getServiceStatus(): Promise<ApiResponse<{
    grobid: boolean;
    n8n: boolean;
    split_sentences: boolean;
    database: boolean;
  }>> {
    return this.request('/status');
  }

  createProcessingWebSocket(onMessage: (data: unknown) => void, onError?: (error: Event) => void): WebSocket | null {
    try {
      const wsUrl = getWebSocketUrl('/processing/ws');
      const ws = new WebSocket(wsUrl);

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
        if (onError) onError(error);
      };

      return ws;
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      return null;
    }
  }

  async getPaperStatus(paperId: string): Promise<ApiResponse<PaperStatusResponse>> {
    return this.request(`/papers/${paperId}/status`);
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
    return this.request(`/papers/${paperId}/sentences`);
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
    return this.request('/papers/selected/sentences');
  }

  async getTaskStatus(taskId: string): Promise<ApiResponse<TaskStatus>> {
    return this.request(`/tasks/${taskId}/status`);
  }

  // ===== 緊急新增：臨時工作區管理方法 =====
  
  /**
   * 獲取當前硬編碼工作區的資訊 (緊急修復)
   */
  getCurrentWorkspaceId(): string {
    return this.EMERGENCY_WORKSPACE_ID;
  }

  /**
   * 設置緊急工作區ID (用於測試)
   * 注意：這是緊急修復方法，應該在第二階段移除
   */
  setEmergencyWorkspaceId(workspaceId: string): void {
    console.warn('🚨 Changing emergency workspace ID to:', workspaceId);
    console.warn('🚨 This method will be removed in the next iteration');
    // 暫時使用 Object.defineProperty 來修改 readonly 屬性
    Object.defineProperty(this, 'EMERGENCY_WORKSPACE_ID', {
      value: workspaceId,
      writable: false,
      configurable: true
    });
  }
}

// 導出單例實例
export const apiService = new ApiService();
export default apiService;