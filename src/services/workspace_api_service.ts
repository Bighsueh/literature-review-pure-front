/**
 * 工作區化API服務層 - FE-00 重構版本
 * 負責所有與後端工作區化API的通訊
 * 支援JWT token管理和完整的工作區隔離
 */

import { 
  ApiResponse, 
  ApiError, 
  PaginatedResponse,
  User, 
  AuthResponse, 
  Workspace, 
  WorkspaceCreate, 
  WorkspaceUpdate,
  UserWithWorkspaces,
  Paper, 
  PaperUpdate,
  PaperSelection,
  PaperSelectionUpdate,
  ChatHistory,
  ChatHistoryCreate,
  ChatWithContext,
  QueryRequest,
  QueryResult,
  UploadResponse,
  TaskStatus,
  HealthCheckResponse,
  ServiceStatus,
  ProcessingProgress,
  PaperProcessingStatus,
  WebSocketMessage,
  ProcessingWebSocketData
} from '../types/api';

import { API_CONFIG, getWebSocketUrl } from '../config/api.config';

/**
 * JWT Token 管理類
 */
class TokenManager {
  private static readonly TOKEN_KEY = 'jwt_token';
  private static readonly REFRESH_TOKEN_KEY = 'refresh_token';
  private static readonly USER_KEY = 'current_user';

  static getToken(): string | null {
    // 優先從 HTTP-only cookies 讀取 (更安全)
    // 如果不可用，則從 localStorage 讀取 (開發環境)
    const token = this.getCookie('access_token') || localStorage.getItem(this.TOKEN_KEY);
    return token;
  }

  static setToken(token: string): void {
    localStorage.setItem(this.TOKEN_KEY, token);
  }

  static getRefreshToken(): string | null {
    return this.getCookie('refresh_token') || localStorage.getItem(this.REFRESH_TOKEN_KEY);
  }

  static setRefreshToken(token: string): void {
    localStorage.setItem(this.REFRESH_TOKEN_KEY, token);
  }

  static getCurrentUser(): User | null {
    const userStr = localStorage.getItem(this.USER_KEY);
    return userStr ? JSON.parse(userStr) : null;
  }

  static setCurrentUser(user: User): void {
    localStorage.setItem(this.USER_KEY, JSON.stringify(user));
  }

  static clearAuth(): void {
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.REFRESH_TOKEN_KEY);
    localStorage.removeItem(this.USER_KEY);
    // 清除 cookies (如果可能)
    this.deleteCookie('access_token');
    this.deleteCookie('refresh_token');
  }

  static isAuthenticated(): boolean {
    // 開發模式：如果沒有 token，創建一個假的認證狀態
    if (import.meta.env.DEV || import.meta.env.VITE_NODE_ENV === 'development') {
      const token = this.getToken();
      const user = this.getCurrentUser();
      
      // 如果沒有認證資料，創建開發模式的假資料
      if (!token || !user) {
        console.warn('🚨 開發模式：使用假認證資料');
        this.setToken('dev-token-' + Date.now());
        this.setCurrentUser({
          id: 'dev-user-id',
          google_id: 'dev-google-id',
          email: 'dev@example.com',
          name: '開發用戶',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        });
        return true;
      }
      
      return !!(token && user);
    }
    
    // 生產模式：正常驗證
    const token = this.getToken();
    const user = this.getCurrentUser();
    return !!(token && user);
  }

  private static getCookie(name: string): string | null {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) {
      return parts.pop()?.split(';').shift() || null;
    }
    return null;
  }

  private static deleteCookie(name: string): void {
    document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
  }
}

/**
 * 工作區化API服務主類
 */
class WorkspaceApiService {
  private readonly baseUrl: string;
  private readonly timeout: number;
  private currentWorkspaceId: string | null = null;

  constructor() {
    this.baseUrl = API_CONFIG.API_BASE_URL;
    this.timeout = API_CONFIG.API_TIMEOUT;
  }

  // ===== 認證相關方法 =====

  /**
   * Google OAuth 登入
   */
  async googleLogin(): Promise<void> {
    try {
      // 1. 從後端獲取 Google OAuth 授權 URL
      const response = await this.request<{ authorization_url: string }>('/auth/google/url');
      
      if (response.success && response.data) {
        // 2. 重定向到 Google OAuth
        window.location.href = response.data.authorization_url;
      } else {
        console.error('Failed to get Google OAuth URL:', response.error);
        throw new Error(response.error || 'Failed to initiate Google login');
      }
    } catch (error) {
      console.error('Google login failed:', error);
      throw error;
    }
  }

  /**
   * 登出
   */
  async logout(): Promise<ApiResponse<{ message: string }>> {
    try {
      const response = await this.authenticatedRequest<{ message: string }>('/auth/logout', {
        method: 'POST'
      });
      
      // 清除本地認證資料
      TokenManager.clearAuth();
      this.currentWorkspaceId = null;
      
      return response;
    } catch (error) {
      // 即使API調用失敗，也要清除本地資料
      TokenManager.clearAuth();
      this.currentWorkspaceId = null;
      throw error;
    }
  }

  /**
   * 獲取當前使用者資訊
   */
  async getCurrentUser(): Promise<ApiResponse<UserWithWorkspaces>> {
    // 開發模式：返回假資料
    if (import.meta.env.DEV || import.meta.env.VITE_NODE_ENV === 'development') {
      console.warn('🚨 開發模式：返回假用戶資料');
      
      const mockUser: UserWithWorkspaces = {
        id: 'dev-user-id',
        google_id: 'dev-google-id',
        email: 'dev@example.com',
        name: '開發用戶',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        workspaces: [
          {
            id: '1e7a7a7a-5e8d-4b78-a7e9-2536ea9fad64',
            user_id: 'dev-user-id',
            name: 'first-chat',
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
          },
          {
            id: '7ddbb7c1-7cc0-4d60-ad3e-c8deed1447ea',
            user_id: 'dev-user-id',
            name: 'second-chat',
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
          }
        ]
      };
      
      return {
        success: true,
        data: mockUser
      };
    }
    
    return this.authenticatedRequest<UserWithWorkspaces>('/auth/me');
  }

  /**
   * 刷新 JWT token
   */
  async refreshToken(): Promise<ApiResponse<AuthResponse>> {
    const refreshToken = TokenManager.getRefreshToken();
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    const response = await this.request<AuthResponse>('/auth/refresh', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken })
    });

    if (response.success && response.data) {
      TokenManager.setToken(response.data.tokens.access_token);
      TokenManager.setCurrentUser(response.data.user);
    }

    return response;
  }

  // ===== 工作區管理方法 =====

  /**
   * 獲取使用者的所有工作區
   */
  async getWorkspaces(): Promise<ApiResponse<Workspace[]>> {
    // 開發模式：返回假資料
    if (import.meta.env.DEV || import.meta.env.VITE_NODE_ENV === 'development') {
      console.warn('🚨 開發模式：返回假工作區資料');
      
      const mockWorkspaces: Workspace[] = [
        {
          id: '1e7a7a7a-5e8d-4b78-a7e9-2536ea9fad64',
          user_id: 'dev-user-id',
          name: 'first-chat',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        },
        {
          id: '7ddbb7c1-7cc0-4d60-ad3e-c8deed1447ea',
          user_id: 'dev-user-id',
          name: 'second-chat',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        }
      ];
      
      return {
        success: true,
        data: mockWorkspaces
      };
    }
    
    return this.authenticatedRequest<Workspace[]>('/workspaces/');
  }

  /**
   * 創建新工作區
   */
  async createWorkspace(data: WorkspaceCreate): Promise<ApiResponse<Workspace>> {
    return this.authenticatedRequest<Workspace>('/workspaces', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  /**
   * 獲取特定工作區詳情
   */
  async getWorkspace(workspaceId: string): Promise<ApiResponse<Workspace>> {
    return this.authenticatedRequest<Workspace>(`/workspaces/${workspaceId}`);
  }

  /**
   * 更新工作區
   */
  async updateWorkspace(workspaceId: string, data: WorkspaceUpdate): Promise<ApiResponse<Workspace>> {
    return this.authenticatedRequest<Workspace>(`/workspaces/${workspaceId}`, {
      method: 'PUT',
      body: JSON.stringify(data)
    });
  }

  /**
   * 刪除工作區
   */
  async deleteWorkspace(workspaceId: string): Promise<ApiResponse<{ message: string }>> {
    return this.authenticatedRequest<{ message: string }>(`/workspaces/${workspaceId}`, {
      method: 'DELETE'
    });
  }

  // ===== 工作區上下文管理 =====

  /**
   * 設置當前工作區
   */
  setCurrentWorkspace(workspaceId: string): void {
    this.currentWorkspaceId = workspaceId;
    // 將當前工作區保存到 localStorage
    localStorage.setItem('current_workspace_id', workspaceId);
  }

  /**
   * 獲取當前工作區ID
   */
  getCurrentWorkspaceId(): string | null {
    if (!this.currentWorkspaceId) {
      // 嘗試從 localStorage 恢復
      this.currentWorkspaceId = localStorage.getItem('current_workspace_id');
    }
    return this.currentWorkspaceId;
  }

  /**
   * 清除當前工作區
   */
  clearCurrentWorkspace(): void {
    this.currentWorkspaceId = null;
    localStorage.removeItem('current_workspace_id');
  }

  // ===== 檔案/論文管理方法 =====

  /**
   * 上傳檔案到當前工作區
   */
  async uploadFile(file: File): Promise<ApiResponse<UploadResponse>> {
    const workspaceId = this.requireCurrentWorkspace();
    const formData = new FormData();
    formData.append('file', file);

    return this.authenticatedRequest<UploadResponse>(`/workspaces/${workspaceId}/files`, {
      method: 'POST',
      body: formData,
      headers: {} // 讓瀏覽器自動設定 Content-Type
    });
  }

  /**
   * 獲取工作區檔案列表
   */
  async getPapers(): Promise<ApiResponse<PaginatedResponse<Paper>>> {
    const workspaceId = this.requireCurrentWorkspace();
    return this.authenticatedRequest<PaginatedResponse<Paper>>(`/workspaces/${workspaceId}/files`);
  }

  /**
   * 獲取特定論文詳情
   */
  async getPaper(paperId: string): Promise<ApiResponse<Paper>> {
    const workspaceId = this.requireCurrentWorkspace();
    return this.authenticatedRequest<Paper>(`/workspaces/${workspaceId}/files/${paperId}`);
  }

  /**
   * 更新論文資訊
   */
  async updatePaper(paperId: string, data: PaperUpdate): Promise<ApiResponse<Paper>> {
    const workspaceId = this.requireCurrentWorkspace();
    return this.authenticatedRequest<Paper>(`/workspaces/${workspaceId}/files/${paperId}`, {
      method: 'PUT',
      body: JSON.stringify(data)
    });
  }

  /**
   * 刪除論文
   */
  async deletePaper(paperId: string): Promise<ApiResponse<{ message: string }>> {
    const workspaceId = this.requireCurrentWorkspace();
    return this.authenticatedRequest<{ message: string }>(`/workspaces/${workspaceId}/files/${paperId}`, {
      method: 'DELETE'
    });
  }

  /**
   * 切換論文選擇狀態
   */
  async togglePaperSelection(paperId: string, isSelected: boolean): Promise<ApiResponse<PaperSelection>> {
    const workspaceId = this.requireCurrentWorkspace();
    const data: PaperSelectionUpdate = { is_selected: isSelected };
    
    return this.authenticatedRequest<PaperSelection>(`/workspaces/${workspaceId}/files/${paperId}/selection`, {
      method: 'PUT',
      body: JSON.stringify(data)
    });
  }

  /**
   * 批量設置論文選擇狀態
   */
  async setBatchPaperSelection(paperIds: string[], isSelected: boolean): Promise<ApiResponse<{ message: string, updated_count: number }>> {
    const workspaceId = this.requireCurrentWorkspace();
    const data = { paper_ids: paperIds, is_selected: isSelected };
    
    return this.authenticatedRequest<{ message: string, updated_count: number }>(`/workspaces/${workspaceId}/files/batch-selection`, {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  // ===== 查詢和對話方法 =====

  /**
   * 發送查詢請求
   */
  async query(request: QueryRequest): Promise<ApiResponse<QueryResult>> {
    const workspaceId = this.requireCurrentWorkspace();
    return this.authenticatedRequest<QueryResult>(`/workspaces/${workspaceId}/query`, {
      method: 'POST',
      body: JSON.stringify(request)
    });
  }

  /**
   * 獲取對話歷史
   */
  async getChatHistory(page: number = 1, pageSize: number = 20): Promise<ApiResponse<PaginatedResponse<ChatWithContext>>> {
    const workspaceId = this.requireCurrentWorkspace();
    const params = new URLSearchParams({
      page: page.toString(),
      page_size: pageSize.toString()
    });
    
    return this.authenticatedRequest<PaginatedResponse<ChatWithContext>>(`/workspaces/${workspaceId}/chats?${params}`);
  }

  /**
   * 保存對話記錄
   */
  async saveChatHistory(data: Omit<ChatHistoryCreate, 'workspace_id'>): Promise<ApiResponse<ChatHistory>> {
    const workspaceId = this.requireCurrentWorkspace();
    const chatData: ChatHistoryCreate = { ...data, workspace_id: workspaceId };
    
    return this.authenticatedRequest<ChatHistory>(`/workspaces/${workspaceId}/chats`, {
      method: 'POST',
      body: JSON.stringify(chatData)
    });
  }

  // ===== 處理狀態和任務監控 =====

  /**
   * 獲取處理進度
   */
  async getProcessingStatus(): Promise<ApiResponse<ProcessingProgress>> {
    const workspaceId = this.requireCurrentWorkspace();
    return this.authenticatedRequest<ProcessingProgress>(`/workspaces/${workspaceId}/processing/status`);
  }

  /**
   * 獲取論文處理狀態
   */
  async getPaperProcessingStatus(paperId: string): Promise<ApiResponse<PaperProcessingStatus>> {
    const workspaceId = this.requireCurrentWorkspace();
    
    // 增強錯誤處理：嘗試多個路由
    const routes = [
      `/workspaces/${workspaceId}/files/${paperId}/status`, // 首選：工作區範圍的路由
      `/api/papers/${paperId}/status`, // 備用：全局路由
      `/api/processing/status/${paperId}` // 最後備用：處理狀態路由
    ];
    
    let lastError = '';
    
    for (const route of routes) {
      try {
        const response = await this.authenticatedRequest<PaperProcessingStatus>(route);
        if (response.success) {
          return response;
        }
        lastError = response.error || 'Request failed';
      } catch (error) {
        lastError = error instanceof Error ? error.message : 'Unknown error';
        console.warn(`Route ${route} failed:`, lastError);
      }
    }
    
    // 如果所有路由都失敗，返回友好的錯誤信息
    console.error(`All status routes failed for paper ${paperId}. Last error: ${lastError}`);
    
    return {
      success: false,
      error: `無法獲取檔案處理狀態。這可能是暫時的網路問題，請稍後重試。`,
      data: undefined
    };
  }

  /**
   * 獲取任務狀態
   */
  async getTaskStatus(taskId: string): Promise<ApiResponse<TaskStatus>> {
    return this.authenticatedRequest<TaskStatus>(`/tasks/${taskId}`);
  }

  /**
   * 開始處理
   */
  async startProcessing(): Promise<ApiResponse<{ message: string }>> {
    const workspaceId = this.requireCurrentWorkspace();
    return this.authenticatedRequest<{ message: string }>(`/workspaces/${workspaceId}/processing/start`, {
      method: 'POST'
    });
  }

  /**
   * 停止處理
   */
  async stopProcessing(): Promise<ApiResponse<{ message: string }>> {
    const workspaceId = this.requireCurrentWorkspace();
    return this.authenticatedRequest<{ message: string }>(`/workspaces/${workspaceId}/processing/stop`, {
      method: 'POST'
    });
  }

  // ===== WebSocket 連接 =====

  /**
   * 創建工作區範圍的處理 WebSocket 連接
   */
  createProcessingWebSocket(
    onMessage: (data: ProcessingWebSocketData) => void, 
    onError?: (error: Event) => void
  ): WebSocket | null {
    const workspaceId = this.getCurrentWorkspaceId();
    if (!workspaceId) {
      console.error('No current workspace set for WebSocket connection');
      return null;
    }

    try {
      const token = TokenManager.getToken();
      const wsUrl = `${getWebSocketUrl()}/workspaces/${workspaceId}/processing/ws?token=${encodeURIComponent(token || '')}`;
      
      const ws = new WebSocket(wsUrl);
      
      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          if (message.type === 'processing_update') {
            onMessage(message.data as ProcessingWebSocketData);
          }
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        onError?.(error);
      };
      
      return ws;
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      onError?.(error as Event);
      return null;
    }
  }

  // ===== 系統健康檢查 =====

  /**
   * 健康檢查
   */
  async healthCheck(): Promise<ApiResponse<HealthCheckResponse>> {
    return this.request<HealthCheckResponse>('/health');
  }

  /**
   * 獲取服務狀態
   */
  async getServiceStatus(): Promise<ApiResponse<ServiceStatus>> {
    return this.request<ServiceStatus>('/health/services');
  }

  // ===== 私有輔助方法 =====

  /**
   * 要求當前工作區存在
   */
  private requireCurrentWorkspace(): string {
    const workspaceId = this.getCurrentWorkspaceId();
    if (!workspaceId) {
      throw new Error('No current workspace selected. Please select a workspace first.');
    }
    return workspaceId;
  }

  /**
   * 帶認證的請求
   */
  private async authenticatedRequest<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const token = TokenManager.getToken();
    if (!token) {
      throw new Error('No authentication token available');
    }

    const headers = {
      ...options.headers,
      'Authorization': `Bearer ${token}`
    };

    try {
      return await this.request<T>(endpoint, { ...options, headers });
    } catch (error) {
      // 如果是 401 錯誤，嘗試刷新 token
      if (error instanceof Error && error.message.includes('401')) {
        try {
          await this.refreshToken();
          // 重試原請求
          const newToken = TokenManager.getToken();
          if (newToken) {
            return await this.request<T>(endpoint, {
              ...options,
              headers: {
                ...options.headers,
                'Authorization': `Bearer ${newToken}`
              }
            });
          }
        } catch {
          // 刷新失敗，清除認證資料並重導向到登入頁面
          TokenManager.clearAuth();
          window.location.href = '/login';
          throw new Error('Authentication expired. Please login again.');
        }
      }
      throw error;
    }
  }

  /**
   * 基礎請求方法
   */
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    try {
      const url = `${this.baseUrl}${endpoint}`;
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.timeout);

      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
        ...options.headers as Record<string, string>
      };

      // 如果是檔案上傳，移除 Content-Type 讓瀏覽器自動設定
      if (options.body instanceof FormData) {
        delete headers['Content-Type'];
      }

      const response = await fetch(url, {
        ...options,
        headers,
        signal: controller.signal,
        credentials: 'include' // 支援 HTTP-only cookies
      });

      clearTimeout(timeoutId);

      // 處理 HTTP 錯誤
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        
        // RFC-7807 格式錯誤處理
        if (errorData.type && errorData.title) {
          const apiError: ApiError = {
            type: errorData.type,
            title: errorData.title,
            status: response.status,
            detail: errorData.detail || response.statusText,
            instance: errorData.instance,
            errors: errorData.errors
          };
          
          return {
            success: false,
            error: apiError.detail,
            message: `${apiError.title}: ${apiError.detail}`
          };
        }

        return {
          success: false,
          error: errorData.message || response.statusText,
          message: `HTTP ${response.status}: ${errorData.message || response.statusText}`
        };
      }

      const data = await response.json();
      
      return {
        success: true,
        data: data as T,
        message: 'Request successful'
      };

    } catch (error) {
      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          return {
            success: false,
            error: 'Request timeout',
            message: 'Request timed out after ' + this.timeout / 1000 + ' seconds'
          };
        }
        
        return {
          success: false,
          error: error.message,
          message: 'Network error: ' + error.message
        };
      }
      
      return {
        success: false,
        error: 'Unknown error',
        message: 'An unknown error occurred'
      };
    }
  }
}

// 單例實例
export const workspaceApiService = new WorkspaceApiService();

// 導出 TokenManager 供其他模組使用
export { TokenManager };

// 默認導出
export default workspaceApiService; 