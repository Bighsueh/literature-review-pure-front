/**
 * 工作區選擇器組件 - FE-02 多工作區狀態管理重構
 */

import React, { useState } from 'react';
import { useWorkspaceContext } from '../../contexts/WorkspaceContext';
import LoadingSpinner from '../common/LoadingSpinner';

const WorkspaceSelector: React.FC = () => {
  const { 
    workspaces, 
    currentWorkspace,
    isLoading,
    error,
    switchWorkspace,
    createWorkspace
  } = useWorkspaceContext();
  
  const [isCreating, setIsCreating] = useState(false);
  const [newWorkspaceName, setNewWorkspaceName] = useState('');
  const [createError, setCreateError] = useState<string | null>(null);

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

  const handleSwitchWorkspace = async (workspaceId: string) => {
    try {
      await switchWorkspace(workspaceId);
    } catch (error) {
      console.error('Switch workspace error:', error);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <LoadingSpinner />
          <p className="text-gray-600 mt-4">載入工作區中...</p>
        </div>
      </div>
    );
  }

  if (workspaces.length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full space-y-8 p-8">
          <div className="text-center">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">歡迎！</h2>
            <p className="text-gray-600 mb-8">
              您還沒有任何工作區。創建您的第一個工作區來開始使用。
            </p>
            
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
                {error}
              </div>
            )}
            
            {createError && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
                {createError}
              </div>
            )}
            
            <div className="space-y-4">
              <input
                type="text"
                value={newWorkspaceName}
                onChange={(e) => setNewWorkspaceName(e.target.value)}
                placeholder="輸入工作區名稱"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={isCreating}
              />
              
              <button 
                onClick={handleCreateWorkspace}
                disabled={isCreating || !newWorkspaceName.trim()}
                className="w-full bg-blue-600 text-white py-3 px-4 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
              >
                {isCreating ? '創建中...' : '創建我的第一個工作區'}
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!currentWorkspace) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full space-y-8 p-8">
          <div className="text-center">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">選擇工作區</h2>
            <p className="text-gray-600 mb-8">請選擇一個工作區來繼續使用。</p>
            
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
                {error}
              </div>
            )}
            
            <div className="space-y-4">
              {workspaces.map((workspace) => (
                <button
                  key={workspace.id}
                  onClick={() => handleSwitchWorkspace(workspace.id)}
                  className="w-full text-left p-3 border border-gray-200 rounded-lg hover:bg-blue-50 hover:border-blue-300 transition-colors"
                >
                  <div className="font-medium text-gray-900">{workspace.name}</div>
                  <div className="text-sm text-gray-500">
                    建立於 {new Date(workspace.created_at).toLocaleDateString('zh-TW')}
                  </div>
                </button>
              ))}
              
              <div className="border-t pt-4">
                <h3 className="text-sm font-medium text-gray-700 text-left mb-2">或創建新工作區：</h3>
                
                {createError && (
                  <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded mb-2 text-sm">
                    {createError}
                  </div>
                )}
                
                <div className="flex space-x-2">
                  <input
                    type="text"
                    value={newWorkspaceName}
                    onChange={(e) => setNewWorkspaceName(e.target.value)}
                    placeholder="新工作區名稱"
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    disabled={isCreating}
                  />
                  <button 
                    onClick={handleCreateWorkspace}
                    disabled={isCreating || !newWorkspaceName.trim()}
                    className="bg-green-600 text-white py-2 px-4 rounded-md hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
                  >
                    {isCreating ? '創建中...' : '創建'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return null;
};

export default WorkspaceSelector;
