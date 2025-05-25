// stores/appStore.ts
import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { ProcessingStage } from '../types/api';
import { ProcessedSentence } from '../types/file';

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
  
  // 進度狀態
  progress: {
    currentStage: ProcessingStage;
    percentage: number;
    details: any;
    isProcessing: boolean;
    error: string | null;
  };

  // 引用句子
  selectedReferences: ProcessedSentence[];
  
  // 動作
  setUI: (updates: Partial<AppState['ui']>) => void;
  setProgress: (updates: Partial<AppState['progress']>) => void;
  resetProgress: () => void;
  setSelectedReferences: (references: ProcessedSentence[]) => void;
}

export const useAppStore = create<AppState>()(
  devtools(
    persist(
      (set) => ({
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
        })
      }),
      { name: 'app-storage' }
    )
  )
);
