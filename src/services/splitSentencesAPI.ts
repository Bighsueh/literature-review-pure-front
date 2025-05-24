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
   * @returns 句子對象陣列，包含頁碼和句子文本
   */
  async processFile(file: File): Promise<SentenceWithPage[]> {
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
      let extractedSentences: SentenceWithPage[] = [];
      
      if (response.data.data && response.data.data.sentences) {
        // 如果響應包含 data.sentences 格式
        const sentences = response.data.data.sentences;
        extractedSentences = this.normalizeSentences(sentences, file.name);
      } else if (response.data.sentences) {
        // 如果響應直接包含 sentences 格式
        const sentences = response.data.sentences;
        extractedSentences = this.normalizeSentences(sentences, file.name);
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
   * 將不同格式的句子數據正規化為包含頁碼的句子對象
   * @param sentences 可能是字符串數組或帶頁碼的句子對象數組
   * @param fileName 檔案名稱
   * @returns 正規化後的句子對象數組，包含頁碼和檔案名稱
   */
  private normalizeSentences(sentences: string[] | SentenceWithPage[], fileName: string): SentenceWithPage[] {
    if (sentences.length === 0) {
      return [];
    }
    
    // 檢查第一個元素來判斷數組類型
    if (typeof sentences[0] === 'string') {
      // 如果是字符串數組，轉換為對象數組，頁碼預設為1
      return (sentences as string[]).map(sentence => ({
        sentence,
        page: 1,
        fileName: fileName
      }));
    } else {
      // 如果是對象數組，確保每個對象都有檔案名稱
      return (sentences as SentenceWithPage[]).map(item => ({
        ...item,
        fileName: fileName
      }));
    }
  }
}

export const splitSentencesAPI = new SplitSentencesAPI();
