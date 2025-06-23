/**
 * 工作區核心狀態管理 - FE-02 多工作區狀態管理重構
 * 負責管理工作區資訊、當前活動工作區和工作區間的協調
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { Workspace, User } from '../../types/api';
import { workspaceApiService } from '../../services/workspace_api_service';

interface WorkspaceState {
  // 核心工作區資料
  workspaces: Workspace[];
  currentWorkspaceId: string | null;
  currentUser: User | null;
  
  // 載入狀態
  isLoading: boolean;
  error: string | null;
  
  // 工作區統計 (快取)
  workspaceStats: Record<string, {
    fileCount: number;
    chatCount: number;
    lastActivity: string;
    processingTasks: number;
  }>;
  
  // 動作
  setWorkspaces: (workspaces: Workspace[]) => void;
  setCurrentWorkspace: (workspaceId: string | null) => void;
  setCurrentUser: (user: User | null) => void;
  
  // 工作區管理
  addWorkspace: (workspace: Workspace) => void;
  updateWorkspace: (workspaceId: string, updates: Partial<Workspace>) => void;
  removeWorkspace: (workspaceId: string) => void;
  
  // 載入狀態管理
  setLoading: (isLoading: boolean) => void;
  setError: (error: string | null) => void;
  
  // 統計資料管理
  updateWorkspaceStats: (workspaceId: string, stats: Partial<WorkspaceState['workspaceStats'][string]>) => void;
  
  // 工作區操作
  createWorkspace: (name: string) => Promise<Workspace | null>;
  switchToWorkspace: (workspaceId: string) => Promise<boolean>;
  refreshWorkspaces: () => Promise<void>;
  
  // 清理
  clearWorkspaceData: () => void;
}

export const useWorkspaceStore = create<WorkspaceState>()(
  devtools(
    persist(
      (set, get) => ({
        // 初始狀態
        workspaces: [],
        currentWorkspaceId: null,
        currentUser: null,
        isLoading: false,
        error: null,
        workspaceStats: {},
        
        // 基礎設置動作
        setWorkspaces: (workspaces) => set({ workspaces }),
        
        setCurrentWorkspace: (workspaceId) => {
          set({ currentWorkspaceId: workspaceId });
          if (workspaceId) {
            workspaceApiService.setCurrentWorkspace(workspaceId);
          } else {
            workspaceApiService.clearCurrentWorkspace();
          }
        },
        
        setCurrentUser: (user) => set({ currentUser: user }),
        
        // 工作區管理
        addWorkspace: (workspace) => set((state) => ({
          workspaces: [...state.workspaces, workspace]
        })),
        
        updateWorkspace: (workspaceId, updates) => set((state) => ({
          workspaces: state.workspaces.map(workspace =>
            workspace.id === workspaceId ? { ...workspace, ...updates } : workspace
          )
        })),
        
        removeWorkspace: (workspaceId) => set((state) => {
          const newWorkspaces = state.workspaces.filter(w => w.id !== workspaceId);
          const newCurrentWorkspaceId = state.currentWorkspaceId === workspaceId 
            ? (newWorkspaces.length > 0 ? newWorkspaces[0].id : null)
            : state.currentWorkspaceId;
          
          // 同步到 API 服務
          if (newCurrentWorkspaceId) {
            workspaceApiService.setCurrentWorkspace(newCurrentWorkspaceId);
          } else {
            workspaceApiService.clearCurrentWorkspace();
          }
          
          return {
            workspaces: newWorkspaces,
            currentWorkspaceId: newCurrentWorkspaceId
          };
        }),
        
        // 載入狀態管理
        setLoading: (isLoading) => set({ isLoading }),
        setError: (error) => set({ error }),
        
        // 統計資料管理
        updateWorkspaceStats: (workspaceId, stats) => set((state) => ({
          workspaceStats: {
            ...state.workspaceStats,
            [workspaceId]: {
              ...state.workspaceStats[workspaceId],
              ...stats
            }
          }
        })),
        
        // 工作區操作
        createWorkspace: async (name) => {
          set({ isLoading: true, error: null });
          
          try {
            const response = await workspaceApiService.createWorkspace({ name });
            
            if (response.success && response.data) {
              const newWorkspace = response.data;
              
              // 更新狀態
              get().addWorkspace(newWorkspace);
              
              // 如果這是第一個工作區，自動切換到它
              if (get().workspaces.length === 1) {
                get().setCurrentWorkspace(newWorkspace.id);
              }
              
              set({ isLoading: false });
              return newWorkspace;
            } else {
              set({ isLoading: false, error: response.error || 'Failed to create workspace' });
              return null;
            }
          } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Unknown error';
            set({ isLoading: false, error: errorMessage });
            return null;
          }
        },
        
        switchToWorkspace: async (workspaceId) => {
          const workspace = get().workspaces.find(w => w.id === workspaceId);
          if (!workspace) {
            set({ error: 'Workspace not found' });
            return false;
          }
          
          try {
            // 切換工作區
            get().setCurrentWorkspace(workspaceId);
            
            // 更新最後活動時間
            get().updateWorkspaceStats(workspaceId, {
              lastActivity: new Date().toISOString()
            });
            
            return true;
          } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to switch workspace';
            set({ error: errorMessage });
            return false;
          }
        },
        
        refreshWorkspaces: async () => {
          set({ isLoading: true, error: null });
          
          try {
            const response = await workspaceApiService.getWorkspaces();
            
            if (response.success && response.data) {
              set({ 
                workspaces: response.data,
                isLoading: false 
              });
              
              // 如果當前工作區不在新列表中，切換到第一個可用的工作區
              const currentWorkspaceId = get().currentWorkspaceId;
              if (currentWorkspaceId && !response.data.some(w => w.id === currentWorkspaceId)) {
                if (response.data.length > 0) {
                  get().setCurrentWorkspace(response.data[0].id);
                } else {
                  get().setCurrentWorkspace(null);
                }
              }
            } else {
              set({ 
                isLoading: false, 
                error: response.error || 'Failed to fetch workspaces' 
              });
            }
          } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Unknown error';
            set({ isLoading: false, error: errorMessage });
          }
        },
        
        // 清理
        clearWorkspaceData: () => set({
          workspaces: [],
          currentWorkspaceId: null,
          currentUser: null,
          isLoading: false,
          error: null,
          workspaceStats: {}
        })
      }),
      {
        name: 'workspace-storage',
        partialize: (state) => ({
          // 持久化工作區列表和當前工作區
          workspaces: state.workspaces,
          currentWorkspaceId: state.currentWorkspaceId,
          currentUser: state.currentUser,
          workspaceStats: state.workspaceStats
          // 不持久化載入狀態和錯誤狀態
        })
      }
    ),
    { name: 'WorkspaceStore' }
  )
);

// 工作區相關的選擇器 (selectors)
export const useCurrentWorkspace = () => {
  return useWorkspaceStore((state) => {
    const currentWorkspaceId = state.currentWorkspaceId;
    return currentWorkspaceId 
      ? state.workspaces.find(w => w.id === currentWorkspaceId) || null
      : null;
  });
};

export const useWorkspaceStats = (workspaceId: string) => {
  return useWorkspaceStore((state) => state.workspaceStats[workspaceId] || {
    fileCount: 0,
    chatCount: 0,
    lastActivity: new Date().toISOString(),
    processingTasks: 0
  });
};

// 工作區驗證 Hook
export const useWorkspaceValidation = () => {
  const { currentWorkspaceId, workspaces } = useWorkspaceStore();
  
  const isWorkspaceValid = () => {
    return currentWorkspaceId && workspaces.some(w => w.id === currentWorkspaceId);
  };
  
  const requireValidWorkspace = () => {
    if (!isWorkspaceValid()) {
      throw new Error('No valid workspace selected');
    }
    return currentWorkspaceId!;
  };
  
  return {
    currentWorkspaceId,
    isWorkspaceValid,
    requireValidWorkspace
  };
}; 