/**
 * 工作區導航組件 - FE-03 工作區管理界面開發
 * 提供工作區間導航和快速切換功能
 */

import React from 'react';
import { ChevronLeftIcon, ChevronRightIcon } from '@heroicons/react/24/outline';
import { useWorkspace } from '../../contexts/WorkspaceContext';
import LoadingSpinner from '../common/LoadingSpinner';

interface WorkspaceNavigationProps {
  className?: string;
  showLabels?: boolean;
}

const WorkspaceNavigation: React.FC<WorkspaceNavigationProps> = ({
  className = '',
  showLabels = true
}) => {
  const { workspaces, currentWorkspace, selectWorkspace, loading } = useWorkspace();
  
  // 找到當前工作區的索引
  const currentIndex = workspaces.findIndex(w => w.id === currentWorkspace?.id);
  const canGoToPrevious = currentIndex > 0;
  const canGoToNext = currentIndex < workspaces.length - 1;
  
  const switchToPrevious = async () => {
    if (canGoToPrevious) {
      const previousWorkspace = workspaces[currentIndex - 1];
      await selectWorkspace(previousWorkspace.id);
    }
  };
  
  const switchToNext = async () => {
    if (canGoToNext) {
      const nextWorkspace = workspaces[currentIndex + 1];
      await selectWorkspace(nextWorkspace.id);
    }
  };

  if (workspaces.length <= 1) {
    return null; // 只有一個或沒有工作區時不顯示導航
  }

  return (
    <div className={`flex items-center space-x-2 ${className}`}>
      {/* 上一個工作區 */}
      <button
        onClick={switchToPrevious}
        disabled={!canGoToPrevious || loading}
        className="flex items-center space-x-1 px-2 py-1 rounded-md text-gray-600 hover:text-gray-900 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        title={canGoToPrevious ? `切換到 ${workspaces[currentIndex - 1]?.name}` : '已是第一個工作區'}
      >
        {loading ? (
          <LoadingSpinner size="small" />
        ) : (
          <ChevronLeftIcon className="w-4 h-4" />
        )}
        {showLabels && (
          <span className="text-sm">上一個</span>
        )}
      </button>
      
      {/* 工作區指示器 */}
      <div className="flex items-center space-x-1 px-2 py-1 bg-gray-100 rounded-md">
        <span className="text-sm text-gray-600">
          {currentIndex + 1} / {workspaces.length}
        </span>
      </div>
      
      {/* 下一個工作區 */}
      <button
        onClick={switchToNext}
        disabled={!canGoToNext || loading}
        className="flex items-center space-x-1 px-2 py-1 rounded-md text-gray-600 hover:text-gray-900 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        title={canGoToNext ? `切換到 ${workspaces[currentIndex + 1]?.name}` : '已是最後一個工作區'}
      >
        {showLabels && (
          <span className="text-sm">下一個</span>
        )}
        {loading ? (
          <LoadingSpinner size="small" />
        ) : (
          <ChevronRightIcon className="w-4 h-4" />
        )}
      </button>
    </div>
  );
};

export default WorkspaceNavigation; 