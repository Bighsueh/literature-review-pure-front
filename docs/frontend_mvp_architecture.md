# 純前端 MVP 技術架構設計

## 2.1 技術棧調整

### 核心框架保持不變
- **語言**: TypeScript 5.0+
- **框架**: React 18+
- **建構工具**: Vite 4+
- **路由**: React Router 6+

### 狀態管理簡化
- **全局狀態**: Zustand（替代 Redux Toolkit，更輕量）
- **伺服器狀態**: TanStack Query (React Query) 4+
- **表單狀態**: React Hook Form 7+
- **本地數據**: LocalStorage + IndexedDB

### UI 與樣式保持
- **樣式庫**: TailwindCSS 3+
- **組件庫**: Headless UI
- **圖標**: Heroicons
- **PDF 渲染**: PDF.js

### 網絡通信調整
- **HTTP 客戶端**: Axios
- **外部 API**: split_sentences + n8n APIs
- **檔案處理**: File API + Blob handling
- **進度管理**: 自定義 Promise chains 替代 WebSocket

## 2.2 外部 API 整合

### split_sentences API
```typescript
// 文檔處理 API
interface SplitSentencesAPI {
  endpoint: string; // Docker 環境中的服務地址
  processFile: (file: File) => Promise<string[]>;
}
```

### n8n Webhook APIs
```typescript
// n8n API 配置
interface N8nAPIs {
  baseUrl: 'https://n8n.hsueh.tw';
  checkOdCd: '/webhook/5fd2cefe-147a-490d-ada9-8849234c1580';
  keywordExtraction: '/webhook/keyword-extraction';
  organizeResponse: '/webhook/1394997a-36ab-46eb-9247-8b987eca91fc';
}
```

## 2.3 數據流架構

```
User Action → Frontend State → API Calls → Local Storage → UI Update
     ↑                                                           ↓
     └──────────── Progress Simulation ←←←←←←←←←←←←←←←←←←←←←←←←←←←←
```

### 數據管理策略
1. **檔案管理**: 使用 IndexedDB 儲存檔案內容和處理結果
2. **對話歷史**: LocalStorage 儲存聊天記錄
3. **進度狀態**: Zustand 管理即時進度
4. **快取機制**: React Query 管理 API 快取

## 2.4 關鍵組件架構

### FileProcessingManager
```typescript
interface FileProcessingManager {
  uploadFile: (file: File) => Promise<void>;
  processSentences: (sentences: string[]) => Promise<ProcessedSentence[]>;
  updateProgress: (stage: ProcessingStage, progress: number) => void;
}
```

### QueryProcessor
```typescript
interface QueryProcessor {
  extractKeywords: (query: string) => Promise<string[]>;
  searchSentences: (keywords: string[], sentences: ProcessedSentence[]) => ProcessedSentence[];
  generateResponse: (context: ProcessedSentence[], query: string) => Promise<string>;
}
```

### ProgressSimulator
```typescript
interface ProgressSimulator {
  simulateFileProcessing: (totalSentences: number) => Promise<void>;
  simulateQueryProcessing: (steps: ProcessingStep[]) => Promise<void>;
  updateUI: (stage: string, progress: number, details?: any) => void;
}
```
