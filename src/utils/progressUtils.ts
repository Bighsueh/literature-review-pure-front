// utils/progressUtils.ts
import { ProcessingStage } from '../types/api';

export interface ProgressStep {
  stage: ProcessingStage;
  percentage: number;
  message: string;
  delay?: number; // 毫秒
}

/**
 * 根據處理階段取得顏色
 */
export const getStageColor = (stage: ProcessingStage): string => {
  const colorMap: Record<ProcessingStage, string> = {
    'idle': 'gray',
    'uploading': 'blue',
    'analyzing': 'purple',
    'saving': 'green',
    'extracting': 'orange',
    'searching': 'teal',
    'generating': 'indigo',
    'completed': 'green',
    'error': 'red'
  };
  
  return colorMap[stage] || 'gray';
};

/**
 * 檔案處理進度模擬步驟
 */
export const getFileProcessingSteps = (totalSentences: number): ProgressStep[] => [
  { stage: 'uploading', percentage: 10, message: '正在上傳檔案...', delay: 1000 },
  { stage: 'analyzing', percentage: 20, message: '開始分析句子類型...', delay: 500 },
  { stage: 'saving', percentage: 95, message: '儲存處理結果...', delay: 1000 },
  { stage: 'completed', percentage: 100, message: '檔案處理完成！', delay: 500 }
];

/**
 * 查詢處理進度模擬步驟
 */
export const getQueryProcessingSteps = (): ProgressStep[] => [
  { stage: 'extracting', percentage: 10, message: '提取查詢關鍵詞...', delay: 800 },
  { stage: 'extracting', percentage: 30, message: '關鍵詞提取完成', delay: 500 },
  { stage: 'searching', percentage: 50, message: '搜尋相關定義句子...', delay: 1000 },
  { stage: 'generating', percentage: 70, message: '生成智能回答...', delay: 1500 },
  { stage: 'completed', percentage: 100, message: '回答生成完成！', delay: 500 }
];

/**
 * 計算兩個進度百分比之間的中間值
 */
export const interpolateProgress = (
  start: number, 
  end: number, 
  steps: number, 
  currentStep: number
): number => {
  return start + ((end - start) / steps) * currentStep;
};
