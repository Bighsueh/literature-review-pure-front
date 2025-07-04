/**
 * 論文服務層
 * 整合 API 調用和本地狀態管理，提供高級的論文操作功能
 */

import { apiService } from './api_service';
import { localStorageService } from './localStorageService';
import { ProcessedSentence, FileMetadata } from '../types/file';
import { Message } from '../types/chat';

// 類型定義
interface PaperInfo {
  id: string;
  title: string;
  authors: string[];
  file_path: string;
  file_hash: string;
  upload_time: string;
  processing_status: string;
  selected: boolean;
  section_count: number;
  sentence_count: number;
}

interface QueryResponse {
  response: string;
  references?: Array<{
    id: string;
    paper_name: string;
    section_type: string;
    page_num: number;
    content_snippet: string;
  }>;
  selected_sections?: Array<{
    id: string;
    section_type: string;
    content: string;
  }>;
  analysis_focus?: string;
  source_summary?: {
    total_papers: number;
    papers_used: string[];
    sections_analyzed: string[];
    analysis_type: string;
  };
}

interface QueryRequest {
  query: string;
  paper_ids?: string[];
  max_results?: number;
}

export interface PaperUploadResult {
  success: boolean;
  file_id?: string;
  task_id?: string;
  message?: string;
  error?: string;
  duplicate?: boolean;
}

export interface PaperProcessingResult {
  success: boolean;
  processed_sentences?: ProcessedSentence[];
  message?: string;
  error?: string;
}

class PaperService {
  private refreshCallbacks: Array<() => void> = [];

  /**
   * 註冊刷新回調，用於多Client同步
   */
  onRefresh(callback: () => void): () => void {
    this.refreshCallbacks.push(callback);
    return () => {
      const index = this.refreshCallbacks.indexOf(callback);
      if (index > -1) {
        this.refreshCallbacks.splice(index, 1);
      }
    };
  }

  /**
   * 觸發所有刷新回調
   */
  private triggerRefresh(): void {
    this.refreshCallbacks.forEach(callback => {
      try {
        callback();
      } catch (error) {
        console.error('Error in refresh callback:', error);
      }
    });
  }

  // ===== 檔案管理 =====

  /**
   * 上傳 PDF 檔案並保存元資料
   */
  async uploadPdf(file: File): Promise<PaperUploadResult> {
    try {
      // 1. 上傳到後端
      const uploadResult = await apiService.uploadFile(file);
      
      if (!uploadResult.success || !uploadResult.data) {
        return {
          success: false,
          error: uploadResult.error || 'Upload failed',
        };
      }

      // 2. 保存本地元資料
      const metadata: FileMetadata = {
        id: uploadResult.data.paper_id,
        name: file.name,
        size: file.size,
        type: file.type,
        uploadedAt: new Date(),
      };

      await localStorageService.saveFileMetadata(metadata);

      // 3. 觸發刷新
      this.triggerRefresh();

      return {
        success: true,
        file_id: uploadResult.data.paper_id,
        task_id: uploadResult.data.task_id,
        message: uploadResult.data.message,
        duplicate: uploadResult.data.duplicate,
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  /**
   * 獲取所有論文（結合 API 和本地資料）
   */
  async getAllPapers(): Promise<PaperInfo[]> {
    try {
      const result = await apiService.getPapers();
      
      if (result.success && result.data) {
        // result.data 是 WorkspaceFile[]，需要轉換為 PaperInfo[]
        return result.data.map(file => ({
          id: file.id,
          title: file.title,
          authors: [],
          file_path: file.file_path,
          file_hash: file.file_hash,
          upload_time: file.upload_time,
          processing_status: file.processing_status,
          selected: file.selected,
          section_count: file.section_count,
          sentence_count: file.sentence_count,
        }));
      }
      
      // 如果 API 失敗，嘗試使用本地資料
      console.warn('API failed, falling back to local data:', result.error);
      const localMetadata = await localStorageService.getAllFileMetadata();
      
      return localMetadata.map(meta => ({
        id: meta.id,
        title: meta.name.replace('.pdf', ''),
        authors: [],
        file_path: meta.name,
        file_hash: '',
        upload_time: meta.uploadedAt.toISOString(),
        processing_status: 'pending',
        selected: false,
        section_count: 0,
        sentence_count: 0,
      }));
    } catch (error) {
      console.error('Error getting papers:', error);
      return [];
    }
  }

  /**
   * 切換論文選取狀態
   */
  async togglePaperSelection(paperId: string, selected: boolean): Promise<boolean> {
    try {
      const result = await apiService.togglePaperSelection(paperId, selected);
      
      if (result.success) {
        this.triggerRefresh();
        return true;
      }
      
      console.error('Failed to toggle paper selection:', result.error);
      return false;
    } catch (error) {
      console.error('Error toggling paper selection:', error);
      return false;
    }
  }

  /**
   * 批次設置論文選取狀態
   */
  async setBatchSelection(paperIds: string[], selected: boolean): Promise<boolean> {
    try {
      const result = await apiService.setBatchPaperSelection(paperIds, selected);
      
      if (result.success) {
        this.triggerRefresh();
        return true;
      }
      
      console.error('Failed to set batch selection:', result.error);
      return false;
    } catch (error) {
      console.error('Error setting batch selection:', error);
      return false;
    }
  }

  /**
   * 刪除論文
   */
  async deletePaper(paperId: string): Promise<boolean> {
    try {
      const result = await apiService.deletePaper(paperId);
      
      if (result.success) {
                 // 清理本地資料
         try {
           await localStorageService.getSentencesByFileId(paperId);
           // TODO: 實現句子刪除邏輯
         } catch (error) {
           console.warn('Error cleaning local data:', error);
         }
        
        this.triggerRefresh();
        return true;
      }
      
      console.error('Failed to delete paper:', result.error);
      return false;
    } catch (error) {
      console.error('Error deleting paper:', error);
      return false;
    }
  }

  // ===== 處理管理 =====

  /**
   * 開始處理選中的論文
   */
  async startProcessing(): Promise<boolean> {
    try {
      const result = await apiService.startProcessing();
      
      if (result.success) {
        this.triggerRefresh();
        return true;
      }
      
      console.error('Failed to start processing:', result.error);
      return false;
    } catch (error) {
      console.error('Error starting processing:', error);
      return false;
    }
  }

  /**
   * 停止當前處理
   */
  async stopProcessing(): Promise<boolean> {
    try {
      const result = await apiService.stopProcessing();
      
      if (result.success) {
        this.triggerRefresh();
        return true;
      }
      
      console.error('Failed to stop processing:', result.error);
      return false;
    } catch (error) {
      console.error('Error stopping processing:', error);
      return false;
    }
  }

  // ===== 查詢處理 =====

  /**
   * 執行智能查詢並保存對話記錄
   */
  async executeQuery(query: string, paperIds?: string[]): Promise<{
    success: boolean;
    response?: QueryResponse;
    error?: string;
  }> {
    try {
      const request: QueryRequest = {
        query,
        paper_ids: paperIds,
        max_results: 10,
      };

      const result = await apiService.query(request);
      
      if (result.success && result.data) {
        // 保存對話記錄
        try {
          const conversationId = 'default'; // 可以改為動態生成
          const existingMessages = await localStorageService.getConversation(conversationId) || [];
          
          const userMessage: Message = {
            id: crypto.randomUUID(),
            type: 'user',
            content: query,
            timestamp: new Date(),
          };
          
          const assistantMessage: Message = {
            id: crypto.randomUUID(),
            type: 'system',
            content: result.data.response,
            timestamp: new Date(),
            references: [],
            metadata: {
              query: query,
              processingTime: Date.now(),
            },
          };
          
          const updatedMessages = [...existingMessages, userMessage, assistantMessage];
          await localStorageService.saveConversation(conversationId, updatedMessages);
        } catch (error) {
          console.warn('Failed to save conversation:', error);
        }
        
        return {
          success: true,
          response: result.data,
        };
      }
      
      return {
        success: false,
        error: result.error || 'Query failed',
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  // ===== 本地資料管理 =====

  /**
   * 獲取論文的已處理句子
   */
  async getPaperSentences(paperId: string): Promise<ProcessedSentence[]> {
    try {
      return await localStorageService.getSentencesByFileId(paperId);
    } catch (error) {
      console.error('Error getting paper sentences:', error);
      return [];
    }
  }

  /**
   * 從後端獲取論文句子資料並同步到前端狀態
   */
  async syncPaperSentencesFromBackend(paperId: string): Promise<ProcessedSentence[]> {
    try {
      const result = await apiService.getPaperSentences(paperId);
      
      if (result.success && result.data) {
        // 轉換後端資料格式為前端格式
        const sentences: ProcessedSentence[] = result.data.sentences.map(sentence => ({
          id: sentence.id,
          content: sentence.content,
          type: sentence.type as 'OD' | 'CD' | 'OTHER' | 'UNKNOWN',
          reason: sentence.reason || '',
          pageNumber: sentence.pageNumber || 1,
          fileName: sentence.fileName,
          fileId: sentence.fileId,
          sentenceOrder: sentence.sentenceOrder,
          sectionId: sentence.sectionId,
          confidence: sentence.confidence,
          wordCount: sentence.wordCount
        }));
        
        // 同步到本地儲存
        await localStorageService.saveSentences(sentences);
        
        this.triggerRefresh();
        return sentences;
      }
      
      console.warn('Failed to sync sentences from backend:', result.error);
      return [];
    } catch (error) {
      console.error('Error syncing sentences from backend:', error);
      return [];
    }
  }

  /**
   * 獲取所有已選取論文的句子資料（從後端獲取）
   */
  async getAllSelectedPapersSentences(): Promise<{
    sentences: ProcessedSentence[];
    totalSentences: number;
    totalPapers: number;
    papers: Array<{ id: string; fileName: string; processingStatus: string }>;
  }> {
    try {
      const result = await apiService.getAllSelectedPapersSentences();
      
      if (result.success && result.data) {
        // 轉換後端資料格式為前端格式
        const sentences: ProcessedSentence[] = result.data.sentences.map(sentence => ({
          id: sentence.id,
          content: sentence.content,
          type: sentence.type as 'OD' | 'CD' | 'OTHER' | 'UNKNOWN',
          reason: sentence.reason || '',
          pageNumber: sentence.pageNumber || 1,
          fileName: sentence.fileName,
          fileId: sentence.fileId,
          sentenceOrder: sentence.sentenceOrder,
          sectionId: sentence.sectionId,
          confidence: sentence.confidence,
          wordCount: sentence.wordCount
        }));
        
        // 批次同步到本地儲存
        await localStorageService.saveSentences(sentences);
        
        this.triggerRefresh();
        
        return {
          sentences,
          totalSentences: result.data.total_sentences,
          totalPapers: result.data.total_papers,
          papers: result.data.papers.map(paper => ({
            id: paper.id,
            fileName: paper.fileName,
            processingStatus: paper.processing_status
          }))
        };
      }
      
      console.warn('Failed to get all sentences from backend:', result.error);
      return {
        sentences: [],
        totalSentences: 0,
        totalPapers: 0,
        papers: []
      };
    } catch (error) {
      console.error('Error getting all sentences from backend:', error);
      return {
        sentences: [],
        totalSentences: 0,
        totalPapers: 0,
        papers: []
      };
    }
  }

  /**
   * 檢查論文是否有可用的句子資料
   */
  async hasPaperSentences(paperId: string): Promise<boolean> {
    try {
      const result = await apiService.getPaperSentences(paperId);
      return result.success && result.data ? result.data.total_count > 0 : false;
    } catch (error) {
      console.error('Error checking paper sentences:', error);
      return false;
    }
  }

  /**
   * 檢查是否有任何已完成處理的論文
   */
  async hasAnyCompletedPapers(): Promise<boolean> {
    try {
      const papers = await this.getAllPapers();
      return Array.isArray(papers) && papers.some(paper => paper.processing_status === 'completed');
    } catch (error) {
      console.error('Error checking completed papers:', error);
      return false;
    }
  }

  /**
   * 保存處理後的句子（向後兼容性）
   */
  async savePaperSentences(sentences: ProcessedSentence[]): Promise<void> {
    try {
      await localStorageService.saveSentences(sentences);
      this.triggerRefresh();
    } catch (error) {
      console.error('Error saving sentences:', error);
      throw error;
    }
  }

  /**
   * 獲取對話記錄
   */
  async getConversation(conversationId = 'default'): Promise<Message[]> {
    try {
      return await localStorageService.getConversation(conversationId) || [];
    } catch (error) {
      console.error('Error getting conversation:', error);
      return [];
    }
  }

  /**
   * 清理所有本地資料
   */
  async clearAllData(): Promise<void> {
    try {
      await localStorageService.clearAll();
      this.triggerRefresh();
    } catch (error) {
      console.error('Error clearing data:', error);
      throw error;
    }
  }

  // ===== 服務狀態 =====

  /**
   * 檢查服務健康狀態
   */
  async checkServiceHealth(): Promise<{
    api: boolean;
    grobid: boolean;
    n8n: boolean;
    split_sentences: boolean;
    database: boolean;
  }> {
    try {
      const [healthResult, statusResult] = await Promise.all([
        apiService.healthCheck(),
        apiService.getServiceStatus(),
      ]);

      return {
        api: healthResult.success,
        grobid: statusResult.data?.grobid || false,
        n8n: statusResult.data?.n8n || false,
        split_sentences: statusResult.data?.split_sentences || false,
        database: statusResult.data?.database || false,
      };
    } catch (error) {
      console.error('Error checking service health:', error);
      return {
        api: false,
        grobid: false,
        n8n: false,
        split_sentences: false,
        database: false,
      };
    }
  }
}

// 導出單例實例
export const paperService = new PaperService();
export default paperService; 