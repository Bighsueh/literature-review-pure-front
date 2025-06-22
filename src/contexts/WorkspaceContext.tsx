/**
 * 工作區上下文提供者 - FE-02 多工作區狀態管理重構
 * 為整個應用提供工作區狀態的 React Context
 */

import React, { createContext, useContext, useEffect, ReactNode } from 'react';
import { useWorkspaceStore } from '../stores/workspace/workspaceStore';
import { Workspace } from '../types/api';

interface WorkspaceContextType {
  // 工作區狀態
  currentWorkspace: Workspace | null;
  workspaces: Workspace[];
  loading: boolean;
  error: string | null;
  
  // 工作區操作
  selectWorkspace: (workspaceId: string) => Promise<boolean>;
  createWorkspace: (name: string, description?: string) => Promise<Workspace | null>;
  refreshWorkspaces: () => Promise<void>;
  
  // 工作區驗證
  hasValidWorkspace: boolean;
  requireWorkspace: () => Workspace;
}

const WorkspaceContext = createContext<WorkspaceContextType | undefined>(undefined);

interface WorkspaceProviderProps {
  children: ReactNode;
}

export const WorkspaceProvider: React.FC<WorkspaceProviderProps> = ({ children }) => {
  // 使用 Zustand store
  const {
    workspaces,
    currentWorkspaceId,
    isLoading,
    error,
    switchToWorkspace,
    createWorkspace,
    refreshWorkspaces,
    setCurrentWorkspace
  } = useWorkspaceStore();

  // 計算當前工作區
  const currentWorkspace = workspaces.find(w => w.id === currentWorkspaceId) || null;
  const hasValidWorkspace = !!currentWorkspace;

  // 初始化工作區
  useEffect(() => {
    const initializeWorkspaces = async () => {
      try {
        await refreshWorkspaces();
        
        // 如果沒有當前工作區但有可用工作區，選擇第一個
        if (!currentWorkspaceId && workspaces.length > 0) {
          setCurrentWorkspace(workspaces[0].id);
        }
      } catch (error) {
        console.error('工作區初始化失敗:', error);
      }
    };

    initializeWorkspaces();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 更新頁面標題
  useEffect(() => {
    document.title = currentWorkspace 
      ? `${currentWorkspace.name} - Research Assistant`
      : 'Research Assistant';
  }, [currentWorkspace]);

  // 工作區操作方法
  const contextValue: WorkspaceContextType = {
    // 狀態
    currentWorkspace,
    workspaces,
    loading: isLoading,
    error,
    
    // 操作
    selectWorkspace: switchToWorkspace,
    
    createWorkspace: async (name: string, description?: string) => {
      // 注意：原始 createWorkspace 不支援 description 參數
      return createWorkspace(name);
    },
    
    refreshWorkspaces,
    
    // 驗證
    hasValidWorkspace,
    requireWorkspace: () => {
      if (!currentWorkspace) {
        throw new Error('需要有效的工作區才能執行此操作');
      }
      return currentWorkspace;
    }
  };

  return (
    <WorkspaceContext.Provider value={contextValue}>
      {children}
    </WorkspaceContext.Provider>
  );
};

export const useWorkspace = (): WorkspaceContextType => {
  const context = useContext(WorkspaceContext);
  if (context === undefined) {
    throw new Error('useWorkspace 必須在 WorkspaceProvider 內使用');
  }
  return context;
};

// 工作區權限檢查 Hook
export const useWorkspaceAuth = () => {
  const { currentWorkspace, hasValidWorkspace } = useWorkspace();
  
  const requireWorkspace = (workspaceId?: string): Workspace => {
    if (workspaceId) {
      // 檢查特定工作區
      const { workspaces } = useWorkspaceStore.getState();
      const workspace = workspaces.find(w => w.id === workspaceId);
      if (!workspace) {
        throw new Error(`工作區 ${workspaceId} 不存在`);
      }
      return workspace;
    } else {
      // 檢查當前工作區
      if (!currentWorkspace) {
        throw new Error('未選擇工作區');
      }
      return currentWorkspace;
    }
  };
  
  return {
    currentWorkspace,
    hasValidWorkspace,
    requireWorkspace
  };
};

// 工作區範圍內的資料操作 Hook
export const useWorkspaceData = () => {
  const { currentWorkspace, requireWorkspace } = useWorkspace();
  
  const ensureWorkspaceContext = (): Workspace => {
    return requireWorkspace();
  };
  
  return {
    currentWorkspace,
    ensureWorkspaceContext
  };
};
