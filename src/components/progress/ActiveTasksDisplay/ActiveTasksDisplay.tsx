import React from 'react';
import { useAppStore } from '../../../stores/appStore';
import { useWorkspace } from '../../../contexts/WorkspaceContext';
import { useWorkspaceFileStore } from '../../../stores/workspace/workspaceFileStore';
import ProgressBar from '../../common/ProgressBar/ProgressBar';

const ActiveTasksDisplay: React.FC = () => {
  const activeTasks = useAppStore((state) => state.activeTasks);
  const isUploading = useAppStore((state) => state.isUploading);
  const { currentWorkspace } = useWorkspace();
  const { uploadingFiles } = useWorkspaceFileStore(currentWorkspace?.id || '');

  // 檢查是否有任何活動
  const hasWorkspaceUploads = Object.keys(uploadingFiles).length > 0;
  const hasGlobalTasks = activeTasks.length > 0;
  const hasAnyActivity = hasWorkspaceUploads || hasGlobalTasks || isUploading;

  if (!hasAnyActivity) {
    return (
      <div className="bg-white rounded-lg p-4 border border-gray-200 shadow-sm">
        <h3 className="text-base font-medium text-gray-800">處理狀態</h3>
        <p className="text-sm text-gray-500 mt-1">目前沒有正在處理的檔案</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg p-4 border border-gray-200 shadow-sm">
      <h3 className="text-base font-medium text-gray-800">
        活動任務 {(hasWorkspaceUploads || hasGlobalTasks) && 
          `(${Object.keys(uploadingFiles).length + activeTasks.length})`}
      </h3>

      {/* 全局上傳狀態 */}
      {isUploading && (
        <div className="mt-3 p-3 bg-blue-50 rounded border border-blue-200">
          <div className="flex items-center">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2"></div>
            <span className="text-sm text-blue-700">正在上傳檔案...</span>
          </div>
        </div>
      )}

      {/* 工作區上傳進度 */}
      {hasWorkspaceUploads && (
        <div className="mt-3">
          <p className="text-sm font-medium text-gray-600 mb-2">檔案上傳進度:</p>
          {Object.entries(uploadingFiles).map(([uploadId, { fileName, progress }]) => (
            <div key={uploadId} className="mb-3 last:mb-0">
              <div className="flex justify-between items-start mb-1">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-800 truncate">
                    {fileName}
                  </p>
                  <p className="text-xs text-gray-500 mt-0.5">
                    上傳中...
                  </p>
                </div>
                <span className="text-xs text-gray-600 ml-2">
                  {Math.round(progress)}%
                </span>
              </div>
              
              <ProgressBar 
                progress={progress} 
                stage={progress >= 100 ? 'completed' : 'uploading'}
                size="sm"
                showLabel={false}
              />
            </div>
          ))}
        </div>
      )}

      {/* 全局處理任務 */}
      {hasGlobalTasks && (
        <div className="mt-3">
          {hasWorkspaceUploads && <hr className="border-gray-200 mb-3" />}
          <p className="text-sm font-medium text-gray-600 mb-2">處理進度:</p>
          {activeTasks.map((task) => (
            <div key={task.paperId} className="mb-3 last:mb-0">
              <div className="flex justify-between items-start mb-1">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-800 truncate">
                    {task.filename}
                  </p>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {task.step}
                  </p>
                </div>
                <span className="text-xs text-gray-600 ml-2">
                  {Math.round(task.progress)}%
                </span>
              </div>
              
              <ProgressBar 
                progress={task.progress} 
                stage={
                  task.step.includes('錯誤') || task.step.includes('404') ? 'error' :
                  task.progress >= 100 ? 'completed' : 'analyzing'
                }
                size="sm"
                showLabel={false}
              />
              
              {(task.step.includes('錯誤') || task.step.includes('404') || task.step.includes('失敗')) && (
                <div className="mt-1 text-xs text-red-600 bg-red-50 p-2 rounded">
                  <p className="font-medium">處理遇到問題：</p>
                  <p className="mt-0.5">{task.step}</p>
                  <p className="mt-1 text-gray-600">
                    任務將在 5 秒後自動移除，或將嘗試自動重試
                  </p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ActiveTasksDisplay; 