// services/error_handler.ts

// 錯誤類型定義
export enum ErrorType {
  NETWORK = 'NETWORK',
  API = 'API',
  VALIDATION = 'VALIDATION',
  AUTHENTICATION = 'AUTHENTICATION',
  PERMISSION = 'PERMISSION',
  FILE_UPLOAD = 'FILE_UPLOAD',
  FILE_PROCESSING = 'FILE_PROCESSING',
  N8N_API = 'N8N_API',
  DATABASE = 'DATABASE',
  UNKNOWN = 'UNKNOWN'
}

export enum ErrorSeverity {
  LOW = 'LOW',
  MEDIUM = 'MEDIUM',
  HIGH = 'HIGH',
  CRITICAL = 'CRITICAL'
}

export interface ErrorDetails {
  type: ErrorType;
  severity: ErrorSeverity;
  message: string;
  originalError?: Error;
  context?: Record<string, unknown>;
  timestamp: Date;
  userAgent?: string;
  url?: string;
  userId?: string;
  stackTrace?: string;
  retryable: boolean;
  retryCount?: number;
  maxRetries?: number;
}

export interface RetryConfig {
  maxRetries: number;
  baseDelay: number;
  maxDelay: number;
  exponentialBackoff: boolean;
  retryCondition?: (error: ErrorDetails) => boolean;
}

// 預設重試配置
const DEFAULT_RETRY_CONFIG: RetryConfig = {
  maxRetries: 3,
  baseDelay: 1000,
  maxDelay: 10000,
  exponentialBackoff: true,
  retryCondition: (error) => {
    return error.type === ErrorType.NETWORK || 
           error.type === ErrorType.API ||
           error.type === ErrorType.N8N_API;
  }
};

class ErrorHandler {
  private errorLog: ErrorDetails[] = [];
  private readonly maxLogSize = 100;
  private retryConfig: RetryConfig = DEFAULT_RETRY_CONFIG;

  // 設置重試配置
  setRetryConfig(config: Partial<RetryConfig>): void {
    this.retryConfig = { ...this.retryConfig, ...config };
  }

  // 處理錯誤
  handleError(error: Error | ErrorDetails, context?: Record<string, unknown>): ErrorDetails {
    let errorDetails: ErrorDetails;

    if (this.isErrorDetails(error)) {
      errorDetails = error;
    } else {
      errorDetails = this.createErrorDetails(error, context);
    }

    // 記錄錯誤
    this.logError(errorDetails);

    // 顯示使用者友好訊息
    this.showUserMessage(errorDetails);

    // 報告錯誤（如果有監控服務）
    this.reportError(errorDetails);

    return errorDetails;
  }

  // 創建錯誤詳情
  private createErrorDetails(error: Error, context?: Record<string, unknown>): ErrorDetails {
    const errorType = this.determineErrorType(error);
    const severity = this.determineSeverity(errorType);

    return {
      type: errorType,
      severity,
      message: this.createUserFriendlyMessage(errorType),
      originalError: error,
      context: {
        ...context,
        errorName: error.name,
        errorMessage: error.message
      },
      timestamp: new Date(),
      userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : 'unknown',
      url: typeof window !== 'undefined' ? window.location.href : 'unknown',
      stackTrace: error.stack,
      retryable: this.isRetryable(errorType),
      retryCount: 0,
      maxRetries: this.retryConfig.maxRetries
    };
  }

  // 判斷錯誤類型
  private determineErrorType(error: Error): ErrorType {
    const message = error.message.toLowerCase();

    if (error.name === 'TypeError' && message.includes('fetch')) {
      return ErrorType.NETWORK;
    }
    
    if (message.includes('unauthorized') || message.includes('401')) {
      return ErrorType.AUTHENTICATION;
    }
    
    if (message.includes('forbidden') || message.includes('403')) {
      return ErrorType.PERMISSION;
    }
    
    if (message.includes('validation') || message.includes('invalid')) {
      return ErrorType.VALIDATION;
    }
    
    if (message.includes('upload') || message.includes('file')) {
      return ErrorType.FILE_UPLOAD;
    }
    
    if (message.includes('n8n') || message.includes('webhook')) {
      return ErrorType.N8N_API;
    }
    
    if (message.includes('database') || message.includes('sql')) {
      return ErrorType.DATABASE;
    }
    
    if (message.includes('api') || message.includes('server')) {
      return ErrorType.API;
    }

    return ErrorType.UNKNOWN;
  }

  // 判斷錯誤嚴重程度
  private determineSeverity(type: ErrorType): ErrorSeverity {
    switch (type) {
      case ErrorType.DATABASE:
        return ErrorSeverity.CRITICAL;
      
      case ErrorType.AUTHENTICATION:
      case ErrorType.PERMISSION:
      case ErrorType.FILE_PROCESSING:
        return ErrorSeverity.HIGH;
      
      case ErrorType.API:
      case ErrorType.N8N_API:
      case ErrorType.FILE_UPLOAD:
        return ErrorSeverity.MEDIUM;
      
      case ErrorType.NETWORK:
      case ErrorType.VALIDATION:
        return ErrorSeverity.LOW;
      
      default:
        return ErrorSeverity.MEDIUM;
    }
  }

  // 創建使用者友好訊息
  private createUserFriendlyMessage(type: ErrorType): string {
    const baseMessages = {
      [ErrorType.NETWORK]: '網路連線發生問題，請檢查您的網路連線',
      [ErrorType.API]: 'API 服務暫時無法使用，請稍後重試',
      [ErrorType.VALIDATION]: '輸入資料格式不正確，請檢查後重試',
      [ErrorType.AUTHENTICATION]: '身份驗證失敗，請重新登入',
      [ErrorType.PERMISSION]: '您沒有權限執行此操作',
      [ErrorType.FILE_UPLOAD]: '檔案上傳失敗，請檢查檔案格式和大小',
      [ErrorType.FILE_PROCESSING]: '檔案處理失敗，請稍後重試',
      [ErrorType.N8N_API]: 'AI 分析服務暫時無法使用，請稍後重試',
      [ErrorType.DATABASE]: '資料庫連線錯誤，請聯繫系統管理員',
      [ErrorType.UNKNOWN]: '發生未知錯誤，請稍後重試'
    };

    return baseMessages[type] || baseMessages[ErrorType.UNKNOWN];
  }

  // 判斷是否可重試
  private isRetryable(type: ErrorType): boolean {
    const retryableTypes = [
      ErrorType.NETWORK,
      ErrorType.API,
      ErrorType.N8N_API,
      ErrorType.FILE_UPLOAD,
      ErrorType.FILE_PROCESSING
    ];
    
    return retryableTypes.includes(type);
  }

  // 顯示使用者訊息
  private showUserMessage(errorDetails: ErrorDetails): void {
    // 在開發環境顯示詳細錯誤
    if (process.env.NODE_ENV === 'development') {
      console.warn(`🚨 [${errorDetails.severity}] ${errorDetails.message}`);
    }
  }

  // 記錄錯誤
  private logError(errorDetails: ErrorDetails): void {
    this.errorLog.unshift(errorDetails);
    
    // 限制日誌大小
    if (this.errorLog.length > this.maxLogSize) {
      this.errorLog = this.errorLog.slice(0, this.maxLogSize);
    }

    // 控制台輸出
    console.group(`🚨 Error [${errorDetails.type}] - ${errorDetails.severity}`);
    console.error('Message:', errorDetails.message);
    console.error('Original Error:', errorDetails.originalError);
    console.error('Context:', errorDetails.context);
    console.error('Stack Trace:', errorDetails.stackTrace);
    console.groupEnd();

    // 儲存到 localStorage (可選)
    if (typeof window !== 'undefined') {
      try {
        localStorage.setItem('errorLog', JSON.stringify(this.errorLog.slice(0, 10)));
      } catch (e) {
        console.warn('無法儲存錯誤日誌到 localStorage:', e);
      }
    }
  }

  // 報告錯誤到監控服務
  private reportError(errorDetails: ErrorDetails): void {
    // 這裡可以整合 Sentry, LogRocket 等監控服務
    if (process.env.NODE_ENV === 'development') {
      console.log('📊 Error reported to monitoring service:', errorDetails);
    }
  }

  // 重試機制
  async retry<T>(
    operation: () => Promise<T>,
    context?: Record<string, unknown>
  ): Promise<T> {
    let lastError: ErrorDetails | null = null;
    
    for (let attempt = 0; attempt <= this.retryConfig.maxRetries; attempt++) {
      try {
        return await operation();
      } catch (error) {
        const errorDetails = this.handleError(error as Error, {
          ...context,
          attempt: attempt + 1,
          maxAttempts: this.retryConfig.maxRetries + 1
        });
        
        lastError = errorDetails;
        
        // 檢查是否可以重試
        if (attempt === this.retryConfig.maxRetries || 
            !this.retryConfig.retryCondition?.(errorDetails)) {
          break;
        }
        
        // 計算延遲時間
        const delay = this.calculateDelay(attempt);
        console.log(`🔄 Retrying in ${delay}ms (attempt ${attempt + 1}/${this.retryConfig.maxRetries + 1})`);
        
        await this.sleep(delay);
      }
    }
    
    throw lastError?.originalError || new Error('重試失敗');
  }

  // 計算重試延遲
  private calculateDelay(attempt: number): number {
    if (!this.retryConfig.exponentialBackoff) {
      return this.retryConfig.baseDelay;
    }
    
    const delay = this.retryConfig.baseDelay * Math.pow(2, attempt);
    return Math.min(delay, this.retryConfig.maxDelay);
  }

  // 睡眠函數
  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // 獲取錯誤日誌
  getErrorLog(): ErrorDetails[] {
    return [...this.errorLog];
  }

  // 清除錯誤日誌
  clearErrorLog(): void {
    this.errorLog = [];
    if (typeof window !== 'undefined') {
      localStorage.removeItem('errorLog');
    }
  }

  // 獲取錯誤統計
  getErrorStats(): Record<string, number> {
    const stats: Record<string, number> = {};
    
    this.errorLog.forEach(error => {
      stats[error.type] = (stats[error.type] || 0) + 1;
    });
    
    return stats;
  }

  // 類型守衛
  private isErrorDetails(obj: unknown): obj is ErrorDetails {
    return typeof obj === 'object' && obj !== null && 'type' in obj;
  }
}

// 導出單例
export const errorHandler = new ErrorHandler();

// 設置全域錯誤監聽器
if (typeof window !== 'undefined') {
  window.addEventListener('error', (event) => {
    errorHandler.handleError(event.error, {
      filename: event.filename,
      lineno: event.lineno,
      colno: event.colno
    });
  });

  window.addEventListener('unhandledrejection', (event) => {
    // 安全地處理 event.reason，可能是任何類型
    const errorMessage = 'Unhandled Promise Rejection';
    let originalError: Error;
    
    if (event.reason instanceof Error) {
      originalError = event.reason;
    } else if (typeof event.reason === 'string') {
      originalError = new Error(event.reason);
    } else if (event.reason && typeof event.reason === 'object') {
      // 嘗試從物件中提取錯誤訊息
      const message = event.reason.message || event.reason.toString() || errorMessage;
      originalError = new Error(message);
    } else {
      originalError = new Error(errorMessage);
    }
    
    errorHandler.handleError(originalError, {
      type: 'unhandledPromiseRejection',
      originalReason: event.reason
    });
  });
}

export default errorHandler; 