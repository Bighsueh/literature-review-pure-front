/**
 * 工作區切換器組件 - FE-03 工作區管理界面開發
 * 提供工作區切換、創建、設定和管理功能
 */

import React, { useState, useRef, useEffect } from 'react';
import { useAuth } from '../../App';
import { useWorkspaceContext, useWorkspaceSwitching, useWorkspaceStatistics } from '../../contexts/WorkspaceContext';
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
    isLoading,
    error,
    createWorkspace 
  } = useWorkspaceContext();
  
  const { switchToWorkspace, isSwitching } = useWorkspaceSwitching();
  const { totalWorkspaces, hasWorkspaces } = useWorkspaceStatistics();
  
  const [isOpen, setIsOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [newWorkspaceName, setNewWorkspaceName] = useState('');
  const [createError, setCreateError] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  
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

    try {
      await switchToWorkspace(workspaceId);
      setIsOpen(false);
    } catch (error) {
      console.error('Failed to switch workspace:', error);
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
                  {currentWorkspace?.name?.charAt(0).toUpperCase() || 'W'}
                </span>
              </div>
              
              {/* 工作區資訊 */}
              {!compact && (
                <div className="text-left min-w-0 flex-1">
                  <div className="text-sm font-medium text-gray-900 truncate">
                    {currentWorkspace?.name || '選擇工作區'}
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
                    className={`w-full px-4 py-3 text-left hover:bg-gray-50 flex items-center space-x-3 transition-colors ${
                      isSelected ? 'bg-blue-50 text-blue-700' : 'text-gray-700'
                    }`}
                  >
                    {/* 工作區圖示 */}
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                      isSelected ? 'bg-blue-200' : 'bg-gray-100'
                    }`}>
                      <span className={`font-medium text-sm ${
                        isSelected ? 'text-blue-800' : 'text-gray-600'
                      }`}>
                        {workspace.name.charAt(0).toUpperCase()}
                      </span>
                    </div>
                    
                    {/* 工作區資訊 */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2">
                        <div className="text-sm font-medium truncate">{workspace.name}</div>
                        {isSelected && (
                          <svg className="w-4 h-4 text-blue-600 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                          </svg>
                        )}
                      </div>
                      <div className="text-xs text-gray-500 flex items-center space-x-2">
                        <span>建立於 {new Date(workspace.created_at).toLocaleDateString('zh-TW')}</span>
                        <span>•</span>
                        <span>{stats.fileCount} 個檔案</span>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
          
          {/* 分隔線 */}
          <div className="border-t border-gray-200"></div>
          
          {/* 創建新工作區區域 */}
          <div className="p-4">
            {!showCreateForm ? (
              <button
                onClick={toggleCreateForm}
                className="w-full flex items-center space-x-3 px-3 py-2 text-left hover:bg-gray-50 text-gray-700 rounded-md transition-colors"
              >
                <div className="w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center">
                  <svg className="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                </div>
                <span className="text-sm font-medium">建立新工作區</span>
              </button>
            ) : (
              <div className="space-y-3">
                <div className="flex items-center space-x-2">
                  <button
                    onClick={toggleCreateForm}
                    className="p-1 hover:bg-gray-100 rounded"
                  >
                    <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                  <h4 className="text-sm font-medium text-gray-900">建立新工作區</h4>
                </div>
                
                {createError && (
                  <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded text-sm">
                    {createError}
                  </div>
                )}
                
                <div className="space-y-2">
                  <input
                    type="text"
                    value={newWorkspaceName}
                    onChange={(e) => setNewWorkspaceName(e.target.value)}
                    placeholder="輸入工作區名稱"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    disabled={isCreating}
                    autoFocus
                  />
                  
                  <div className="flex space-x-2">
                    <button
                      onClick={handleCreateWorkspace}
                      disabled={isCreating || !newWorkspaceName.trim()}
                      className="flex-1 bg-blue-600 text-white py-2 px-3 rounded-md text-sm hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
                    >
                      {isCreating ? '創建中...' : '創建'}
                    </button>
                    <button
                      onClick={toggleCreateForm}
                      className="px-3 py-2 border border-gray-300 text-gray-700 rounded-md text-sm hover:bg-gray-50 transition-colors"
                    >
                      取消
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
          
          {/* 分隔線和登出 */}
          <div className="border-t border-gray-200">
            <button
              onClick={() => {
                onLogout();
                setIsOpen(false);
              }}
              className="w-full px-4 py-3 text-left hover:bg-gray-50 text-red-600 flex items-center space-x-3 transition-colors"
            >
              <div className="w-8 h-8 bg-red-100 rounded-full flex items-center justify-center">
                <svg className="w-4 h-4 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013 3v1" />
                </svg>
              </div>
              <span className="text-sm font-medium">登出</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default WorkspaceSwitcher; 