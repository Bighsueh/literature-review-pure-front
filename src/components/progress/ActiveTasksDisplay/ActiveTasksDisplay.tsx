import React from 'react';
import { useAppStore } from '../../../stores/appStore';
import ProgressBar from '../../common/ProgressBar/ProgressBar';

const ActiveTasksDisplay: React.FC = () => {
  const activeTasks = useAppStore((state) => state.activeTasks);
  const isUploading = useAppStore((state) => state.isUploading);

  if (activeTasks.length === 0 && !isUploading) {
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
        處理進度 {activeTasks.length > 0 && `(${activeTasks.length})`}
      </h3>

      {isUploading && (
        <div className="mt-3 p-3 bg-blue-50 rounded border border-blue-200">
          <div className="flex items-center">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2"></div>
            <span className="text-sm text-blue-700">正在上傳檔案...</span>
          </div>
        </div>
      )}

      {activeTasks.map((task) => (
        <div key={task.paperId} className="mt-3 last:mb-0">
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
            stage={task.progress >= 100 ? 'completed' : 'analyzing'}
            size="sm"
            showLabel={false}
          />
          
          {task.step.includes('錯誤') && (
            <p className="text-xs text-red-600 mt-1">
              處理時發生錯誤，將自動移除此任務
            </p>
          )}
        </div>
      ))}
    </div>
  );
};

export default ActiveTasksDisplay; 