// types/api.ts
export interface SplitSentencesResponse {
  sentences: string[];
  success?: boolean;
  data?: {
    sentences: string[];
  };
}

export interface N8nOdCdResponse {
  defining_type: string;
  reason: string;
}

export interface N8nKeywordResponse {
  output: {
    keywords: string[];
  };
}

export interface N8nOrganizeResponse {
  output: {
    response: string;
  };
}

export interface APIError {
  message: string;
  code: string;
  details?: Record<string, unknown>;
}

export type ProcessingStage = 
  | "idle"
  | "uploading"      // 上傳檔案
  | "analyzing"      // 分析句子類型
  | "saving"         // 儲存結果
  | "extracting"     // 提取關鍵詞
  | "searching"      // 搜尋相關句子  
  | "generating"     // 生成回答
  | "completed"      // 完成
  | "error";         // 錯誤
