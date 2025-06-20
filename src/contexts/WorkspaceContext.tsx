/**
 * 工作區上下文提供者 - FE-02 多工作區狀態管理重構
 * 為整個應用提供工作區狀態的 React Context
 */

import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { 
  useWorkspaceStore,
  useCurrentWorkspace,
  useWorkspaceSync,
  useCurrentWorkspaceData
} from '../stores/workspace';
import { Workspace } from '../types/api';

// 工作區上下文類型定義
interface WorkspaceContextType {
  // 當前工作區資訊
  currentWorkspace: Workspace | null;
  currentWorkspaceId: string | null;
  
  // 工作區列表
  workspaces: Workspace[];
  
  // 載入狀態
  isLoading: boolean;
  error: string | null;
  
  // 工作區操作
  switchWorkspace: (workspaceId: string) => Promise<boolean>;
  createWorkspace: (name: string) => Promise<Workspace | null>;
  refreshWorkspaces: () => Promise<void>;
  
  // 狀態檢查
  hasValidWorkspace: boolean;
  isWorkspaceSelected: boolean;
}

// 創建上下文
const WorkspaceContext = createContext<WorkspaceContextType | null>(null);

// 工作區提供者組件
interface WorkspaceProviderProps {
  children: ReactNode;
}

export const WorkspaceProvider: React.FC<WorkspaceProviderProps> = ({ children }) => {
  const [isInitialized, setIsInitialized] = useState(false);
  
  // 使用工作區狀態管理
  const workspaceStore = useWorkspaceStore();
  const currentWorkspace = useCurrentWorkspace();
  const { isWorkspaceSelected } = useWorkspaceSync();
  const { hasValidWorkspace } = useCurrentWorkspaceData();
  
  // 初始化工作區資料
  useEffect(() => {
    const initializeWorkspaces = async () => {
      if (!isInitialized) {
        try {
          // 嘗試刷新工作區列表
          await workspaceStore.refreshWorkspaces();
          setIsInitialized(true);
        } catch (error) {
          console.error('Failed to initialize workspaces:', error);
          setIsInitialized(true); // 即使失敗也標記為初始化完成
        }
      }
    };
    
    initializeWorkspaces();
  }, [isInitialized, workspaceStore]);
  
  // 當工作區切換時的副作用
  useEffect(() => {
    if (currentWorkspace) {
      // 更新頁面標題
      document.title = `${currentWorkspace.name} - Research Assistant`;
      
      // 可以在這裡添加其他工作區切換的副作用
      // 例如：發送分析事件、更新用戶偏好設定等
    } else {
      document.title = 'Research Assistant';
    }
  }, [currentWorkspace]);
  
  // 提供給組件的值
  const contextValue: WorkspaceContextType = {
    // 當前工作區資訊
    currentWorkspace,
    currentWorkspaceId: workspaceStore.currentWorkspaceId,
    
    // 工作區列表
    workspaces: workspaceStore.workspaces,
    
    // 載入狀態
    isLoading: workspaceStore.isLoading,
    error: workspaceStore.error,
    
    // 工作區操作
    switchWorkspace: workspaceStore.switchToWorkspace,
    createWorkspace: workspaceStore.createWorkspace,
    refreshWorkspaces: workspaceStore.refreshWorkspaces,
    
    // 狀態檢查
    hasValidWorkspace,
    isWorkspaceSelected
  };
  
  return (
    <WorkspaceContext.Provider value={contextValue}>
      {children}
    </WorkspaceContext.Provider>
  );
};

// 使用工作區上下文的 Hook
export const useWorkspaceContext = (): WorkspaceContextType => {
  const context = useContext(WorkspaceContext);
  
  if (!context) {
    throw new Error('useWorkspaceContext must be used within a WorkspaceProvider');
  }
  
  return context;
};

// 特定用途的工作區 Hooks

/**
 * Hook：確保有有效的工作區，否則導向工作區選擇
 */
export const useRequireWorkspace = () => {
  const { currentWorkspace, hasValidWorkspace, isLoading } = useWorkspaceContext();
  
  const requireWorkspace = () => {
    if (!hasValidWorkspace && !isLoading) {
      throw new Error('Valid workspace required for this operation');
    }
    return currentWorkspace!;
  };
  
  return {
    currentWorkspace,
    requireWorkspace,
    isReady: hasValidWorkspace && !isLoading
  };
};

/**
 * Hook：工作區統計資訊
 */
export const useWorkspaceStatistics = () => {
  const { workspaces, currentWorkspace } = useWorkspaceContext();
  
  return {
    totalWorkspaces: workspaces.length,
    hasWorkspaces: workspaces.length > 0,
    currentWorkspaceName: currentWorkspace?.name || 'None',
    workspaceNames: workspaces.map(w => w.name)
  };
};

/**
 * Hook：工作區切換輔助功能
 */
export const useWorkspaceSwitching = () => {
  const { switchWorkspace, workspaces, currentWorkspaceId } = useWorkspaceContext();
  const [isSwitching, setIsSwitching] = useState(false);
  
  const switchToWorkspace = async (workspaceId: string) => {
    if (workspaceId === currentWorkspaceId) {
      return true; // 已經在目標工作區
    }
    
    setIsSwitching(true);
    try {
      const success = await switchWorkspace(workspaceId);
      return success;
    } finally {
      setIsSwitching(false);
    }
  };
  
  const getNextWorkspace = () => {
    if (!currentWorkspaceId || workspaces.length <= 1) return null;
    
    const currentIndex = workspaces.findIndex(w => w.id === currentWorkspaceId);
    const nextIndex = (currentIndex + 1) % workspaces.length;
    return workspaces[nextIndex];
  };
  
  const switchToNext = async () => {
    const nextWorkspace = getNextWorkspace();
    if (nextWorkspace) {
      return await switchToWorkspace(nextWorkspace.id);
    }
    return false;
  };
  
  return {
    switchToWorkspace,
    switchToNext,
    isSwitching,
    canSwitchToNext: workspaces.length > 1
  };
}; 