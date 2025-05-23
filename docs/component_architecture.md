# 核心組件設計與實作規範

## 1. 專案結構設計

```
src/
├── components/           # React 組件
│   ├── common/          # 通用組件
│   │   ├── Modal/
│   │   ├── ProgressBar/
│   │   └── Toast/
│   ├── file/            # 檔案相關組件  
│   │   ├── FileUploadZone/
│   │   ├── FileList/
│   │   └── PDFPreview/
│   ├── chat/            # 聊天相關組件
│   │   ├── ChatMessageList/
│   │   ├── ChatInput/
│   │   └── MessageBubble/
│   └── progress/        # 進度相關組件
│       ├── ProgressDisplay/
│       └── ReferencesPanel/
├── hooks/               # 自定義 Hooks
│   ├── useFileProcessor.ts
│   ├── useQueryProcessor.ts
│   ├── useProgress.ts
│   └── usePDFViewer.ts
├── services/            # API 服務層
│   ├── splitSentencesAPI.ts
│   ├── n8nAPI.ts
│   └── localStorageService.ts
├── stores/              # Zustand 狀態管理
│   ├── appStore.ts
│   ├── fileStore.ts
│   └── chatStore.ts
├── types/               # TypeScript 類型定義
│   ├── api.ts
│   ├── file.ts
│   └── chat.ts
├── utils/               # 工具函數
│   ├── fileUtils.ts
│   ├── progressUtils.ts
│   └── pdfUtils.ts
└── constants/           # 常量配置
    ├── apiConfig.ts
    └── uiConfig.ts
```

## 2. 核心類型定義

### 2.1 API 相關類型
```typescript
// types/api.ts
export interface SplitSentencesResponse {
  sentences: string[];
}

export interface N8nOdCdResponse {
  defining_type: string;
  reason: string;
}

export interface N8nKeywordResponse {
  output: {
    keywords: string[];
  };
}

export interface N8nOrganizeResponse {
  output: {
    response: string;
  };
}

export interface APIError {
  message: string;
  code: string;
  details?: any;
}
```

### 2.2 檔案相關類型
```typescript
// types/file.ts
export interface FileData {
  id: string;
  name: string;
  size: number;
  type: string;
  uploadedAt: Date;
  status: FileStatus;
  processingProgress?: number;
  blob?: Blob; // 儲存原始檔案內容
}

export type FileStatus = 
  | 'uploading'
  | 'processing' 
  | 'completed'
  | 'error';

export interface ProcessedSentence {
  id: string;
  content: string;
  type: 'OD' | 'CD' | 'OTHER';
  reason: string;
  fileId: string;
  pageNumber?: number;
  position?: TextPosition;
}

export interface TextPosition {
  x: number;
  y: number;
  width: number;
  height: number;
}
```

### 2.3 聊天相關類型
```typescript
// types/chat.ts
export interface Message {
  id: string;
  type: 'user' | 'system';
  content: string;
  timestamp: Date;
  references?: ProcessedSentence[];
  metadata?: MessageMetadata;
}

export interface MessageMetadata {
  query?: string;
  keywords?: string[];
  processingTime?: number;
  totalReferences?: number;
}

export interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
}
```

## 3. 狀態管理設計

### 3.1 主要應用狀態
```typescript
// stores/appStore.ts
import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

interface AppState {
  // UI 狀態
  ui: {
    leftPanelWidth: number;
    rightPanelWidth: number;
    isPDFModalOpen: boolean;
    selectedSentenceId: string | null;
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
  
  // 動作
  setUI: (updates: Partial<AppState['ui']>) => void;
  setProgress: (updates: Partial<AppState['progress']>) => void;
  resetProgress: () => void;
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
          theme: 'light'
        },
        
        progress: {
          currentStage: 'idle',
          percentage: 0,
          details: null,
          isProcessing: false,
          error: null
        },
        
        setUI: (updates) => set((state) => ({
          ui: { ...state.ui, ...updates }
        })),
        
        setProgress: (updates) => set((state) => ({
          progress: { ...state.progress, ...updates }
        })),
        
        resetProgress: () => set((state) => ({
          progress: {
            currentStage: 'idle',
            percentage: 0,
            details: null,
            isProcessing: false,
            error: null
          }
        }))
      }),
      {
        name: 'app-store',
        partialize: (state) => ({ ui: state.ui }) // 只持久化 UI 狀態
      }
    )
  )
);
```

### 3.2 檔案狀態管理
```typescript
// stores/fileStore.ts
interface FileState {
  files: FileData[];
  currentFileId: string | null;
  sentences: Record<string, ProcessedSentence[]>;
  
  // 動作
  addFile: (file: FileData) => void;
  updateFile: (id: string, updates: Partial<FileData>) => void;
  removeFile: (id: string) => void;
  setSentences: (fileId: string, sentences: ProcessedSentence[]) => void;
  setCurrentFile: (id: string | null) => void;
}

export const useFileStore = create<FileState>()(
  devtools(
    persist(
      (set, get) => ({
        files: [],
        currentFileId: null,
        sentences: {},
        
        addFile: (file) => set((state) => ({
          files: [...state.files, file]
        })),
        
        updateFile: (id, updates) => set((state) => ({
          files: state.files.map(f => 
            f.id === id ? { ...f, ...updates } : f
          )
        })),
        
        removeFile: (id) => set((state) => {
          const { [id]: removed, ...rest } = state.sentences;
          return {
            files: state.files.filter(f => f.id !== id),
            sentences: rest,
            currentFileId: state.currentFileId === id ? null : state.currentFileId
          };
        }),
        
        setSentences: (fileId, sentences) => set((state) => ({
          sentences: { ...state.sentences, [fileId]: sentences }
        })),
        
        setCurrentFile: (id) => set({ currentFileId: id })
      }),
      {
        name: 'file-store'
      }
    )
  )
);
```

## 4. API 服務層設計

### 4.1 Split Sentences API
```typescript
// services/splitSentencesAPI.ts
import axios from 'axios';
import { API_CONFIG } from '../constants/apiConfig';

export class SplitSentencesAPI {
  private client = axios.create({
    baseURL: API_CONFIG.splitSentences.baseUrl,
    timeout: 60000 // 60 秒超時
  });

  async processPDF(file: File): Promise<string[]> {
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await this.client.post<SplitSentencesResponse>(
        API_CONFIG.splitSentences.endpoint,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data'
          },
          onUploadProgress: (progressEvent) => {
            const percentCompleted = Math.round(
              (progressEvent.loaded * 100) / (progressEvent.total || 1)
            );
            // 可以在這裡更新上傳進度
            console.log(`Upload progress: ${percentCompleted}%`);
          }
        }
      );

      return response.data.sentences;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new APIError(
          error.response?.data?.message || 'Split sentences API 錯誤',
          error.response?.status?.toString() || 'UNKNOWN'
        );
      }
      throw error;
    }
  }

  async healthCheck(): Promise<boolean> {
    try {
      await this.client.get('/health');
      return true;
    } catch {
      return false;
    }
  }
}

export const splitSentencesAPI = new SplitSentencesAPI();
```

### 4.2 N8n API 服務
```typescript
// services/n8nAPI.ts
import axios from 'axios';
import { API_CONFIG } from '../constants/apiConfig';

export class N8nAPI {
  private client = axios.create({
    baseURL: API_CONFIG.n8n.baseUrl,
    timeout: 180000 // 3 分鐘超時（組織回答 API 需要較長時間）
  });

  async checkOdCd(sentence: string): Promise<N8nOdCdResponse> {
    const formData = new URLSearchParams();
    formData.append('sentence', sentence);

    const response = await this.client.post<N8nOdCdResponse>(
      API_CONFIG.n8n.endpoints.checkOdCd,
      formData,
      {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      }
    );

    return response.data;
  }

  async extractKeywords(query: string): Promise<N8nKeywordResponse[]> {
    const formData = new URLSearchParams();
    formData.append('query', query);

    const response = await this.client.post<N8nKeywordResponse[]>(
      API_CONFIG.n8n.endpoints.keywordExtraction,
      formData,
      {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      }
    );

    return response.data;
  }

  async organizeResponse(data: {
    "operational definition": string[];
    "conceptual definition": string[];
    "query": string;
  }): Promise<N8nOrganizeResponse[]> {
    const response = await this.client.post<N8nOrganizeResponse[]>(
      API_CONFIG.n8n.endpoints.organizeResponse,
      [data],
      {
        headers: {
          'Content-Type': 'application/json'
        }
      }
    );

    return response.data;
  }
}

export const n8nAPI = new N8nAPI();
```

## 5. 核心業務邏輯 Hooks

### 5.1 檔案處理 Hook
```typescript
// hooks/useFileProcessor.ts
import { useCallback } from 'react';
import { useAppStore } from '../stores/appStore';
import { useFileStore } from '../stores/fileStore';
import { splitSentencesAPI } from '../services/splitSentencesAPI';
import { n8nAPI } from '../services/n8nAPI';
import { generateUUID } from '../utils/fileUtils';

export const useFileProcessor = () => {
  const { setProgress } = useAppStore();
  const { addFile, updateFile, setSentences } = useFileStore();

  const processFile = useCallback(async (file: File) => {
    const fileId = generateUUID();
    
    // 添加檔案到狀態
    addFile({
      id: fileId,
      name: file.name,
      size: file.size,
      type: file.type,
      uploadedAt: new Date(),
      status: 'uploading',
      blob: file
    });

    try {
      // 階段 1: 上傳到 split_sentences
      setProgress({
        currentStage: 'uploading',
        percentage: 10,
        details: { fileName: file.name },
        isProcessing: true,
        error: null
      });

      const sentences = await splitSentencesAPI.processPDF(file);
      
      updateFile(fileId, { status: 'processing' });

      // 階段 2: 逐句分析
      setProgress({
        currentStage: 'analyzing',
        percentage: 20,
        details: { 
          totalSentences: sentences.length,
          currentSentence: 0
        },
        isProcessing: true
      });

      const processedSentences: ProcessedSentence[] = [];

      for (let i = 0; i < sentences.length; i++) {
        const sentence = sentences[i];
        const progress = 20 + (i / sentences.length) * 70;

        setProgress({
          currentStage: 'analyzing',
          percentage: progress,
          details: {
            totalSentences: sentences.length,
            currentSentence: i + 1,
            processingText: sentence.substring(0, 100) + '...'
          },
          isProcessing: true
        });

        const result = await n8nAPI.checkOdCd(sentence);
        
        processedSentences.push({
          id: generateUUID(),
          content: sentence,
          type: result.defining_type.toUpperCase() as 'OD' | 'CD',
          reason: result.reason,
          fileId
        });

        // 顯示即時分析結果
        setProgress({
          currentStage: 'analyzing',
          percentage: progress,
          details: {
            totalSentences: sentences.length,
            currentSentence: i + 1,
            processingText: sentence.substring(0, 100) + '...',
            lastResult: {
              type: result.defining_type,
              reason: result.reason
            },
            odCount: processedSentences.filter(s => s.type === 'OD').length,
            cdCount: processedSentences.filter(s => s.type === 'CD').length
          },
          isProcessing: true
        });
      }

      // 階段 3: 儲存結果
      setProgress({
        currentStage: 'saving',
        percentage: 95,
        details: { totalProcessed: processedSentences.length },
        isProcessing: true
      });

      setSentences(fileId, processedSentences);
      updateFile(fileId, { 
        status: 'completed',
        processingProgress: 100
      });

      // 完成
      setProgress({
        currentStage: 'completed',
        percentage: 100,
        details: {
          fileName: file.name,
          totalSentences: sentences.length,
          odCount: processedSentences.filter(s => s.type === 'OD').length,
          cdCount: processedSentences.filter(s => s.type === 'CD').length,
          completedAt: new Date()
        },
        isProcessing: false,
        error: null
      });

    } catch (error) {
      updateFile(fileId, { status: 'error' });
      setProgress({
        currentStage: 'error',
        percentage: 0,
        details: null,
        isProcessing: false,
        error: error instanceof Error ? error.message : '處理檔案時發生未知錯誤'
      });
      throw error;
    }
  }, [setProgress, addFile, updateFile, setSentences]);

  return { processFile };
};
```

### 5.2 查詢處理 Hook
```typescript
// hooks/useQueryProcessor.ts
import { useCallback } from 'react';
import { useAppStore } from '../stores/appStore';
import { useFileStore } from '../stores/fileStore';
import { useChatStore } from '../stores/chatStore';
import { n8nAPI } from '../services/n8nAPI';

export const useQueryProcessor = () => {
  const { setProgress } = useAppStore();
  const { sentences } = useFileStore();
  const { addMessage, setCurrentConversation } = useChatStore();

  const processQuery = useCallback(async (query: string) => {
    // 檢查是否有可用的句子數據
    const allSentences = Object.values(sentences).flat();
    if (allSentences.length === 0) {
      throw new Error('請先上傳並處理文件後再進行查詢');
    }

    try {
      // 添加用戶消息
      const userMessage: Message = {
        id: generateUUID(),
        type: 'user',
        content: query,
        timestamp: new Date()
      };
      addMessage(userMessage);

      // 階段 1: 關鍵詞提取
      setProgress({
        currentStage: 'extracting',
        percentage: 10,
        details: { query },
        isProcessing: true,
        error: null
      });

      const keywordResult = await n8nAPI.extractKeywords(query);
      const keywords = keywordResult[0].output.keywords;

      setProgress({
        currentStage: 'extracting',
        percentage: 30,
        details: {
          query,
          extractedKeywords: keywords
        },
        isProcessing: true
      });

      // 階段 2: 搜尋相關句子
      setProgress({
        currentStage: 'searching',
        percentage: 40,
        details: {
          keywords,
          totalSentences: allSentences.length,
          searching: true
        },
        isProcessing: true
      });

      const relevantSentences = searchLocalSentences(keywords, allSentences);
      const odSentences = relevantSentences.filter(s => s.type === 'OD');
      const cdSentences = relevantSentences.filter(s => s.type === 'CD');

      setProgress({
        currentStage: 'searching',
        percentage: 60,
        details: {
          keywords,
          foundSentences: relevantSentences.length,
          odCount: odSentences.length,
          cdCount: cdSentences.length,
          relevantSentences: relevantSentences.slice(0, 5) // 顯示前 5 個結果
        },
        isProcessing: true
      });

      // 階段 3: 生成回答
      setProgress({
        currentStage: 'generating',
        percentage: 70,
        details: {
          preparingResponse: true,
          inputSentences: relevantSentences.length
        },
        isProcessing: true
      });

      const organizeData = {
        "operational definition": odSentences.map(s => s.content),
        "conceptual definition": cdSentences.map(s => s.content),
        "query": query
      };

      const response = await n8nAPI.organizeResponse(organizeData);

      // 階段 4: 顯示結果
      const systemMessage: Message = {
        id: generateUUID(),
        type: 'system',
        content: response[0].output.response,
        timestamp: new Date(),
        references: relevantSentences,
        metadata: {
          query,
          keywords,
          processingTime: Date.now() - userMessage.timestamp.getTime(),
          totalReferences: relevantSentences.length
        }
      };

      addMessage(systemMessage);

      setProgress({
        currentStage: 'completed',
        percentage: 100,
        details: {
          query,
          responseGenerated: true,
          referencesCount: relevantSentences.length,
          completedAt: new Date()
        },
        isProcessing: false,
        error: null
      });

    } catch (error) {
      setProgress({
        currentStage: 'error',
        percentage: 0,
        details: null,
        isProcessing: false,
        error: error instanceof Error ? error.message : '處理查詢時發生未知錯誤'
      });
      throw error;
    }
  }, [sentences, addMessage, setProgress]);

  const searchLocalSentences = useCallback((
    keywords: string[],
    allSentences: ProcessedSentence[]
  ): ProcessedSentence[] => {
    return allSentences.filter(sentence =>
      keywords.some(keyword =>
        sentence.content.toLowerCase().includes(keyword.toLowerCase())
      )
    );
  }, []);

  return { processQuery };
};
```

這個架構設計提供了：

1. **完整的類型安全**：TypeScript 類型定義覆蓋所有 API 和狀態
2. **模組化的狀態管理**：Zustand 實現輕量級狀態管理
3. **可重用的業務邏輯**：Custom Hooks 封裝核心功能
4. **錯誤處理機制**：統一的錯誤處理和進度追蹤
5. **API 抽象層**：清晰的 API 服務層設計
6. **即時進度更新**：詳細的處理階段和進度顯示

這樣的架構可以確保系統的可維護性、可測試性和用戶體驗的一致性。
