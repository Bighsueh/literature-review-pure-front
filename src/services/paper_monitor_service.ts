import { apiService, PaperStatusResponse } from './api_service';

interface PaperMonitor {
  paperId: string;
  intervalId: NodeJS.Timeout;
  onProgress: (status: PaperStatusResponse) => void;
  onComplete: (status: PaperStatusResponse) => void;
  onError: (error: string) => void;
}

class PaperMonitorService {
  private monitors = new Map<string, PaperMonitor>();
  private readonly pollInterval = 2000; // 每2秒查詢一次

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

    const intervalId = setInterval(async () => {
      try {
        const result = await apiService.getPaperStatus(paperId);
        
        if (result.success && result.data) {
          const status = result.data;
          
          callbacks.onProgress(status);
          
          if (status.status === 'completed') {
            this.stopMonitoring(paperId);
            callbacks.onComplete(status);
          } else if (status.status === 'error') {
            this.stopMonitoring(paperId);
            callbacks.onError(status.error_message || 'Processing failed without a specific message.');
          }
        } else {
          // API 調用失敗，這也可能是一個暫時性錯誤
          console.warn(`Failed to get paper status for ${paperId}:`, result.error);
          // 在這種情況下我們不停止監控，因為後端可能只是暫時不可用
        }
      } catch (error) {
        console.error(`Error monitoring paper ${paperId}:`, error);
        this.stopMonitoring(paperId);
        callbacks.onError(error instanceof Error ? error.message : 'An unknown error occurred while polling for status.');
      }
    }, this.pollInterval);

    this.monitors.set(paperId, {
      paperId,
      intervalId,
      ...callbacks,
    });

    console.log(`Started monitoring paper: ${paperId}`);
  }

  /**
   * 停止監控論文
   */
  stopMonitoring(paperId: string): void {
    const monitor = this.monitors.get(paperId);
    if (monitor) {
      clearInterval(monitor.intervalId);
      this.monitors.delete(paperId);
      console.log(`Stopped monitoring paper: ${paperId}`);
    }
  }

  /**
   * 停止所有監控
   */
  stopAllMonitoring(): void {
    for (const [paperId] of this.monitors) {
      this.stopMonitoring(paperId);
    }
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
}

// 導出單例實例
export const paperMonitorService = new PaperMonitorService();
export default paperMonitorService; 