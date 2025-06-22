import { apiService, PaperStatusResponse } from './api_service';

interface PaperMonitor {
  paperId: string;
  intervalId: NodeJS.Timeout;
  retryCount: number;
  maxRetries: number;
  baseInterval: number;
  currentInterval: number;
  lastSuccessTime: number;
  onProgress: (status: PaperStatusResponse) => void;
  onComplete: (status: PaperStatusResponse) => void;
  onError: (error: string) => void;
}

// 錯誤快取 - 避免重複請求明顯失敗的資源
interface ErrorCache {
  [paperId: string]: {
    errorCount: number;
    lastErrorTime: number;
    errorMessage: string;
    nextRetryTime: number;
  }
}

class PaperMonitorService {
  private monitors = new Map<string, PaperMonitor>();
  private readonly baseInterval = 2000; // 基礎間隔 2秒
  private readonly maxInterval = 30000; // 最大間隔 30秒
  private readonly maxRetries = 5; // 最大重試次數
  private readonly errorCacheDuration = 60000; // 錯誤快取持續時間 1分鐘
  private errorCache: ErrorCache = {};

  /**
   * 計算指數退避間隔
   */
  private calculateBackoffInterval(retryCount: number, baseInterval: number): number {
    const exponentialDelay = baseInterval * Math.pow(2, Math.min(retryCount, 4));
    const jitter = Math.random() * 1000; // 添加隨機延遲避免同時重試
    return Math.min(exponentialDelay + jitter, this.maxInterval);
  }

  /**
   * 檢查是否應該跳過請求（基於錯誤快取）
   */
  private shouldSkipRequest(paperId: string): boolean {
    const cached = this.errorCache[paperId];
    if (!cached) return false;

    const now = Date.now();
    
    // 如果錯誤快取過期，清除快取
    if (now - cached.lastErrorTime > this.errorCacheDuration) {
      delete this.errorCache[paperId];
      return false;
    }

    // 如果還沒到下次重試時間，跳過請求
    return now < cached.nextRetryTime;
  }

  /**
   * 更新錯誤快取
   */
  private updateErrorCache(paperId: string, error: string): void {
    const now = Date.now();
    const existing = this.errorCache[paperId];
    
    this.errorCache[paperId] = {
      errorCount: existing ? existing.errorCount + 1 : 1,
      lastErrorTime: now,
      errorMessage: error,
      nextRetryTime: now + this.calculateBackoffInterval(
        existing ? existing.errorCount : 0, 
        this.baseInterval
      )
    };
  }

  /**
   * 清除錯誤快取（成功時調用）
   */
  private clearErrorCache(paperId: string): void {
    delete this.errorCache[paperId];
  }

  /**
   * 執行單次狀態檢查
   */
  private async performStatusCheck(paperId: string): Promise<{
    success: boolean;
    status?: PaperStatusResponse;
    error?: string;
  }> {
    try {
      // 檢查錯誤快取
      if (this.shouldSkipRequest(paperId)) {
        const cached = this.errorCache[paperId];
        const waitTime = Math.round((cached.nextRetryTime - Date.now()) / 1000);
        console.log(`Skipping request for ${paperId}, retry in ${waitTime}s`);
        return { success: false, error: `Waiting ${waitTime}s before retry` };
      }

      const result = await apiService.getPaperStatus(paperId);
      
      if (result.success && result.data) {
        // 成功時清除錯誤快取
        this.clearErrorCache(paperId);
        return { success: true, status: result.data };
      } else {
        const error = result.error || 'API call failed without specific error';
        
        // 特殊處理 404 錯誤：檢查是否是暫時的問題
        if (error.includes('404') || error.includes('Not Found')) {
          // 對於 404 錯誤，使用更寬鬆的重試策略
          console.warn(`Got 404 for ${paperId}, this might be a temporary routing issue`);
          this.updateErrorCache(paperId, `Temporary routing issue: ${error}`);
          
          // 檢查是否連續多次 404（可能是檔案真的不存在）
          const cached = this.errorCache[paperId];
          if (cached && cached.errorCount >= 3) {
            return { 
              success: false, 
              error: `檔案可能不存在或已被刪除 (${cached.errorCount} consecutive 404s)` 
            };
          }
        } else {
          this.updateErrorCache(paperId, error);
        }
        
        return { success: false, error };
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      
      // 網路錯誤的特殊處理
      if (errorMessage.includes('fetch') || errorMessage.includes('network')) {
        console.warn(`Network error for ${paperId}:`, errorMessage);
        this.updateErrorCache(paperId, `Network issue: ${errorMessage}`);
      } else {
        this.updateErrorCache(paperId, errorMessage);
      }
      
      return { success: false, error: errorMessage };
    }
  }

  /**
   * 開始監控論文處理進度
   */
  startMonitoring(
    paperId: string,
    callbacks: {
      onProgress: (status: PaperStatusResponse) => void;
      onComplete: (status: PaperStatusResponse) => void;
      onError: (error: string) => void;
    }
  ): void {
    if (this.monitors.has(paperId)) {
      this.stopMonitoring(paperId);
    }

    const monitor: PaperMonitor = {
      paperId,
      retryCount: 0,
      maxRetries: this.maxRetries,
      baseInterval: this.baseInterval,
      currentInterval: this.baseInterval,
      lastSuccessTime: Date.now(),
      intervalId: null as unknown as NodeJS.Timeout,
      ...callbacks
    };

    const pollFunction = async () => {
      const result = await this.performStatusCheck(paperId);
      
      if (result.success && result.status) {
        // 成功獲取狀態
        monitor.retryCount = 0;
        monitor.currentInterval = this.baseInterval;
        monitor.lastSuccessTime = Date.now();
        
        const status = result.status;
        callbacks.onProgress(status);
        
        if (status.status === 'completed') {
          this.stopMonitoring(paperId);
          
          // 論文處理完成時，嘗試同步句子資料
          await this.syncPaperDataOnCompletion(paperId);
          
          callbacks.onComplete(status);
          return;
        } else if (status.status === 'error') {
          this.stopMonitoring(paperId);
          callbacks.onError(status.error_message || 'Processing failed without a specific message.');
          return;
        }
      } else {
        // 請求失敗
        monitor.retryCount++;
        
        // 更新輪詢間隔（指數退避）
        monitor.currentInterval = this.calculateBackoffInterval(
          monitor.retryCount, 
          monitor.baseInterval
        );
        
        console.warn(`Failed to get paper status for ${paperId} (attempt ${monitor.retryCount}/${monitor.maxRetries}):`, result.error);
        
        // 檢查是否達到最大重試次數
        if (monitor.retryCount >= monitor.maxRetries) {
          this.stopMonitoring(paperId);
          callbacks.onError(`Max retries (${monitor.maxRetries}) exceeded for paper ${paperId}. Last error: ${result.error}`);
          return;
        }
        
        // 檢查是否長時間未成功（5分鐘）
        const timeSinceLastSuccess = Date.now() - monitor.lastSuccessTime;
        if (timeSinceLastSuccess > 300000) { // 5分鐘
          this.stopMonitoring(paperId);
          callbacks.onError(`Monitoring timeout for paper ${paperId}. No successful response in ${Math.round(timeSinceLastSuccess / 60000)} minutes.`);
          return;
        }
      }
      
      // 設置下次輪詢
      monitor.intervalId = setTimeout(pollFunction, monitor.currentInterval);
    };

    // 立即執行第一次檢查
    pollFunction();
    
    this.monitors.set(paperId, monitor);
    console.log(`Started monitoring paper: ${paperId} with base interval ${this.baseInterval}ms`);
  }

  /**
   * 論文處理完成時同步資料
   */
  private async syncPaperDataOnCompletion(paperId: string): Promise<void> {
    try {
      console.log(`Syncing data for completed paper: ${paperId}`);
      
      // 導入 paperService（動態導入避免循環依賴）
      const { paperService } = await import('./paper_service');
      
      // 同步論文句子資料到前端
      const sentences = await paperService.syncPaperSentencesFromBackend(paperId);
      
      if (sentences.length > 0) {
        console.log(`Successfully synced ${sentences.length} sentences for paper ${paperId}`);
        
        // 觸發全局狀態更新（如果有其他組件在監聽）
        window.dispatchEvent(new CustomEvent('paperDataSynced', {
          detail: { paperId, sentencesCount: sentences.length }
        }));
      } else {
        console.warn(`No sentences found for completed paper ${paperId}`);
      }
    } catch (error) {
      console.error(`Error syncing data for paper ${paperId}:`, error);
      // 不拋出錯誤，避免影響完成回調
    }
  }

  /**
   * 停止監控論文
   */
  stopMonitoring(paperId: string): void {
    const monitor = this.monitors.get(paperId);
    if (monitor) {
      if (monitor.intervalId) {
        clearTimeout(monitor.intervalId);
      }
      this.monitors.delete(paperId);
      // 清除相關的錯誤快取
      this.clearErrorCache(paperId);
      console.log(`Stopped monitoring paper: ${paperId}`);
    }
  }

  /**
   * 停止所有監控
   */
  stopAllMonitoring(): void {
    for (const paperId of this.monitors.keys()) {
      this.stopMonitoring(paperId);
    }
    this.errorCache = {};
    console.log('Stopped all monitoring');
  }

  /**
   * 獲取當前監控的論文列表
   */
  getMonitoredPapers(): string[] {
    return Array.from(this.monitors.keys());
  }

  /**
   * 檢查是否正在監控某篇論文
   */
  isMonitoring(paperId: string): boolean {
    return this.monitors.has(paperId);
  }

  /**
   * 獲取監控統計資訊
   */
  getMonitoringStats(): {
    activeMonitors: number;
    errorCacheEntries: number;
    monitors: Array<{
      paperId: string;
      retryCount: number;
      currentInterval: number;
      lastSuccessTime: number;
    }>;
  } {
    const monitors = Array.from(this.monitors.values()).map(monitor => ({
      paperId: monitor.paperId,
      retryCount: monitor.retryCount,
      currentInterval: monitor.currentInterval,
      lastSuccessTime: monitor.lastSuccessTime
    }));

    return {
      activeMonitors: this.monitors.size,
      errorCacheEntries: Object.keys(this.errorCache).length,
      monitors
    };
  }

  /**
   * 手動清除錯誤快取（調試用）
   */
  clearAllErrorCache(): void {
    this.errorCache = {};
    console.log('Cleared all error cache');
  }

  /**
   * 強制重試某個論文的監控（忽略錯誤快取）
   */
  forceRetry(paperId: string): void {
    this.clearErrorCache(paperId);
    const monitor = this.monitors.get(paperId);
    if (monitor) {
      monitor.retryCount = 0;
      monitor.currentInterval = this.baseInterval;
      monitor.lastSuccessTime = Date.now();
      console.log(`Force retry for paper: ${paperId}`);
    }
  }
}

export const paperMonitorService = new PaperMonitorService();
export default paperMonitorService; 