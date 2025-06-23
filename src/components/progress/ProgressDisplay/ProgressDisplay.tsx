import React from 'react';
import { useAppStore } from '../../../stores/appStore';
import { useWorkspace } from '../../../contexts/WorkspaceContext';
import { useWorkspaceFileStore } from '../../../stores/workspace/workspaceFileStore';
import ProgressBar from '../../common/ProgressBar/ProgressBar';
import { ProcessingStage } from '../../../types/api';

const ProgressDisplay: React.FC = () => {
  const { progress } = useAppStore();
  const { currentWorkspace } = useWorkspace();
  const { uploadingFiles } = useWorkspaceFileStore(currentWorkspace?.id || '');
  
  // 檢查是否有工作區上傳進度
  const hasWorkspaceUploads = Object.keys(uploadingFiles).length > 0;
  const isIdle = progress.currentStage === 'idle' && !progress.isProcessing && !hasWorkspaceUploads;
  
  const getStageTitle = (stage: ProcessingStage): string => {
    if (hasWorkspaceUploads) return '檔案上傳中';
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
    if (hasWorkspaceUploads) return '正在上傳檔案到伺服器...';
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

  // 計算整體進度
  const getOverallProgress = (): number => {
    if (hasWorkspaceUploads) {
      const uploadProgresses = Object.values(uploadingFiles).map(u => u.progress);
      return uploadProgresses.reduce((sum, prog) => sum + prog, 0) / uploadProgresses.length;
    }
    return isIdle ? 100 : progress.percentage;
  };

  // 渲染工作區上傳詳情
  const renderWorkspaceUploadDetails = () => {
    if (!hasWorkspaceUploads) return null;
    
    return (
      <div className="mt-2 text-sm">
        <p className="font-medium text-gray-700 mb-2">上傳中的檔案：</p>
        <div className="space-y-1">
          {Object.entries(uploadingFiles).map(([uploadId, { fileName, progress }]) => (
            <div key={uploadId} className="flex justify-between items-center text-xs">
              <span className="truncate flex-1 mr-2">{fileName}</span>
              <span className="text-gray-600">{Math.round(progress)}%</span>
            </div>
          ))}
        </div>
      </div>
    );
  };

  // 渲染基本進度詳情
  const renderBasicDetails = () => {
    if (!progress.details || isIdle || hasWorkspaceUploads) return null;
    
    return (
      <div className="mt-2 text-sm text-gray-600">
        <p>{typeof progress.details === 'string' ? progress.details : '處理中...'}</p>
        {progress.error && (
          <div className="mt-2 text-sm text-red-600">
            <p className="font-medium">錯誤信息:</p>
            <p className="mt-1">{progress.error}</p>
          </div>
        )}
      </div>
    );
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
          progress={getOverallProgress()} 
          stage={isIdle ? 'completed' : progress.currentStage}
          size="md"
          showLabel={true}
        />
      </div>
      
      {renderWorkspaceUploadDetails()}
      {renderBasicDetails()}
    </div>
  );
};

export default ProgressDisplay;
