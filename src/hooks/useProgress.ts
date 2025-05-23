// hooks/useProgress.ts
import { useCallback } from 'react';
import { useAppStore } from '../stores/appStore';
import { ProcessingStage } from '../types/api';

type ProgressStepConfig = {
  stage: ProcessingStage;
  percentage: number;
  message: string;
};

export const useProgress = () => {
  const { setProgress, progress, resetProgress } = useAppStore();

  /**
   * 設置當前進度狀態
   */
  const updateProgress = useCallback((stage: ProcessingStage, percentage: number, details?: any) => {
    setProgress({
      currentStage: stage,
      percentage,
      details,
      isProcessing: stage !== 'completed' && stage !== 'error' && stage !== 'idle'
    });
  }, [setProgress]);

  /**
   * 模擬檔案處理進度
   */
  const simulateFileProcessing = useCallback(async (totalSentences: number) => {
    const steps: ProgressStepConfig[] = [
      { stage: 'uploading', percentage: 10, message: '正在上傳檔案...' },
      { stage: 'analyzing', percentage: 20, message: '開始分析句子類型...' },
      { stage: 'saving', percentage: 95, message: '儲存處理結果...' },
      { stage: 'completed', percentage: 100, message: '檔案處理完成！' }
    ];

    // 執行初始階段
    updateProgress(steps[0].stage, steps[0].percentage, steps[0].message);
    await new Promise(resolve => setTimeout(resolve, 1000));

    // 執行分析階段 (逐句模擬)
    updateProgress(steps[1].stage, steps[1].percentage, steps[1].message);
    await new Promise(resolve => setTimeout(resolve, 500));

    // 逐句進度更新
    for (let i = 0; i < totalSentences; i++) {
      const progress = 20 + (i / totalSentences) * 70;
      updateProgress('analyzing', progress, {
        message: `分析第 ${i+1}/${totalSentences} 個句子`,
        processed: i + 1,
        total: totalSentences
      });
      await new Promise(resolve => setTimeout(resolve, 500));
    }

    // 執行儲存階段
    updateProgress(steps[2].stage, steps[2].percentage, steps[2].message);
    await new Promise(resolve => setTimeout(resolve, 1000));

    // 完成
    updateProgress(steps[3].stage, steps[3].percentage, steps[3].message);
  }, [updateProgress]);

  /**
   * 模擬查詢處理進度
   */
  const simulateQueryProcessing = useCallback(async (steps: ProgressStepConfig[]) => {
    for (const step of steps) {
      updateProgress(step.stage, step.percentage, step.message);
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
  }, [updateProgress]);

  return {
    updateProgress,
    simulateFileProcessing,
    simulateQueryProcessing,
    currentProgress: progress,
    resetProgress
  };
};
