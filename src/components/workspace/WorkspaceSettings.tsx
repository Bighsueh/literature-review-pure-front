/**
 * 工作區設定組件 - FE-03 工作區管理界面開發
 * 提供工作區重命名、刪除、統計等管理功能
 */

import React, { useState, useEffect } from 'react';
import { useWorkspace } from '../../contexts/WorkspaceContext';
import { WorkspaceApiService } from '../../services/workspace_api_service';
import Modal from '../common/Modal/Modal';
import LoadingSpinner from '../common/LoadingSpinner';

interface WorkspaceSettingsProps {
  isOpen: boolean;
  onClose: () => void;
  workspaceId?: string;
}

interface WorkspaceStats {
  fileCount: number;
  chatCount: number;
  totalQueries: number;
  createdAt: string;
  lastActivity: string;
  storageUsed: string;
}

const WorkspaceSettings: React.FC<WorkspaceSettingsProps> = ({
  isOpen,
  onClose,
  workspaceId
}) => {
  const { 
    workspaces, 
    currentWorkspace, 
    refreshWorkspaces,
    deleteWorkspace,
    updateWorkspace 
  } = useWorkspace();
  
  const [activeTab, setActiveTab] = useState<'general' | 'stats' | 'danger'>('general');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  // 一般設定
  const [workspaceName, setWorkspaceName] = useState('');
  const [isRenaming, setIsRenaming] = useState(false);
  
  // 刪除確認
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState('');
  const [isDeleting, setIsDeleting] = useState(false);
  
  // 統計資料
  const [stats, setStats] = useState<WorkspaceStats | null>(null);
  
  // 當前操作的工作區
  const targetWorkspace = workspaceId 
    ? workspaces.find(w => w.id === workspaceId)
    : currentWorkspace;

  // 初始化資料
  useEffect(() => {
    if (isOpen && targetWorkspace) {
      setWorkspaceName(targetWorkspace.name);
      setError(null);
      setSuccess(null);
      loadWorkspaceStats();
    }
  }, [isOpen, targetWorkspace]);

  // 載入工作區統計資料
  const loadWorkspaceStats = async () => {
    if (!targetWorkspace) return;

    setIsLoading(true);
    try {
      // 這裡應該從 API 獲取真實的統計資料
      // 暫時使用模擬資料
      const mockStats: WorkspaceStats = {
        fileCount: 0,
        chatCount: 0,
        totalQueries: 0,
        createdAt: targetWorkspace.created_at,
        lastActivity: new Date().toISOString(),
        storageUsed: '0 MB'
      };
      
      // 模擬 API 延遲
      await new Promise(resolve => setTimeout(resolve, 500));
      setStats(mockStats);
    } catch (error) {
      console.error('Failed to load workspace stats:', error);
      setError('載入統計資料失敗');
    } finally {
      setIsLoading(false);
    }
  };

  // 重命名工作區
  const handleRename = async () => {
    if (!targetWorkspace || !workspaceName.trim()) {
      setError('工作區名稱不能為空');
      return;
    }

    if (workspaceName.trim() === targetWorkspace.name) {
      setSuccess('工作區名稱未變更');
      return;
    }

    setIsRenaming(true);
    setError(null);

    try {
      const success = await updateWorkspace(targetWorkspace.id, {
        name: workspaceName.trim()
      });

      if (success) {
        setSuccess('工作區重命名成功');
        await refreshWorkspaces();
      } else {
        setError('重命名失敗，請重試');
      }
    } catch (error) {
      console.error('Rename workspace error:', error);
      setError(error instanceof Error ? error.message : '重命名時發生錯誤');
    } finally {
      setIsRenaming(false);
    }
  };

  // 刪除工作區
  const handleDelete = async () => {
    if (!targetWorkspace) return;

    if (deleteConfirmText !== targetWorkspace.name) {
      setError('請正確輸入工作區名稱以確認刪除');
      return;
    }

    setIsDeleting(true);
    setError(null);

    try {
      const success = await deleteWorkspace(targetWorkspace.id);
      
      if (success) {
        setSuccess('工作區已刪除');
        setTimeout(() => {
          onClose();
        }, 1000);
      } else {
        setError('刪除失敗，請重試');
      }
    } catch (error) {
      console.error('Delete workspace error:', error);
      setError(error instanceof Error ? error.message : '刪除時發生錯誤');
    } finally {
      setIsDeleting(false);
    }
  };

  // 清除訊息
  const clearMessages = () => {
    setError(null);
    setSuccess(null);
  };

  // 渲染標籤頁導航
  const renderTabNavigation = () => {
    const tabs = [
      { id: 'general', label: '一般', icon: '⚙️' },
      { id: 'stats', label: '統計', icon: '📊' },
      { id: 'danger', label: '危險操作', icon: '⚠️' }
    ] as const;

    return (
      <div className="flex border-b border-gray-200">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center space-x-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab.id
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            <span>{tab.icon}</span>
            <span>{tab.label}</span>
          </button>
        ))}
      </div>
    );
  };

  // 渲染一般設定
  const renderGeneralSettings = () => (
    <div className="space-y-6">
      <div>
        <label htmlFor="workspace-name" className="block text-sm font-medium text-gray-700 mb-2">
          工作區名稱
        </label>
        <div className="flex space-x-3">
          <input
            id="workspace-name"
            type="text"
            value={workspaceName}
            onChange={(e) => setWorkspaceName(e.target.value)}
            className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            disabled={isRenaming}
          />
          <button
            onClick={handleRename}
            disabled={isRenaming || !workspaceName.trim()}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            {isRenaming ? '重命名中...' : '重命名'}
          </button>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          建立時間
        </label>
        <p className="text-sm text-gray-600">
          {targetWorkspace ? new Date(targetWorkspace.created_at).toLocaleString('zh-TW') : ''}
        </p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          工作區 ID
        </label>
        <p className="text-sm text-gray-600 font-mono bg-gray-50 p-2 rounded border">
          {targetWorkspace?.id}
        </p>
      </div>
    </div>
  );

  // 渲染統計資料
  const renderStats = () => {
    if (isLoading) {
      return (
        <div className="flex items-center justify-center py-8">
          <LoadingSpinner />
          <span className="ml-2 text-gray-600">載入統計資料中...</span>
        </div>
      );
    }

    if (!stats) {
      return (
        <div className="text-center py-8 text-gray-500">
          無法載入統計資料
        </div>
      );
    }

    const statItems = [
      { label: '檔案數量', value: stats.fileCount, icon: '📄' },
      { label: '對話記錄', value: stats.chatCount, icon: '💬' },
      { label: '總查詢次數', value: stats.totalQueries, icon: '🔍' },
      { label: '儲存空間使用', value: stats.storageUsed, icon: '💾' }
    ];

    return (
      <div className="space-y-6">
        <div className="grid grid-cols-2 gap-4">
          {statItems.map((item) => (
            <div
              key={item.label}
              className="bg-gray-50 p-4 rounded-lg border"
            >
              <div className="flex items-center space-x-2 mb-2">
                <span className="text-lg">{item.icon}</span>
                <span className="text-sm font-medium text-gray-700">{item.label}</span>
              </div>
              <div className="text-2xl font-bold text-gray-900">
                {typeof item.value === 'number' ? item.value.toLocaleString() : item.value}
              </div>
            </div>
          ))}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            最後活動時間
          </label>
          <p className="text-sm text-gray-600">
            {new Date(stats.lastActivity).toLocaleString('zh-TW')}
          </p>
        </div>
      </div>
    );
  };

  // 渲染危險操作
  const renderDangerZone = () => (
    <div className="space-y-6">
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <h3 className="text-lg font-medium text-red-800 mb-2">刪除工作區</h3>
        <p className="text-sm text-red-700 mb-4">
          刪除工作區將永久移除所有相關的檔案、對話記錄和資料。此操作無法復原。
        </p>
        
        {!showDeleteConfirm ? (
          <button
            onClick={() => setShowDeleteConfirm(true)}
            className="bg-red-600 text-white px-4 py-2 rounded-md hover:bg-red-700 transition-colors"
          >
            刪除工作區
          </button>
        ) : (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-red-800 mb-2">
                請輸入工作區名稱「{targetWorkspace?.name}」以確認刪除：
              </label>
              <input
                type="text"
                value={deleteConfirmText}
                onChange={(e) => setDeleteConfirmText(e.target.value)}
                className="w-full px-3 py-2 border border-red-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500"
                placeholder={targetWorkspace?.name}
                disabled={isDeleting}
              />
            </div>
            
            <div className="flex space-x-3">
              <button
                onClick={handleDelete}
                disabled={isDeleting || deleteConfirmText !== targetWorkspace?.name}
                className="bg-red-600 text-white px-4 py-2 rounded-md hover:bg-red-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
              >
                {isDeleting ? '刪除中...' : '確認刪除'}
              </button>
              <button
                onClick={() => {
                  setShowDeleteConfirm(false);
                  setDeleteConfirmText('');
                }}
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 transition-colors"
              >
                取消
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );

  if (!targetWorkspace) {
    return null;
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`工作區設定 - ${targetWorkspace.name}`}
      size="lg"
    >
      <div className="h-96 flex flex-col">
        {/* 標籤頁導航 */}
        {renderTabNavigation()}

        {/* 訊息提示 */}
        {(error || success) && (
          <div className={`mx-6 mt-4 p-3 rounded-md ${
            error ? 'bg-red-50 border border-red-200 text-red-700' : 'bg-green-50 border border-green-200 text-green-700'
          }`}>
            <div className="flex items-center justify-between">
              <span className="text-sm">{error || success}</span>
              <button
                onClick={clearMessages}
                className="text-sm underline hover:no-underline"
              >
                關閉
              </button>
            </div>
          </div>
        )}

        {/* 標籤頁內容 */}
        <div className="flex-1 p-6 overflow-y-auto">
          {activeTab === 'general' && renderGeneralSettings()}
          {activeTab === 'stats' && renderStats()}
          {activeTab === 'danger' && renderDangerZone()}
        </div>
      </div>
    </Modal>
  );
};

export default WorkspaceSettings; 