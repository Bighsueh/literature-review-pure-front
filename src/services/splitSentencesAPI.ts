// services/splitSentencesAPI.ts
import axios from 'axios';
import { API_CONFIG } from '../constants/apiConfig';
import { SplitSentencesResponse, APIError } from '../types/api';

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
            'Content-Type': 'multipart/form-data'
          }
        }
      );

      return response.data.sentences;
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
}

export const splitSentencesAPI = new SplitSentencesAPI();
