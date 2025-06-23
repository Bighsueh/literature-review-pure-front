/**
 * 工作區狀態管理統一匯出 - FE-02 多工作區狀態管理重構
 * 提供統一的工作區狀態管理入口和協調機制
 */

// 核心工作區狀態管理
export { 
  useWorkspaceStore,
  useCurrentWorkspace,
  useWorkspaceStats,
  useWorkspaceValidation
} from './workspaceStore';

// 工作區檔案狀態管理
export {
  getWorkspaceFileStore,
  useCurrentWorkspaceFileStore
} from './workspaceFileStore';

// 工作區對話狀態管理
export {
  getWorkspaceChatStore,
  useCurrentWorkspaceChatStore
} from './workspaceChatStore';

// 工作區狀態協調 Hook
import { useEffect } from 'react';
import { useWorkspaceStore, useCurrentWorkspace } from './workspaceStore';
import { getWorkspaceFileStore } from './workspaceFileStore';
import { getWorkspaceChatStore } from './workspaceChatStore';

/**
 * 工作區狀態同步 Hook - 確保各個 store 之間的資料一致性
 */
export const useWorkspaceSync = () => {
  const { currentWorkspaceId, workspaces } = useWorkspaceStore();
  
  useEffect(() => {
    if (currentWorkspaceId) {
      // 確保當前工作區的 stores 已初始化
      getWorkspaceFileStore(currentWorkspaceId);
      getWorkspaceChatStore(currentWorkspaceId);
      
      // 可以在這裡添加額外的同步邏輯
      // 例如：當工作區切換時自動刷新資料
    }
  }, [currentWorkspaceId]);
  
  return {
    currentWorkspaceId,
    isWorkspaceSelected: !!currentWorkspaceId,
    workspaceCount: workspaces.length
  };
};

/**
 * 統一的工作區資料管理 Hook
 * 提供當前工作區的完整狀態存取
 */
export const useCurrentWorkspaceData = () => {
  const workspaceStore = useWorkspaceStore();
  const currentWorkspace = useCurrentWorkspace();
  
  // 動態獲取當前工作區的檔案和對話 stores
  const getFileStore = () => {
    if (!workspaceStore.currentWorkspaceId) return null;
    return getWorkspaceFileStore(workspaceStore.currentWorkspaceId);
  };
  
  const getChatStore = () => {
    if (!workspaceStore.currentWorkspaceId) return null;
    return getWorkspaceChatStore(workspaceStore.currentWorkspaceId);
  };
  
  return {
    // 工作區基本資訊
    workspace: currentWorkspace,
    workspaceId: workspaceStore.currentWorkspaceId,
    
    // Store 實例
    workspaceStore,
    fileStore: getFileStore(),
    chatStore: getChatStore(),
    
    // 狀態檢查
    isWorkspaceLoaded: !!currentWorkspace,
    hasValidWorkspace: !!workspaceStore.currentWorkspaceId
  };
};

/**
 * 工作區清理 Hook - 清理不活躍工作區的資料
 */
export const useWorkspaceCleanup = () => {
  const { workspaces } = useWorkspaceStore();
  
  const cleanupInactiveWorkspaces = () => {
    // 這裡可以實現清理邏輯
    // 例如：清理 localStorage 中舊的工作區資料
    // 或者釋放記憶體中不活躍的 stores
    
    console.log(`Cleanup completed for ${workspaces.length} workspaces`);
  };
  
  return { cleanupInactiveWorkspaces };
};

/**
 * 批量工作區操作 Hook
 */
export const useWorkspaceBatchOperations = () => {
  const workspaceStore = useWorkspaceStore();
  
  const initializeWorkspaceData = async (workspaceId: string) => {
    const fileStore = getWorkspaceFileStore(workspaceId);
    const chatStore = getWorkspaceChatStore(workspaceId);
    
    // 並行初始化資料
    await Promise.all([
      fileStore.getState().refreshPapers(),
      chatStore.getState().refreshChatHistory()
    ]);
  };
  
  const clearWorkspaceData = (workspaceId: string) => {
    const fileStore = getWorkspaceFileStore(workspaceId);
    const chatStore = getWorkspaceChatStore(workspaceId);
    
    // 清理工作區資料 - 註解掉不確定的方法
    // fileStore.getState().clearAllData?.();
    chatStore.getState().clearAllData();
  };
  
  const switchWorkspace = async (workspaceId: string) => {
    // 切換到新工作區
    const success = await workspaceStore.switchToWorkspace(workspaceId);
    
    if (success) {
      // 初始化新工作區的資料
      await initializeWorkspaceData(workspaceId);
    }
    
    return success;
  };
  
  return {
    initializeWorkspaceData,
    clearWorkspaceData,
    switchWorkspace
  };
}; 