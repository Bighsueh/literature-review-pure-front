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
   * 批次檢查多個句子是否為 OD (操作型定義) 或 CD (概念型定義)，並平行處理
   * @param sentences 要檢查的句子陣列
   * @returns 檢查結果陣列，包含每個句子的類型和原因
   */
  async checkOdCdBatch(sentences: string[]): Promise<{ sentence: string; result: N8nOdCdResponse }[]> {
    if (!sentences || sentences.length === 0) {
      return [];
    }

    const workerEndpoints = API_CONFIG.n8n.endpoints.checkOdCdWorkers;
    const results: { sentence: string; result: N8nOdCdResponse }[] = [];
    const BATCH_SIZE = 10; // 一次最多處理 10 個請求
    
    // 複製一份句子作為任務佇列
    const taskQueue = [...sentences];
    
    // 處理一批句子的函數
    const processNextBatch = async (): Promise<void> => {
      if (taskQueue.length === 0) {
        return;
      }
      
      // 取出下一批任務 (最多 BATCH_SIZE 個)
      const batchTasks = taskQueue.splice(0, BATCH_SIZE);
      console.log(`開始處理新的一批 ${batchTasks.length} 個句子`);
      
      // 創建當前批次的所有 Promise
      const batchPromises = batchTasks.map((sentence, index) => {
        // 為每個句子選擇一個 worker
        const workerIndex = sentence.length % workerEndpoints.length;
        const selectedWorker = workerEndpoints[workerIndex];
        
        console.log(`批次處理：使用 worker ${workerIndex + 1} 處理句子 ${index + 1}/${batchTasks.length}`);
        
        // 返回處理此句子的 Promise
        return this.client.post<N8nOdCdResponse>(selectedWorker, { sentence })
          .then(response => {
            return { sentence, result: response.data };
          })
          .catch(error => {
            console.error(`處理句子 "${sentence}" 時發生錯誤:`, error);
            
            let apiError: APIError;
            if (axios.isAxiosError(error)) {
              apiError = {
                message: error.message,
                code: error.code || 'UNKNOWN',
                details: error.response?.data
              };
            } else {
              apiError = {
                message: 'Failed to check OD/CD',
                code: 'UNKNOWN_ERROR'
              } as APIError;
            }
            
            // 返回錯誤信息和原始句子
            return { 
              sentence, 
              result: {
                type: 'error',
                reason: apiError.message,
                error: apiError
              } as unknown as N8nOdCdResponse 
            };
          });
      });
      
      // 等待當前批次的所有請求完成
      const batchResults = await Promise.allSettled(batchPromises);
      
      // 處理結果
      batchResults.forEach((result, index) => {
        if (result.status === 'fulfilled') {
          results.push(result.value);
        } else {
          // Promise 被拒絕的情況，添加一個錯誤結果
          const sentence = batchTasks[index];
          console.error(`批次處理：句子 "${sentence}" 的 Promise 被拒絕:`, result.reason);
          
          results.push({
            sentence,
            result: {
              type: 'error',
              reason: '處理請求時發生未知錯誤',
              error: { message: result.reason?.message || 'Unknown error', code: 'PROMISE_REJECTED' }
            } as unknown as N8nOdCdResponse
          });
        }
      });
      
      // 處理下一批
      if (taskQueue.length > 0) {
        await processNextBatch();
      }
    };
    
    // 開始處理第一批
    await processNextBatch();
    
    return results;
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
