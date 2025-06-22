/**
 * 工作區切換器組件 - FE-03 工作區管理界面開發
 * 提供工作區切換、創建、設定和管理功能
 */

import React, { useState, useRef, useEffect } from 'react';
import { useAuth } from '../../App';
import { useWorkspace } from '../../contexts/WorkspaceContext';
import LoadingSpinner from '../common/LoadingSpinner';

interface WorkspaceSwitcherProps {
  className?: string;
  showUserInfo?: boolean;
  compact?: boolean;
}

const WorkspaceSwitcher: React.FC<WorkspaceSwitcherProps> = ({ 
  className = '',
  showUserInfo = true,
  compact = false
}) => {
  const { user, onLogout } = useAuth();
  const { 
    workspaces, 
    currentWorkspace, 
    loading: isLoading,
    error,
    createWorkspace,
    selectWorkspace
  } = useWorkspace();
  
  // 本地狀態管理
  const [isOpen, setIsOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [isSwitching, setIsSwitching] = useState(false);
  const [newWorkspaceName, setNewWorkspaceName] = useState('');
  const [createError, setCreateError] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  
  // 安全的工作區名稱處理函數 - 防止 charAt 錯誤
  const getWorkspaceName = (workspace: typeof currentWorkspace): string => {
    if (!workspace) return '選擇工作區';
    const name = workspace.name;
    if (!name || typeof name !== 'string') return '未命名工作區';
    return name.trim() || '未命名工作區';
  };

  // 安全的首字母提取函數 - 防止 undefined.charAt 錯誤
  const getWorkspaceInitial = (workspace: typeof currentWorkspace): string => {
    const name = getWorkspaceName(workspace);
    if (name === '選擇工作區' || name === '未命名工作區') return '?';
    return name.charAt(0).toUpperCase();
  };
  
  // 計算統計資訊
  const totalWorkspaces = workspaces.length;
  const hasWorkspaces = totalWorkspaces > 0;
  
  const dropdownRef = useRef<HTMLDivElement>(null);

  // 處理點擊外部關閉下拉選單
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
        setShowCreateForm(false);
        setCreateError(null);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const handleWorkspaceSelect = async (workspaceId: string) => {
    if (workspaceId === currentWorkspace?.id) {
      setIsOpen(false);
      return;
    }

    setIsSwitching(true);
    try {
      await selectWorkspace(workspaceId);
      setIsOpen(false);
    } catch (error) {
      console.error('Failed to switch workspace:', error);
    } finally {
      setIsSwitching(false);
    }
  };

  const handleCreateWorkspace = async () => {
    if (!newWorkspaceName.trim()) {
      setCreateError('工作區名稱不能為空');
      return;
    }

    setIsCreating(true);
    setCreateError(null);

    try {
      const newWorkspace = await createWorkspace(newWorkspaceName.trim());
      
      if (newWorkspace) {
        setNewWorkspaceName('');
        setShowCreateForm(false);
        setIsOpen(false);
      } else {
        setCreateError('創建工作區失敗，請重試');
      }
    } catch (error) {
      console.error('Create workspace error:', error);
      setCreateError(error instanceof Error ? error.message : '創建工作區時發生錯誤');
    } finally {
      setIsCreating(false);
    }
  };

  const toggleCreateForm = () => {
    setShowCreateForm(!showCreateForm);
    setCreateError(null);
    setNewWorkspaceName('');
  };

  // 取得工作區統計資訊
  const getWorkspaceStats = () => {
    // 這裡可以從工作區 stores 獲取統計資訊
    // 暫時返回預設值，後續可以與具體的 stores 整合
    return {
      fileCount: 0,
      chatCount: 0,
      lastActivity: '最近活動'
    };
  };

  if (!hasWorkspaces) {
    return null; // 沒有工作區時由 WorkspaceSelector 處理
  }

  return (
    <div className={`relative ${className}`} ref={dropdownRef}>
      {/* 當前工作區顯示按鈕 */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={isLoading || isSwitching}
        className={`flex items-center space-x-2 px-3 py-2 bg-white border border-gray-300 rounded-lg shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all ${
          compact ? 'min-w-0' : 'min-w-48'
        }`}
      >
        {isSwitching ? (
          <LoadingSpinner />
        ) : (
          <>
            <div className="flex items-center space-x-2 flex-1 min-w-0">
              {/* 工作區圖示 */}
              <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0">
                <span className="text-blue-600 font-medium text-sm">
                  {getWorkspaceInitial(currentWorkspace)}
                </span>
              </div>
              
              {/* 工作區資訊 */}
              {!compact && (
                <div className="text-left min-w-0 flex-1">
                  <div className="text-sm font-medium text-gray-900 truncate">
                    {getWorkspaceName(currentWorkspace)}
                  </div>
                  {showUserInfo && (
                    <div className="text-xs text-gray-500 truncate">
                      {user.name}
                    </div>
                  )}
                </div>
              )}
            </div>
            
            {/* 下拉箭頭 */}
            <svg
              className={`w-4 h-4 text-gray-400 transition-transform flex-shrink-0 ${isOpen ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </>
        )}
      </button>

      {/* 下拉選單 */}
      {isOpen && (
        <div className="absolute top-full left-0 mt-1 w-full min-w-80 bg-white border border-gray-200 rounded-lg shadow-lg z-50">
          {/* 標題區 */}
          <div className="px-4 py-3 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium text-gray-900">工作區管理</h3>
              <span className="text-xs text-gray-500">{totalWorkspaces} 個工作區</span>
            </div>
          </div>
          
          {/* 錯誤提示 */}
          {error && (
            <div className="mx-4 mt-3 bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded text-sm">
              {error}
            </div>
          )}
          
          <div className="max-h-80 overflow-y-auto">
            {/* 工作區列表 */}
            <div className="py-1">
              {workspaces.map((workspace) => {
                const stats = getWorkspaceStats();
                const isSelected = workspace.id === currentWorkspace?.id;
                
                return (
                  <button
                    key={workspace.id}
                    onClick={() => handleWorkspaceSelect(workspace.id)}
                    disabled={isSwitching}
                    className={`w-full px-4 py-3 text-left hover:bg-gray-50 focus:outline-none focus:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors ${
                      isSelected ? 'bg-blue-50 border-r-2 border-blue-500' : ''
                    }`}
                  >
                    <div className="flex items-center space-x-3">
                      {/* 工作區圖示 */}
                      <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
                        isSelected ? 'bg-blue-500 text-white' : 'bg-gray-100 text-gray-600'
                      }`}>
                        <span className="font-medium">
                          {getWorkspaceInitial(workspace)}
                        </span>
                      </div>
                      
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2">
                          <div className={`text-sm font-medium truncate ${
                            isSelected ? 'text-blue-900' : 'text-gray-900'
                          }`}>
                            {getWorkspaceName(workspace)}
                          </div>
                          {isSelected && (
                            <svg className="w-4 h-4 text-blue-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                            </svg>
                          )}
                        </div>
                        
                        {workspace.description && (
                          <div className="text-xs text-gray-500 truncate mt-1">
                            {workspace.description}
                          </div>
                        )}
                        
                        <div className="flex items-center space-x-4 mt-1">
                          <span className="text-xs text-gray-500">
                            {stats.fileCount} 檔案
                          </span>
                          <span className="text-xs text-gray-500">
                            {stats.chatCount} 對話
                          </span>
                        </div>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
            
            {/* 創建新工作區 */}
            <div className="border-t border-gray-200">
              {!showCreateForm ? (
                <button
                  onClick={toggleCreateForm}
                  className="w-full px-4 py-3 text-left text-sm text-blue-600 hover:bg-blue-50 focus:outline-none focus:bg-blue-50 transition-colors"
                >
                  <div className="flex items-center space-x-2">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                    </svg>
                    <span>創建新工作區</span>
                  </div>
                </button>
              ) : (
                <div className="p-4">
                  <div className="space-y-3">
                    <input
                      type="text"
                      value={newWorkspaceName}
                      onChange={(e) => setNewWorkspaceName(e.target.value)}
                      placeholder="工作區名稱"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      onKeyPress={(e) => {
                        if (e.key === 'Enter') {
                          handleCreateWorkspace();
                        } else if (e.key === 'Escape') {
                          toggleCreateForm();
                        }
                      }}
                      autoFocus
                    />
                    
                    {createError && (
                      <div className="text-red-600 text-xs">
                        {createError}
                      </div>
                    )}
                    
                    <div className="flex space-x-2">
                      <button
                        onClick={handleCreateWorkspace}
                        disabled={isCreating || !newWorkspaceName.trim()}
                        className="flex-1 px-3 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        {isCreating ? '創建中...' : '創建'}
                      </button>
                      <button
                        onClick={toggleCreateForm}
                        disabled={isCreating}
                        className="px-3 py-2 border border-gray-300 text-gray-700 text-sm rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        取消
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default WorkspaceSwitcher; 