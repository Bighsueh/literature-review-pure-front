/**
 * 統一 API 服務層
 * 負責所有與後端 API 的通訊，移除直接資料庫存取
 */
// import { errorHandler } from '@/utils/error_handler';

export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface PaperInfo {
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
  message: string;
  duplicate?: boolean;
  filename?: string;
  original_filename?: string;
  file_size?: number;
  file_hash?: string;
}

class ApiService {
  private readonly baseUrl: string;
  private readonly timeout: number = 30000; // 30 seconds

  constructor() {
    // 從環境變數或預設值獲取 API 基礎 URL
    this.baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001/api';
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
        
        // 根據狀態碼創建適當的錯誤
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
        
        // 使用錯誤處理器記錄錯誤
        // const errorDetails = errorHandler.handleError(error, {
        //   endpoint,
        //   statusCode: response.status,
        //   url,
        //   method: options.method || 'GET'
        // });
        
        return {
          success: false,
          error: errorMessage, //errorDetails.message,
        };
      }

      const data = await response.json();
      return {
        success: true,
        data,
      };
    } catch (error) {
      const err = error as Error;
      
      // 使用錯誤處理器處理異常
      // const errorDetails = errorHandler.handleError(err, {
      //   endpoint,
      //   url: `${this.baseUrl}${endpoint}`,
      //   method: options.method || 'GET'
      // });
      
      return {
        success: false,
        error: err.message, //errorDetails.message,
      };
    }
  }

  // ===== 檔案管理 API =====

  /**
   * 上傳 PDF 檔案
   */
  async uploadFile(file: File): Promise<ApiResponse<UploadResponse>> {
    const formData = new FormData();
    formData.append('file', file);

    return this.request('/upload/', {
      method: 'POST',
      body: formData,
      headers: {}, // 移除 Content-Type，讓瀏覽器自動設置
    });
  }

  /**
   * 獲取所有論文列表
   */
  async getPapers(): Promise<ApiResponse<PaperInfo[]>> {
    return this.request('/papers/');
  }

  /**
   * 切換論文選取狀態
   */
  async togglePaperSelection(paperId: string, selected: boolean): Promise<ApiResponse<{ message: string }>> {
    return this.request(`/papers/${paperId}/select`, {
      method: 'POST',
      body: JSON.stringify({ is_selected: selected }),
    });
  }

  /**
   * 批次設置論文選取狀態
   */
  async setBatchPaperSelection(paperIds: string[], selected: boolean): Promise<ApiResponse<{ message: string }>> {
    return this.request('/papers/batch-select', {
      method: 'POST',
      body: JSON.stringify({ paper_ids: paperIds, selected }),
    });
  }

  /**
   * 刪除論文
   */
  async deletePaper(paperId: string): Promise<ApiResponse<{ message: string }>> {
    return this.request(`/papers/${paperId}`, {
      method: 'DELETE',
    });
  }

  // ===== 處理狀態 API =====

  /**
   * 獲取處理狀態
   */
  async getProcessingStatus(): Promise<ApiResponse<ProcessingStatus>> {
    return this.request('/processing/queue/status');
  }

  /**
   * 開始處理選中的論文
   */
  async startProcessing(): Promise<ApiResponse<{ message: string }>> {
    return this.request('/processing/start', {
      method: 'POST',
    });
  }

  /**
   * 停止當前處理
   */
  async stopProcessing(): Promise<ApiResponse<{ message: string }>> {
    return this.request('/processing/stop', {
      method: 'POST',
    });
  }

  // ===== 查詢 API =====

  /**
   * 執行智能查詢
   */
  async query(request: QueryRequest): Promise<ApiResponse<QueryResponse>> {
    return this.request('/papers/unified-query', {
      method: 'POST',
      body: JSON.stringify({ query: request.query }),
    });
  }

  /**
   * 獲取論文章節摘要（用於智能查詢）
   */
  async getPaperSections(paperIds?: string[]): Promise<ApiResponse<Record<string, unknown>>> {
    const params = paperIds ? `?paper_ids=${paperIds.join(',')}` : '';
    return this.request(`/papers/sections-summary${params}`);
  }

  // ===== 健康檢查 API =====

  /**
   * 檢查 API 服務健康狀態
   */
  async healthCheck(): Promise<ApiResponse<{ status: string; services: Record<string, boolean> }>> {
    return this.request('/health');
  }

  /**
   * 檢查各個服務的狀態
   */
  async getServiceStatus(): Promise<ApiResponse<{
    grobid: boolean;
    n8n: boolean;
    split_sentences: boolean;
    database: boolean;
  }>> {
    return this.request('/status');
  }

  // ===== WebSocket 連接（用於實時更新） =====

  /**
   * 創建 WebSocket 連接以獲取實時處理更新
   */
  createProcessingWebSocket(onMessage: (data: unknown) => void, onError?: (error: Event) => void): WebSocket | null {
    try {
      const wsUrl = this.baseUrl.replace('http', 'ws') + '/processing/ws';
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
}

// 導出單例實例
export const apiService = new ApiService();
export default apiService;