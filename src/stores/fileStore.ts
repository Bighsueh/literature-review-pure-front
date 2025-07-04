// stores/fileStore.ts
import { create } from 'zustand';
import { devtools, persist, createJSONStorage } from 'zustand/middleware';
import { FileData, ProcessedSentence } from '../types/file';

interface FileState {
  // 檔案列表
  files: FileData[];
  currentFileId: string | null;
  
  // 處理後的句子
  sentences: ProcessedSentence[];
  
  // 動作
  addFile: (file: FileData) => void;
  updateFile: (id: string, updates: Partial<FileData>) => void;
  removeFile: (id: string) => void;
  setCurrentFile: (id: string | null) => void;
  setSentences: (sentences: ProcessedSentence[]) => void;
  addSentences: (sentences: ProcessedSentence[]) => void;
  clearSentences: () => void;
}

export const useFileStore = create<FileState>()(
  devtools(
    persist(
      (set) => ({
        files: [],
        currentFileId: null,
        sentences: [],
        
        addFile: (file) => set((state) => ({
          files: [...state.files, file]
        })),
        
        updateFile: (id, updates) => set((state) => ({
          files: state.files.map(file => 
            file.id === id ? { ...file, ...updates } : file
          )
        })),
        
        removeFile: (id) => set((state) => {
          // 從 sentences 中移除與文件相關的句子
          const updatedSentences = state.sentences.filter(sentence => sentence.fileId !== id);
          
          return {
            files: state.files.filter(file => file.id !== id),
            currentFileId: state.currentFileId === id ? null : state.currentFileId,
            sentences: updatedSentences
          };
        }),
        
        setCurrentFile: (id) => set({
          currentFileId: id
        }),
        
        setSentences: (sentences) => set({
          sentences
        }),
        
        addSentences: (newSentences) => set((state) => ({
          sentences: [...state.sentences, ...newSentences]
        })),
        
        clearSentences: () => set({
          sentences: []
        })
      }),
      { 
        name: 'file-storage',
        storage: createJSONStorage(() => localStorage, {
          replacer: (key, value) => {
            // 將 Date 對象轉換為 ISO 字符串
            if (value instanceof Date) {
              return value.toISOString();
            }
            // 移除 blob 屬性以避免序列化問題
            if (key === 'blob') {
              return undefined;
            }
            return value;
          },
          reviver: (key, value) => {
            // 將 uploadedAt 字符串轉換回 Date 對象
            if (key === 'uploadedAt' && typeof value === 'string') {
              return new Date(value);
            }
            return value;
          }
        })
      }
    )
  )
);
