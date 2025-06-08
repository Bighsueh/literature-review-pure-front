import React from 'react';
import { useAppStore } from '../../../stores/appStore';
import ProgressBar from '../../common/ProgressBar/ProgressBar';
import { ProcessingStage } from '../../../types/api';

const ProgressDisplay: React.FC = () => {
  const { progress } = useAppStore();
  
  const isIdle = progress.currentStage === 'idle' && !progress.isProcessing;
  
  const getStageTitle = (stage: ProcessingStage): string => {
    if (isIdle) return '處理完成';
    const titles: Record<ProcessingStage, string> = {
      idle: '準備就緒',
      uploading: '上傳檔案',
      analyzing: '分析句子類型',
      saving: '儲存結果',
      extracting: '提取關鍵詞',
      searching: '搜尋相關句子',
      generating: '生成回答',
      completed: '處理完成',
      error: '處理錯誤'
    };
    
    return titles[stage] || '處理中';
  };
  
  const getStageDescription = (stage: ProcessingStage): string => {
    if (isIdle) return '系統已準備好，可開始新的處理任務。';
    const descriptions: Record<ProcessingStage, string> = {
      idle: '系統已準備好處理檔案或查詢',
      uploading: '正在將檔案發送到 split_sentences 服務...',
      analyzing: '使用 n8n API 逐句分析 OD/CD 類型...',
      saving: '正在儲存處理結果到本地...',
      extracting: '從您的查詢中提取關鍵詞...',
      searching: '在已處理的句子中搜尋相關定義...',
      generating: '基於找到的定義生成回答...',
      completed: '處理已完成！',
      error: '處理過程中發生錯誤，請重試'
    };
    
    return descriptions[stage] || '';
  };
  
  // 渲染特定階段的詳細資訊
  const renderStageDetails = () => {
    const { currentStage, details } = progress;
    
    if (!details) return null;
    
    switch (currentStage) {
      case 'analyzing':
        return (
          <div className="mt-2 text-sm">
            {details.message && <p>{details.message}</p>}
            {details.currentSentence && (
              <div className="mt-1 p-2 bg-gray-50 rounded text-xs">
                <p className="font-medium">當前處理句子:</p>
                <p className="italic mt-1">
                  {typeof details.currentSentence === 'string'
                    ? details.currentSentence
                    : details.currentSentence.sentence || JSON.stringify(details.currentSentence)}
                </p>
              </div>
            )}
            {details.processed && details.total && (
              <p className="text-right text-xs text-gray-500 mt-1">
                {details.processed}/{details.total} 句子
              </p>
            )}
          </div>
        );
      
      case 'extracting':
        return (
          <div className="mt-2">
            {details.keywords && (
              <div className="flex flex-wrap gap-1 mt-1">
                {details.keywords.map((keyword: string, index: number) => (
                  <span 
                    key={index} 
                    className="inline-block bg-blue-100 text-blue-800 text-xs px-2 py-0.5 rounded"
                  >
                    {keyword}
                  </span>
                ))}
              </div>
            )}
          </div>
        );
      
      case 'searching':
        if (details.odSentences || details.cdSentences) {
          return (
            <div className="mt-2 text-sm">
              <div className="flex justify-between mb-1">
                <span>操作型定義 (OD):</span>
                <span className="font-medium">{details.odSentences?.length || 0}</span>
              </div>
              <div className="flex justify-between mb-1">
                <span>概念型定義 (CD):</span>
                <span className="font-medium">{details.cdSentences?.length || 0}</span>
              </div>
              <div className="flex justify-between">
                <span>總計:</span>
                <span className="font-medium">{details.total || 0}</span>
              </div>
            </div>
          );
        }
        return null;
      
      case 'error':
        return (
          <div className="mt-2 text-sm text-red-600">
            <p className="font-medium">錯誤信息:</p>
            <p className="mt-1">{progress.error || '未知錯誤'}</p>
          </div>
        );
      
      default:
        if (typeof details === 'string') {
          return <p className="mt-2 text-sm">{details}</p>;
        }
        return null;
    }
  };

  return (
    <div className="bg-white rounded-lg p-4 border border-gray-200 shadow-sm">
      <h3 className="text-base font-medium text-gray-800">
        {getStageTitle(progress.currentStage)}
      </h3>
      
      <p className="text-sm text-gray-500 mt-1">
        {getStageDescription(progress.currentStage)}
      </p>
      
      <div className="mt-3">
        <ProgressBar 
          progress={isIdle ? 100 : progress.percentage} 
          stage={isIdle ? 'completed' : progress.currentStage}
          size="md"
          showLabel={true}
        />
      </div>
      
      {!isIdle && renderStageDetails()}
    </div>
  );
};

export default ProgressDisplay;
