// stores/appStore.ts
import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { ProcessingStage } from '../types/api';
import { ProcessedSentence } from '../types/file';
import { paperMonitorService } from '../services/paper_monitor_service';
import { apiService } from '../services/api_service';

interface ActiveTask {
  paperId: string;
  filename: string;
  progress: number;
  step: string;
}

interface AppState {
  // UI 狀態
  ui: {
    leftPanelWidth: number;
    rightPanelWidth: number;
    isPDFModalOpen: boolean;
    selectedSentenceId: string | null;
    highlightedText: string | null;
    theme: 'light' | 'dark';
  };
  
  // 進度狀態 (legacy - 保留向後兼容性)
  progress: {
    currentStage: ProcessingStage;
    percentage: number;
    details: unknown;
    isProcessing: boolean;
    error: string | null;
  };

  // NEW: 活動任務狀態 (基於 paper_id 的可靠進度追蹤)
  activeTasks: ActiveTask[];
  isUploading: boolean;

  // 引用句子
  selectedReferences: ProcessedSentence[];
  
  // 動作
  setUI: (updates: Partial<AppState['ui']>) => void;
  setProgress: (updates: Partial<AppState['progress']>) => void;
  resetProgress: () => void;
  setSelectedReferences: (references: ProcessedSentence[]) => void;
  
  // NEW: 活動任務管理動作
  addActiveTask: (task: ActiveTask) => void;
  updateActiveTask: (paperId: string, updates: Partial<ActiveTask>) => void;
  removeActiveTask: (paperId: string) => void;
  clearAllActiveTasks: () => void;
  startPaperMonitoring: (paperId: string, filename: string) => void;
  uploadPdf: (file: File) => Promise<void>;
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
          theme: 'light'
        },
        
        progress: {
          currentStage: 'idle',
          percentage: 0,
          details: null,
          isProcessing: false,
          error: null
        },

        activeTasks: [],
        isUploading: false,
        
        selectedReferences: [],
        
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
            details: null,
            isProcessing: false,
            error: null
          }
        })),

        setSelectedReferences: (references) => set({
          selectedReferences: references
        }),

        // NEW: 活動任務管理
        addActiveTask: (task) => set((state) => ({
          activeTasks: [...state.activeTasks, task]
        })),

        updateActiveTask: (paperId, updates) => set((state) => ({
          activeTasks: state.activeTasks.map(task =>
            task.paperId === paperId ? { ...task, ...updates } : task
          )
        })),

        removeActiveTask: (paperId) => set((state) => ({
          activeTasks: state.activeTasks.filter(task => task.paperId !== paperId)
        })),

        clearAllActiveTasks: () => set({ activeTasks: [] }),

        startPaperMonitoring: (paperId, filename) => {
          const { activeTasks, addActiveTask, updateActiveTask, removeActiveTask } = get();
          
          // 避免重複監控
          if (activeTasks.some(t => t.paperId === paperId)) return;

          // 立即添加任務到狀態中
          addActiveTask({
            paperId,
            filename,
            progress: 0,
            step: '排隊中...',
          });

          // 使用新的 paperMonitorService 開始監控
          paperMonitorService.startMonitoring(paperId, {
            onProgress: (status) => {
              updateActiveTask(paperId, {
                progress: status.progress?.percentage ?? 0,
                step: status.progress?.step_name ?? '處理中...',
              });
            },
            onComplete: () => {
              removeActiveTask(paperId);
              // 可以在這裡觸發論文列表刷新
            },
            onError: (errorMessage) => {
              updateActiveTask(paperId, {
                step: `錯誤: ${errorMessage.substring(0, 20)}...`,
                progress: 100,
              });
              
              // 5秒後移除錯誤任務
              setTimeout(() => {
                removeActiveTask(paperId);
              }, 5000);
            }
          });
        },

        uploadPdf: async (file) => {
          set({ isUploading: true });
          
          try {
            const response = await apiService.uploadFile(file);
            
            if (response.success && response.data?.paper_id) {
              const { paper_id, original_filename } = response.data;
              get().startPaperMonitoring(paper_id, original_filename || file.name);
            } else {
              console.error('Upload failed:', response.error);
            }
          } catch (error) {
            console.error('Upload error:', error);
          } finally {
            set({ isUploading: false });
          }
        },
      }),
      { 
        name: 'app-storage',
        // 不持久化 activeTasks 和 isUploading，因為它們是臨時狀態
        partialize: (state) => ({
          ui: state.ui,
          progress: state.progress,
          selectedReferences: state.selectedReferences
        })
      }
    )
  )
);
