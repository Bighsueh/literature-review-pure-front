// services/splitSentencesAPI.ts
import axios from 'axios';
import { API_CONFIG } from '../constants/apiConfig';
import { SplitSentencesResponse, APIError, SentenceWithPage } from '../types/api';

export class SplitSentencesAPI {
  private client = axios.create({
    baseURL: API_CONFIG.splitSentences.baseUrl,
    timeout: 30000 // 30 秒超時
  });

  /**
   * 將 PDF 檔案發送到分句服務進行處理
   * @param file PDF 檔案
   * @returns 句子陣列
   */
  async processFile(file: File): Promise<string[]> {
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await this.client.post<SplitSentencesResponse>(
        API_CONFIG.splitSentences.endpoint,
        formData,
        {
          headers: {
            'accept': 'application/json',
            'Content-Type': 'multipart/form-data'
          }
        }
      );

      // 處理不同的響應格式
      let extractedSentences: string[] = [];
      
      if (response.data.data && response.data.data.sentences) {
        // 如果響應包含 data.sentences 格式
        const sentences = response.data.data.sentences;
        extractedSentences = this.extractSentenceStrings(sentences);
      } else if (response.data.sentences) {
        // 如果響應直接包含 sentences 格式
        const sentences = response.data.sentences;
        extractedSentences = this.extractSentenceStrings(sentences);
      } else {
        throw new Error('Invalid API response format: sentences not found');
      }
      
      return extractedSentences;
    } catch (error) {
      console.error('Split sentences API error:', error);
      
      if (axios.isAxiosError(error)) {
        const apiError: APIError = {
          message: error.message,
          code: error.code || 'UNKNOWN',
          details: error.response?.data
        };
        throw apiError;
      }
      
      throw {
        message: 'Failed to process file',
        code: 'UNKNOWN_ERROR'
      } as APIError;
    }
  }

  /**
   * 從不同格式的數據中提取句子字符串
   * @param sentences 可能是字符串數組或帶頁碼的句子對象數組
   * @returns 提取的純句子字符串數組
   */
  private extractSentenceStrings(sentences: string[] | SentenceWithPage[]): string[] {
    if (sentences.length === 0) {
      return [];
    }
    
    // 檢查第一個元素來判斷數組類型
    if (typeof sentences[0] === 'string') {
      // 如果是字符串數組，直接返回
      return sentences as string[];
    } else {
      // 如果是對象數組，提取 sentence 屬性
      return (sentences as SentenceWithPage[]).map(item => item.sentence);
    }
  }
}

export const splitSentencesAPI = new SplitSentencesAPI();
