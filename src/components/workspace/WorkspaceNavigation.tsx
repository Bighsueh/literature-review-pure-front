/**
 * 工作區導航組件 - FE-03 工作區管理界面開發
 * 包含工作區切換器、快捷鍵支援和導航功能
 */

import React, { useState, useCallback, useEffect } from 'react';
import { useWorkspaceContext, useWorkspaceSwitching } from '../../contexts/WorkspaceContext';
import WorkspaceSwitcher from './WorkspaceSwitcher';

interface WorkspaceNavigationProps {
  className?: string;
  position?: 'top' | 'side';
  showQuickActions?: boolean;
}

const WorkspaceNavigation: React.FC<WorkspaceNavigationProps> = ({
  className = '',
  position = 'top',
  showQuickActions = true
}) => {
  const { workspaces, currentWorkspace } = useWorkspaceContext();
  const { switchToWorkspace, switchToNext, canSwitchToNext } = useWorkspaceSwitching();
  const [showShortcuts, setShowShortcuts] = useState(false);

  // 快捷鍵處理
  useEffect(() => {
    const handleKeyPress = (event: KeyboardEvent) => {
      // Cmd/Ctrl + K: 顯示工作區選擇器
      if ((event.metaKey || event.ctrlKey) && event.key === 'k') {
        event.preventDefault();
        // 觸發工作區切換器打開
        const switcher = document.querySelector('[data-workspace-switcher]') as HTMLButtonElement;
        if (switcher) {
          switcher.click();
        }
      }

      // Cmd/Ctrl + ]: 下一個工作區
      if ((event.metaKey || event.ctrlKey) && event.key === ']' && canSwitchToNext) {
        event.preventDefault();
        switchToNext();
      }

      // Cmd/Ctrl + [: 上一個工作區（循環回去）
      if ((event.metaKey || event.ctrlKey) && event.key === '[' && workspaces.length > 1) {
        event.preventDefault();
        const currentIndex = workspaces.findIndex(w => w.id === currentWorkspace?.id);
        const prevIndex = currentIndex > 0 ? currentIndex - 1 : workspaces.length - 1;
        switchToWorkspace(workspaces[prevIndex].id);
      }

      // 數字鍵 1-9: 快速切換到對應工作區
      const num = parseInt(event.key);
      if ((event.metaKey || event.ctrlKey) && !isNaN(num) && num >= 1 && num <= 9) {
        const targetWorkspace = workspaces[num - 1];
        if (targetWorkspace) {
          event.preventDefault();
          switchToWorkspace(targetWorkspace.id);
        }
      }
    };

    document.addEventListener('keydown', handleKeyPress);
    return () => {
      document.removeEventListener('keydown', handleKeyPress);
    };
  }, [workspaces, currentWorkspace, switchToWorkspace, switchToNext, canSwitchToNext]);

  const handleQuickSwitch = useCallback((direction: 'next' | 'prev') => {
    if (workspaces.length <= 1) return;

    const currentIndex = workspaces.findIndex(w => w.id === currentWorkspace?.id);
    if (currentIndex === -1) return;

    let targetIndex;
    if (direction === 'next') {
      targetIndex = (currentIndex + 1) % workspaces.length;
    } else {
      targetIndex = currentIndex > 0 ? currentIndex - 1 : workspaces.length - 1;
    }

    switchToWorkspace(workspaces[targetIndex].id);
  }, [workspaces, currentWorkspace, switchToWorkspace]);

  // 渲染快捷操作
  const renderQuickActions = () => {
    if (!showQuickActions || workspaces.length <= 1) return null;

    return (
      <div className="flex items-center space-x-1">
        {/* 上一個工作區 */}
        <button
          onClick={() => handleQuickSwitch('prev')}
          className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors"
          title="上一個工作區 (Cmd+[)"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>

        {/* 下一個工作區 */}
        <button
          onClick={() => handleQuickSwitch('next')}
          className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors"
          title="下一個工作區 (Cmd+])"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </button>

        {/* 快捷鍵提示 */}
        <button
          onClick={() => setShowShortcuts(!showShortcuts)}
          className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors"
          title="快捷鍵說明"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </button>
      </div>
    );
  };

  // 渲染快捷鍵說明
  const renderShortcutsHelp = () => {
    if (!showShortcuts) return null;

    return (
      <div className="absolute top-full right-0 mt-2 w-64 bg-white border border-gray-200 rounded-lg shadow-lg z-50 p-4">
        <h3 className="text-sm font-medium text-gray-900 mb-3">工作區快捷鍵</h3>
        <div className="space-y-2 text-xs">
          <div className="flex justify-between">
            <span className="text-gray-600">打開工作區選擇器</span>
            <kbd className="px-2 py-1 bg-gray-100 rounded text-gray-800">⌘K</kbd>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">下一個工作區</span>
            <kbd className="px-2 py-1 bg-gray-100 rounded text-gray-800">⌘]</kbd>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">上一個工作區</span>
            <kbd className="px-2 py-1 bg-gray-100 rounded text-gray-800">⌘[</kbd>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">切換到工作區 1-9</span>
            <kbd className="px-2 py-1 bg-gray-100 rounded text-gray-800">⌘1-9</kbd>
          </div>
        </div>
        
        {/* 關閉按鈕 */}
        <button
          onClick={() => setShowShortcuts(false)}
          className="absolute top-2 right-2 p-1 text-gray-400 hover:text-gray-600 rounded"
        >
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    );
  };

  return (
    <div className={`relative flex items-center space-x-3 ${className}`}>
      {/* 工作區切換器 */}
      <div className="flex-1">
        <WorkspaceSwitcher 
          compact={position === 'side'}
          showUserInfo={position === 'top'}
        />
      </div>

      {/* 快捷操作 */}
      {renderQuickActions()}

      {/* 快捷鍵說明 */}
      {renderShortcutsHelp()}

      {/* 點擊外部關閉快捷鍵說明 */}
      {showShortcuts && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setShowShortcuts(false)}
        />
      )}
    </div>
  );
};

export default WorkspaceNavigation; 