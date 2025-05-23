// services/n8nAPI.ts
import axios from 'axios';
import { API_CONFIG } from '../constants/apiConfig';
import { N8nOdCdResponse, N8nKeywordResponse, N8nOrganizeResponse, APIError } from '../types/api';

export class N8nAPI {
  private client = axios.create({
    baseURL: API_CONFIG.n8n.baseUrl,
    timeout: 180000 // 3 分鐘超時（組織回答 API 需要較長時間）
  });

  /**
   * 檢查句子是否為 OD (操作型定義) 或 CD (概念型定義)
   * @param sentence 要檢查的句子
   * @returns 檢查結果，包含類型和原因
   */
  async checkOdCd(sentence: string): Promise<N8nOdCdResponse> {
    try {
      // 使用四個 worker 中的其中一個處理請求
      const workerEndpoints = API_CONFIG.n8n.endpoints.checkOdCdWorkers;
      
      // 選擇一個 worker (簡單的載均平衡方式，可以根據句子內容長度或隨機選擇)
      // 這裡使用句子長度模 4 來選擇 worker
      const workerIndex = sentence.length % workerEndpoints.length;
      const selectedWorker = workerEndpoints[workerIndex];
      
      console.log(`Using worker ${workerIndex + 1} for sentence with length ${sentence.length}`);
      
      const response = await this.client.post<N8nOdCdResponse>(
        selectedWorker,
        { sentence }
      );
      
      return response.data;
    } catch (error) {
      console.error('n8n OD/CD API error:', error);
      
      if (axios.isAxiosError(error)) {
        const apiError: APIError = {
          message: error.message,
          code: error.code || 'UNKNOWN',
          details: error.response?.data
        };
        throw apiError;
      }
      
      throw {
        message: 'Failed to check OD/CD',
        code: 'UNKNOWN_ERROR'
      } as APIError;
    }
  }

  /**
   * 從查詢中提取關鍵詞
   * @param query 使用者查詢
   * @returns 關鍵詞列表
   */
  async extractKeywords(query: string): Promise<N8nKeywordResponse[]> {
    try {
      const response = await this.client.post<N8nKeywordResponse[]>(
        API_CONFIG.n8n.endpoints.keywordExtraction,
        { query }
      );
      
      return response.data;
    } catch (error) {
      console.error('n8n Keyword API error:', error);
      
      if (axios.isAxiosError(error)) {
        const apiError: APIError = {
          message: error.message,
          code: error.code || 'UNKNOWN',
          details: error.response?.data
        };
        throw apiError;
      }
      
      throw {
        message: 'Failed to extract keywords',
        code: 'UNKNOWN_ERROR'
      } as APIError;
    }
  }

  /**
   * 根據提供的定義和查詢生成組織化回答
   * @param data 包含 OD, CD 和查詢的數據
   * @returns 組織化回答
   */
  async organizeResponse(data: {
    "operational definition": string[];
    "conceptual definition": string[];
    "query": string;
  }): Promise<N8nOrganizeResponse[]> {
    try {
      console.log('Sending organize request with data:', JSON.stringify(data, null, 2));
      
      // 確保所有字段均為字符串類型
      const requestData = {
        "operational definition": data["operational definition"],
        "conceptual definition": data["conceptual definition"],
        "query": data.query
      };
      
      const response = await this.client.post<N8nOrganizeResponse[]>(
        API_CONFIG.n8n.endpoints.organizeResponse,
        requestData
      );
      
      return response.data;
    } catch (error) {
      console.error('n8n Organize API error:', error);
      
      if (axios.isAxiosError(error)) {
        const apiError: APIError = {
          message: error.message,
          code: error.code || 'UNKNOWN',
          details: error.response?.data
        };
        throw apiError;
      }
      
      throw {
        message: 'Failed to organize response',
        code: 'UNKNOWN_ERROR'
      } as APIError;
    }
  }
}

export const n8nAPI = new N8nAPI();
