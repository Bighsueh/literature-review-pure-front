/**
 * 工作區檔案狀態管理 - FE-02 多工作區狀態管理重構
 * 負責特定工作區的檔案、論文和處理狀態管理
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { Paper, TaskStatus, UploadResponse } from '../../types/api';
import { workspaceApiService } from '../../services/workspace_api_service';
import { useWorkspaceStore } from './workspaceStore';
import { paperMonitorService } from '../../services/paper_monitor_service';

// 導入全局 appStore 以整合進度監控
import { useAppStore } from '../appStore';

// 工作區檔案狀態接口
interface WorkspaceFileState {
  // 論文/檔案資料
  papers: Paper[];
  selectedPaperIds: Set<string>;
  
  // 處理狀態
  processingTasks: Record<string, TaskStatus>; // paperId -> TaskStatus
  uploadingFiles: Record<string, { fileName: string; progress: number }>; // uploadId -> progress
  
  // UI 狀態
  isLoading: boolean;
  error: string | null;
  lastRefreshTime: string | null;
  
  // 動作
  setPapers: (papers: Paper[]) => void;
  addPaper: (paper: Paper) => void;
  updatePaper: (paperId: string, updates: Partial<Paper>) => void;
  removePaper: (paperId: string) => void;
  
  // 選擇管理
  togglePaperSelection: (paperId: string) => void;
  setBatchSelection: (paperIds: string[], selected: boolean) => void;
  clearSelection: () => void;
  selectAll: () => void;
  
  // 處理狀態管理
  setProcessingTask: (paperId: string, task: TaskStatus) => void;
  updateProcessingTask: (paperId: string, updates: Partial<TaskStatus>) => void;
  removeProcessingTask: (paperId: string) => void;
  
  // 上傳狀態管理
  setUploadProgress: (uploadId: string, fileName: string, progress: number) => void;
  removeUploadProgress: (uploadId: string) => void;
  
  // 載入狀態
  setLoading: (isLoading: boolean) => void;
  setError: (error: string | null) => void;
  
  // API 操作
  refreshPapers: () => Promise<void>;
  uploadFile: (file: File) => Promise<UploadResponse | null>;
  deletePaper: (paperId: string) => Promise<boolean>;
}

// 創建工作區檔案狀態管理工廠
const createWorkspaceFileStore = (workspaceId: string) => {
  const store = create<WorkspaceFileState>()(
    devtools(
      persist(
        (set, get) => ({
          // 初始狀態
          papers: [],
          selectedPaperIds: new Set(),
          processingTasks: {},
          uploadingFiles: {},
          isLoading: false,
          error: null,
          lastRefreshTime: null,
          
          // 基礎資料操作
          setPapers: (papers) => {
            set({ 
              papers,
              lastRefreshTime: new Date().toISOString()
            });
          },
          
          addPaper: (paper) => set((state) => ({
            papers: [...state.papers, paper]
          })),
          
          updatePaper: (paperId, updates) => set((state) => ({
            papers: state.papers.map(paper =>
              paper.id === paperId ? { ...paper, ...updates } : paper
            )
          })),
          
          removePaper: (paperId) => set((state) => {
            const newSelectedPaperIds = new Set(state.selectedPaperIds);
            newSelectedPaperIds.delete(paperId);
            
            const newProcessingTasks = { ...state.processingTasks };
            delete newProcessingTasks[paperId];
            
            return {
              papers: state.papers.filter(p => p.id !== paperId),
              selectedPaperIds: newSelectedPaperIds,
              processingTasks: newProcessingTasks
            };
          }),
          
          // 選擇管理
          togglePaperSelection: (paperId) => set((state) => {
            const newSelectedPaperIds = new Set(state.selectedPaperIds);
            if (newSelectedPaperIds.has(paperId)) {
              newSelectedPaperIds.delete(paperId);
            } else {
              newSelectedPaperIds.add(paperId);
            }
            return { selectedPaperIds: newSelectedPaperIds };
          }),
          
          setBatchSelection: (paperIds, selected) => set((state) => {
            const newSelectedPaperIds = new Set(state.selectedPaperIds);
            paperIds.forEach(id => {
              if (selected) {
                newSelectedPaperIds.add(id);
              } else {
                newSelectedPaperIds.delete(id);
              }
            });
            return { selectedPaperIds: newSelectedPaperIds };
          }),
          
          clearSelection: () => set({ selectedPaperIds: new Set() }),
          
          selectAll: () => set((state) => ({
            selectedPaperIds: new Set(state.papers.map(p => p.id))
          })),
          
          // 處理狀態管理
          setProcessingTask: (paperId, task) => set((state) => ({
            processingTasks: {
              ...state.processingTasks,
              [paperId]: task
            }
          })),
          
          updateProcessingTask: (paperId, updates) => set((state) => {
            const currentTask = state.processingTasks[paperId];
            if (!currentTask) return state;
            
            return {
              processingTasks: {
                ...state.processingTasks,
                [paperId]: { ...currentTask, ...updates }
              }
            };
          }),
          
          removeProcessingTask: (paperId) => set((state) => {
            const newProcessingTasks = { ...state.processingTasks };
            delete newProcessingTasks[paperId];
            return { processingTasks: newProcessingTasks };
          }),
          
          // 上傳狀態管理
          setUploadProgress: (uploadId, fileName, progress) => set((state) => ({
            uploadingFiles: {
              ...state.uploadingFiles,
              [uploadId]: { fileName, progress }
            }
          })),
          
          removeUploadProgress: (uploadId) => set((state) => {
            const newUploadingFiles = { ...state.uploadingFiles };
            delete newUploadingFiles[uploadId];
            return { uploadingFiles: newUploadingFiles };
          }),
          
          // 載入狀態
          setLoading: (isLoading) => set({ isLoading }),
          setError: (error) => set({ error }),
          
          // API 操作
          refreshPapers: async () => {
            set({ isLoading: true, error: null });
            
            try {
              const response = await workspaceApiService.getPapers();
              
              if (response.success && response.data) {
                // 後端返回的是分頁響應格式，被前端包裝在 ApiResponse 中
                // response.data 就是 PaginatedResponse<Paper>
                const papers = response.data.items || [];
                get().setPapers(papers);
                set({ isLoading: false });
                
                console.log(`✅ 成功載入 ${papers.length} 個檔案`);
              } else {
                set({ 
                  isLoading: false, 
                  error: response.error || 'Failed to fetch papers' 
                });
                console.error('❌ 載入檔案失敗:', response.error);
              }
            } catch (error) {
              const errorMessage = error instanceof Error ? error.message : 'Unknown error';
              set({ isLoading: false, error: errorMessage });
              console.error('❌ 載入檔案異常:', errorMessage);
            }
          },
          
          uploadFile: async (file) => {
            const uploadId = `upload_${Date.now()}`;
            
            try {
              get().setUploadProgress(uploadId, file.name, 0);
              
              const response = await workspaceApiService.uploadFile(file);
              
              if (response.success && response.data) {
                get().setUploadProgress(uploadId, file.name, 100);
                
                // 整合全局進度監控：開始監控檔案處理進度
                const { paper_id, original_filename } = response.data;
                if (paper_id) {
                  // 使用全局 appStore 的進度監控
                  const globalStore = useAppStore.getState();
                  globalStore.startPaperMonitoring(paper_id, original_filename || file.name);
                }
                
                setTimeout(() => {
                  get().removeUploadProgress(uploadId);
                }, 2000);
                
                await get().refreshPapers();
                return response.data;
              } else {
                get().removeUploadProgress(uploadId);
                set({ error: response.error || 'Upload failed' });
                return null;
              }
            } catch (error) {
              get().removeUploadProgress(uploadId);
              const errorMessage = error instanceof Error ? error.message : 'Upload error';
              set({ error: errorMessage });
              return null;
            }
          },
          
          deletePaper: async (paperId) => {
            try {
              const response = await workspaceApiService.deletePaper(paperId);
              
              if (response.success) {
                get().removePaper(paperId);
                return true;
              } else {
                set({ error: response.error || 'Delete failed' });
                return false;
              }
            } catch (error) {
              const errorMessage = error instanceof Error ? error.message : 'Delete error';
              set({ error: errorMessage });
              return false;
            }
          }
        }),
        {
          name: `workspace-files-${workspaceId}`,
          partialize: (state) => ({
            papers: state.papers,
            selectedPaperIds: Array.from(state.selectedPaperIds),
            lastRefreshTime: state.lastRefreshTime
          }),
          onRehydrateStorage: () => (state) => {
            if (state && Array.isArray(state.selectedPaperIds)) {
              state.selectedPaperIds = new Set(state.selectedPaperIds as string[]);
            }
          }
        }
      ),
      { name: `WorkspaceFileStore-${workspaceId}` }
    )
  );
  
  // 註冊 paperMonitorService 的回呼
  paperMonitorService.registerOnStatusChange((paperId: string) => {
    console.log(`Received status change for paper ${paperId}, refreshing papers...`);
    store.getState().refreshPapers();
  });

  return store;
};

// 工作區檔案 stores 快取
const workspaceFileStores: Record<string, ReturnType<typeof createWorkspaceFileStore>> = {};

// 獲取或創建工作區檔案 store
export const getWorkspaceFileStore = (workspaceId: string) => {
  if (!workspaceFileStores[workspaceId]) {
    workspaceFileStores[workspaceId] = createWorkspaceFileStore(workspaceId);
  }
  return workspaceFileStores[workspaceId];
};

// Hook：使用指定工作區的檔案 store
export const useWorkspaceFileStore = (workspaceId: string) => {
  if (!workspaceId) {
    // 返回預設的空狀態而不是拋出錯誤
    return {
      papers: [] as Paper[], // 確保始終是陣列
      selectedPaperIds: new Set<string>(),
      processingTasks: {} as Record<string, TaskStatus>,
      uploadingFiles: {} as Record<string, { fileName: string; progress: number }>,
      isLoading: false,
      error: null,
      lastRefreshTime: null,
      setPapers: () => {},
      addPaper: () => {},
      updatePaper: () => {},
      removePaper: () => {},
      togglePaperSelection: () => {},
      setBatchSelection: () => {},
      clearSelection: () => {},
      selectAll: () => {},
      setProcessingTask: () => {},
      updateProcessingTask: () => {},
      removeProcessingTask: () => {},
      setUploadProgress: () => {},
      removeUploadProgress: () => {},
      setLoading: () => {},
      setError: () => {},
      refreshPapers: async () => {},
      uploadFile: async () => null,
      deletePaper: async () => false
    };
  }
  
  const store = getWorkspaceFileStore(workspaceId)();
  
  // 確保 papers 始終是陣列
  return {
    ...store,
    papers: Array.isArray(store.papers) ? store.papers : []
  };
};

// Hook：使用當前工作區的檔案 store
export const useCurrentWorkspaceFileStore = () => {
  const currentWorkspaceId = useWorkspaceStore((state) => state.currentWorkspaceId);
  
  if (!currentWorkspaceId) {
    throw new Error('No current workspace selected');
  }
  
  return getWorkspaceFileStore(currentWorkspaceId)();
}; 