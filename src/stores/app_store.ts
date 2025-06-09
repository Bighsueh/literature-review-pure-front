import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { ProcessingStage } from '../types/api';
import { ProcessedSentence } from '../types/file';
import { PaperInfo } from '../services/api_service';
import { paperService } from '../services/paper_service';
import { paperMonitorService } from '../services/paper_monitor_service';

interface AppState {
  // UI 狀態
  ui: {
    leftPanelWidth: number;
    rightPanelWidth: number;
    isPDFModalOpen: boolean;
    selectedSentenceId: string | null;
    highlightedText: string | null;
    theme: 'light' | 'dark';
    isLoading: boolean;
    errorMessage: string | null;
  };
  
  // 論文狀態
  papers: {
    list: PaperInfo[];
    selectedIds: string[];
    lastUpdated: number | null;
  };
  
  // 進度狀態 (保留向後兼容性)
  progress: {
    currentStage: ProcessingStage;
    percentage: number;
    details: Record<string, unknown>;
    isProcessing: boolean;
    error: string | null;
  };

  // NEW: 任務追蹤 (基於 paper_id 而非 task_id)
  activeTasks: Map<string, {
    paperId: string;
    fileName: string;
    status: string;
    progress: number;
    stepName: string;
    startTime: number;
  }>;

  // 引用句子
  selectedReferences: ProcessedSentence[];
  
  // 服務狀態
  services: {
    api: boolean;
    grobid: boolean;
    n8n: boolean;
    split_sentences: boolean;
    database: boolean;
    lastChecked: number | null;
  };
  
  // 動作
  setUI: (updates: Partial<AppState['ui']>) => void;
  setProgress: (updates: Partial<AppState['progress']>) => void;
  resetProgress: () => void;
  setSelectedReferences: (references: ProcessedSentence[]) => void;
  
  // NEW: Paper-based 任務管理動作
  addTask: (paperId: string, fileName: string) => void;
  updateTaskProgress: (paperId: string, progress: number, stepName: string, status: string) => void;
  removeTask: (paperId: string) => void;
  startPaperMonitoring: (paperId: string) => void;
  stopPaperMonitoring: (paperId: string) => void;
  
  // 論文管理動作
  refreshPapers: () => Promise<void>;
  uploadPaper: (file: File) => Promise<{ success: boolean; error?: string }>;
  togglePaperSelection: (paperId: string) => Promise<void>;
  deletePaper: (paperId: string) => Promise<void>;
  startProcessing: () => Promise<void>;
  stopProcessing: () => Promise<void>;
  
  // 服務狀態動作
  checkServiceHealth: () => Promise<void>;
  
  // 錯誤處理
  setError: (error: string | null) => void;
  clearError: () => void;
}

export const useAppStore = create<AppState>()(
  devtools(
    persist(
      (set, get) => ({
        ui: {
          leftPanelWidth: 300,
          rightPanelWidth: 300,
          isPDFModalOpen: false,
          selectedSentenceId: null,
          highlightedText: null,
          theme: 'light',
          isLoading: false,
          errorMessage: null,
        },
        
        papers: {
          list: [],
          selectedIds: [],
          lastUpdated: null,
        },
        
        progress: {
          currentStage: 'idle',
          percentage: 0,
          details: {},
          isProcessing: false,
          error: null,
        },

        activeTasks: new Map(),
        
        selectedReferences: [],
        
        services: {
          api: false,
          grobid: false,
          n8n: false,
          split_sentences: false,
          database: false,
          lastChecked: null,
        },
        
        // UI 動作
        setUI: (updates) => set((state) => ({
          ui: { ...state.ui, ...updates }
        })),
        
        setProgress: (updates) => set((state) => ({
          progress: { ...state.progress, ...updates }
        })),
        
        resetProgress: () => set(() => ({
          progress: {
            currentStage: 'idle',
            percentage: 0,
            details: {},
            isProcessing: false,
            error: null
          }
        })),

        setSelectedReferences: (references) => set({
          selectedReferences: references
        }),

        // NEW: Paper-based 任務管理動作
        addTask: (paperId: string, fileName: string) => {
          const state = get();
          const newTasks = new Map(state.activeTasks);
          newTasks.set(paperId, {
            paperId,
            fileName,
            status: 'pending',
            progress: 0,
            stepName: '準備中...',
            startTime: Date.now(),
          });
          set({ activeTasks: newTasks });
        },

        updateTaskProgress: (paperId: string, progress: number, stepName: string, status: string) => {
          const state = get();
          const newTasks = new Map(state.activeTasks);
          const task = newTasks.get(paperId);
          if (task) {
            newTasks.set(paperId, {
              ...task,
              progress,
              stepName,
              status,
            });
            set({ activeTasks: newTasks });
          }
        },

        removeTask: (paperId: string) => {
          const state = get();
          const newTasks = new Map(state.activeTasks);
          newTasks.delete(paperId);
          set({ activeTasks: newTasks });
        },

        startPaperMonitoring: (paperId: string) => {
          const actions = get();
          const task = actions.activeTasks.get(paperId);
          if (!task) return;
          
          paperMonitorService.startMonitoring(paperId, {
            onProgress: (status) => {
              // 更新任務進度
              actions.updateTaskProgress(
                paperId,
                status.progress?.percentage ?? 0,
                status.progress?.step_name ?? '處理中...',
                status.status
              );
              
              // 更新全局進度狀態以保持向後兼容性
              actions.setProgress({
                currentStage: 'analyzing',
                percentage: status.progress?.percentage ?? 0,
                details: {
                  stepName: status.progress?.step_name,
                  ...(typeof status.progress?.details === 'object' && status.progress?.details ? status.progress.details as Record<string, unknown> : {})
                },
                isProcessing: true,
                error: null
              });
            },
            onComplete: (status) => {
              // 任務完成
              actions.updateTaskProgress(paperId, 100, '處理完成', 'completed');
              setTimeout(() => actions.removeTask(paperId), 2000);
              
              // 重新載入論文列表以獲取最新狀態
              actions.refreshPapers();
              
              // 重置進度狀態
              actions.setProgress({
                currentStage: 'completed',
                percentage: 100,
                details: { 
                  message: '檔案處理完成！',
                  paperId: status.paper_id
                },
                isProcessing: false,
                error: null
              });
              
              console.log(`Paper processing completed: ${paperId}`);
            },
            onError: (error) => {
              // 任務失敗
              actions.updateTaskProgress(paperId, 0, '處理失敗', 'error');
              setTimeout(() => actions.removeTask(paperId), 5000);
              
              // 設置錯誤狀態
              actions.setProgress({
                currentStage: 'error',
                percentage: 0,
                details: { message: error },
                isProcessing: false,
                error: error
              });
              
              console.error(`Paper processing failed: ${paperId}`, error);
            }
          });
        },

        stopPaperMonitoring: (paperId: string) => {
          paperMonitorService.stopMonitoring(paperId);
        },
        
        // 論文管理動作
        refreshPapers: async () => {
          const state = get();
          set({ ui: { ...state.ui, isLoading: true, errorMessage: null } });
          
          try {
            const papers = await paperService.getAllPapers();
            const selectedIds = papers.filter(p => p.selected).map(p => p.id);
            
            set({
              papers: {
                list: papers,
                selectedIds,
                lastUpdated: Date.now(),
              },
              ui: { ...state.ui, isLoading: false },
            });
          } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to refresh papers';
            set({
              ui: { ...state.ui, isLoading: false, errorMessage },
            });
          }
        },
        
        uploadPaper: async (file: File) => {
          const state = get();
          const actions = get();
          set({ ui: { ...state.ui, isLoading: true, errorMessage: null } });
          
          try {
            const result = await paperService.uploadPdf(file);
            
            if (result.success) {
              const { file_id, duplicate } = result;
              
              // 如果是新檔案，開始監控進度
              if (file_id && !duplicate) {
                actions.addTask(file_id, file.name);
                actions.startPaperMonitoring(file_id);
              }
              
              // 刷新論文列表
              await get().refreshPapers();
              set({ ui: { ...state.ui, isLoading: false } });
              return { success: true };
            } else {
              set({
                ui: { ...state.ui, isLoading: false, errorMessage: result.error || 'Upload failed' },
              });
              return { success: false, error: result.error };
            }
          } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Upload failed';
            set({
              ui: { ...state.ui, isLoading: false, errorMessage },
            });
            return { success: false, error: errorMessage };
          }
        },
        
        togglePaperSelection: async (paperId: string) => {
          const state = get();
          const paper = state.papers.list.find(p => p.id === paperId);
          if (!paper) return;
          
          try {
            const success = await paperService.togglePaperSelection(paperId, !paper.selected);
            
            if (success) {
              // 更新本地狀態
              const updatedPapers = state.papers.list.map(p => 
                p.id === paperId ? { ...p, selected: !p.selected } : p
              );
              const selectedIds = updatedPapers.filter(p => p.selected).map(p => p.id);
              
              set({
                papers: {
                  ...state.papers,
                  list: updatedPapers,
                  selectedIds,
                },
              });
            }
          } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to toggle selection';
            set({
              ui: { ...state.ui, errorMessage },
            });
          }
        },
        
        deletePaper: async (paperId: string) => {
          const state = get();
          set({ ui: { ...state.ui, isLoading: true, errorMessage: null } });
          
          try {
            const success = await paperService.deletePaper(paperId);
            
            if (success) {
              // 移除本地狀態中的論文
              const updatedPapers = state.papers.list.filter(p => p.id !== paperId);
              const selectedIds = updatedPapers.filter(p => p.selected).map(p => p.id);
              
              set({
                papers: {
                  ...state.papers,
                  list: updatedPapers,
                  selectedIds,
                },
                ui: { ...state.ui, isLoading: false },
              });
            } else {
              set({
                ui: { ...state.ui, isLoading: false, errorMessage: 'Failed to delete paper' },
              });
            }
          } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to delete paper';
            set({
              ui: { ...state.ui, isLoading: false, errorMessage },
            });
          }
        },
        
        startProcessing: async () => {
          const state = get();
          
          try {
            const success = await paperService.startProcessing();
            
            if (success) {
              set({
                                 progress: {
                   ...state.progress,
                   isProcessing: true,
                   currentStage: 'analyzing',
                   error: null,
                 },
              });
            } else {
              set({
                ui: { ...state.ui, errorMessage: 'Failed to start processing' },
              });
            }
          } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to start processing';
            set({
              ui: { ...state.ui, errorMessage },
            });
          }
        },
        
        stopProcessing: async () => {
          const state = get();
          
          try {
            const success = await paperService.stopProcessing();
            
            if (success) {
              set({
                progress: {
                  ...state.progress,
                  isProcessing: false,
                  currentStage: 'idle',
                },
              });
            } else {
              set({
                ui: { ...state.ui, errorMessage: 'Failed to stop processing' },
              });
            }
          } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to stop processing';
            set({
              ui: { ...state.ui, errorMessage },
            });
          }
        },
        
        // 服務狀態檢查
        checkServiceHealth: async () => {
          try {
            const status = await paperService.checkServiceHealth();
            
            set({
              services: {
                ...status,
                lastChecked: Date.now(),
              },
            });
          } catch (error) {
            console.error('Failed to check service health:', error);
            set({
              services: {
                api: false,
                grobid: false,
                n8n: false,
                split_sentences: false,
                database: false,
                lastChecked: Date.now(),
              },
            });
          }
        },
        
        // 錯誤處理
        setError: (error: string | null) => set((state) => ({
          ui: { ...state.ui, errorMessage: error }
        })),
        
        clearError: () => set((state) => ({
          ui: { ...state.ui, errorMessage: null }
        })),
      }),
      { 
        name: 'app-storage',
        // 只持久化 UI 偏好設定，其他狀態由 API 管理
        partialize: (state) => ({
          ui: {
            leftPanelWidth: state.ui.leftPanelWidth,
            rightPanelWidth: state.ui.rightPanelWidth,
            theme: state.ui.theme,
          },
        }),
      }
    ),
    { name: 'app-store' }
  )
);

// 註冊 paperService 的刷新回調以實現多Client同步
paperService.onRefresh(() => {
  const store = useAppStore.getState();
  store.refreshPapers();
});

export default useAppStore; 