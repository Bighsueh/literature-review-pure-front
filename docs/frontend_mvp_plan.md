# 純前端 React MVP 專案計劃

## 1. 技術棧架構

### 1.1 核心技術
```typescript
// 技術棧配置
const techStack = {
  // 核心框架
  framework: "React 18+",
  language: "TypeScript 5.0+",
  bundler: "Vite 4+",
  routing: "React Router 6+",
  
  // 狀態管理
  globalState: "Zustand", // 輕量級替代 Redux
  serverState: "TanStack Query",
  formState: "React Hook Form",
  localStorage: "LocalStorage + IndexedDB",
  
  // UI & 樣式
  styling: "TailwindCSS 3+",
  components: "Headless UI",
  icons: "Heroicons",
  pdfRenderer: "PDF.js",
  
  // 網絡通信
  httpClient: "Axios",
  externalAPIs: ["split_sentences", "n8n APIs"],
  progressTracking: "自定義 Promise chains"
}
```

### 1.2 外部 API 整合
```typescript
// API 端點配置
const apiConfig = {
  splitSentences: {
    baseUrl: "http://localhost:8000", // Docker 服務
    endpoint: "/split",
    method: "POST",
    contentType: "multipart/form-data"
  },
  n8n: {
    baseUrl: "https://n8n.hsueh.tw",
    endpoints: {
      checkOdCd: "/webhook/5fd2cefe-147a-490d-ada9-8849234c1580",
      keywordExtraction: "/webhook/421337df-0d97-47b4-a96b-a70a6c35d416", 
      organizeResponse: "/webhook/1394997a-36ab-46eb-9247-8b987eca91fc"
    }
  }
}
```

## 2. 關鍵組件設計

### 2.1 主要組件架構
```
App
├── MainLayout
│   ├── LeftPanel
│   │   ├── FileUploadZone
│   │   └── FileList
│   ├── CenterPanel  
│   │   ├── ChatMessageList
│   │   └── ChatInput
│   └── RightPanel
│       ├── ProgressDisplay
│       └── ReferencesPanel
└── PDFPreviewModal
```

### 2.2 狀態管理設計

#### Zustand Store 結構
```typescript
interface AppState {
  // 檔案管理
  files: FileData[];
  currentFile: FileData | null;
  
  // 對話管理  
  conversations: Conversation[];
  currentConversation: string | null;
  
  // 進度管理
  processingState: {
    stage: ProcessingStage;
    progress: number;
    details: any;
    isProcessing: boolean;
  };
  
  // UI 狀態
  ui: {
    isPDFModalOpen: boolean;
    selectedSentence: string | null;
    highlightedText: string | null;
  };
}
```

#### LocalStorage 數據結構
```typescript
interface LocalStorageData {
  // 處理後的句子數據
  sentences: {
    [fileId: string]: ProcessedSentence[];
  };
  
  // 對話歷史
  conversations: {
    [conversationId: string]: Message[];
  };
  
  // 檔案元數據
  fileMetadata: {
    [fileId: string]: FileMetadata;
  };
}

interface ProcessedSentence {
  id: string;
  content: string;
  type: 'OD' | 'CD' | 'OTHER';
  reason: string;
  fileId: string;
  pageNumber?: number;
  position?: { x: number; y: number };
}
```

## 3. 核心流程實現

### 3.1 檔案處理流程
```typescript
class FileProcessor {
  async processFile(file: File): Promise<void> {
    const fileId = generateUUID();
    
    // 階段 1：上傳檔案到 split_sentences
    this.updateProgress("uploading", 10, "正在上傳檔案...");
    const sentences = await this.splitSentencesAPI.process(file);
    
    // 階段 2：逐句分析 OD/CD
    this.updateProgress("analyzing", 20, "開始分析句子類型...");
    const processedSentences: ProcessedSentence[] = [];
    
    for (let i = 0; i < sentences.length; i++) {
      const sentence = sentences[i];
      const progress = 20 + (i / sentences.length) * 70;
      
      this.updateProgress("analyzing", progress, `分析第 ${i+1}/${sentences.length} 個句子`);
      
      const result = await this.n8nAPI.checkOdCd(sentence);
      processedSentences.push({
        id: generateUUID(),
        content: sentence,
        type: result.defining_type.toUpperCase() as 'OD' | 'CD',
        reason: result.reason,
        fileId
      });
      
      // 顯示即時結果
      this.updateProgress("analyzing", progress, {
        currentSentence: sentence,
        result: result.defining_type,
        processed: i + 1,
        total: sentences.length
      });
    }
    
    // 階段 3：儲存到 LocalStorage
    this.updateProgress("saving", 95, "儲存處理結果...");
    this.saveToLocalStorage(fileId, processedSentences);
    
    this.updateProgress("completed", 100, "檔案處理完成！");
  }
}
```

### 3.2 查詢處理流程
```typescript
class QueryProcessor {
  async processQuery(query: string): Promise<void> {
    // 階段 1：關鍵詞提取
    this.updateProgress("extracting", 10, "提取查詢關鍵詞...");
    const keywordResult = await this.n8nAPI.extractKeywords(query);
    const keywords = keywordResult[0].output.keywords;
    
    this.updateProgress("extracting", 30, {
      stage: "關鍵詞提取完成",
      keywords: keywords
    });
    
    // 階段 2：本地搜尋相關句子
    this.updateProgress("searching", 40, "搜尋相關定義句子...");
    const relevantSentences = this.searchLocalSentences(keywords);
    
    this.updateProgress("searching", 60, {
      stage: "找到相關句子",
      odSentences: relevantSentences.filter(s => s.type === 'OD'),
      cdSentences: relevantSentences.filter(s => s.type === 'CD'),
      total: relevantSentences.length
    });
    
    // 階段 3：生成回答
    this.updateProgress("generating", 70, "生成智能回答...");
    const response = await this.n8nAPI.organizeResponse({
      "operational definition": relevantSentences.filter(s => s.type === 'OD').map(s => s.content),
      "conceptual definition": relevantSentences.filter(s => s.type === 'CD').map(s => s.content),
      "query": query
    });
    
    // 階段 4：顯示結果
    this.updateProgress("completed", 100, {
      response: response[0].output.response,
      references: relevantSentences
    });
  }
  
  private searchLocalSentences(keywords: string[]): ProcessedSentence[] {
    const allSentences = this.getStoredSentences();
    return allSentences.filter(sentence => 
      keywords.some(keyword => 
        sentence.content.toLowerCase().includes(keyword.toLowerCase())
      )
    );
  }
}
```

## 4. 進度顯示系統

### 4.1 進度組件設計
```typescript
interface ProgressDisplayProps {
  stage: ProcessingStage;
  progress: number;
  details: any;
}

const ProgressDisplay: React.FC<ProgressDisplayProps> = ({ stage, progress, details }) => {
  return (
    <div className="progress-container">
      {/* 進度條 */}
      <div className="progress-bar">
        <div className="progress-fill" style={{ width: `${progress}%` }} />
      </div>
      
      {/* 階段說明 */}
      <div className="stage-info">
        <h3>{getStageTitle(stage)}</h3>
        <p>{getStageDescription(stage)}</p>
      </div>
      
      {/* 即時詳情 */}
      {details && (
        <div className="details-panel">
          {renderDetailsContent(stage, details)}
        </div>
      )}
    </div>
  );
};
```

### 4.2 進度階段定義
```typescript
type ProcessingStage = 
  | "uploading"      // 上傳檔案
  | "analyzing"      // 分析句子類型
  | "saving"         // 儲存結果
  | "extracting"     // 提取關鍵詞
  | "searching"      // 搜尋相關句子  
  | "generating"     // 生成回答
  | "completed"      // 完成
  | "error";         // 錯誤

const stageConfig = {
  uploading: {
    title: "上傳檔案",
    description: "正在將檔案發送到 split_sentences 服務...",
    color: "blue"
  },
  analyzing: {
    title: "分析句子類型", 
    description: "使用 n8n API 逐句分析 OD/CD 類型...",
    color: "purple"
  },
  // ... 其他階段
};
```

## 5. PDF 預覽與互動功能

### 5.1 PDF 預覽組件
```typescript
const PDFPreviewModal: React.FC<PDFPreviewProps> = ({ 
  isOpen, 
  file, 
  highlightText,
  onClose 
}) => {
  const [pdfDocument, setPdfDocument] = useState<PDFDocumentProxy | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  
  // PDF.js 初始化
  useEffect(() => {
    if (file && isOpen) {
      loadPDF(file).then(setPdfDocument);
    }
  }, [file, isOpen]);
  
  // 高亮顯示功能
  const highlightSentence = useCallback((text: string) => {
    // 使用 PDF.js 文本搜尋 API
    // 高亮顯示匹配的文本
  }, [pdfDocument]);
  
  return (
    <Modal isOpen={isOpen} onClose={onClose}>
      <div className="pdf-viewer">
        <PDFViewer 
          document={pdfDocument}
          page={currentPage}
          highlightText={highlightText}
        />
        <PDFControls 
          currentPage={currentPage}
          totalPages={pdfDocument?.numPages || 0}
          onPageChange={setCurrentPage}
        />
      </div>
    </Modal>
  );
};
```

### 5.2 句子引用與跳轉
```typescript
const ReferencesPanel: React.FC = () => {
  const { selectedReferences } = useAppStore();
  
  const handleViewInPDF = (sentence: ProcessedSentence) => {
    // 打開 PDF 預覽
    openPDFModal({
      fileId: sentence.fileId,
      highlightText: sentence.content,
      pageNumber: sentence.pageNumber
    });
  };
  
  return (
    <div className="references-panel">
      <h3>引用原文</h3>
      {selectedReferences.map(ref => (
        <div key={ref.id} className="reference-item">
          <div className="sentence-content">{ref.content}</div>
          <div className="sentence-meta">
            <span className={`type-badge ${ref.type.toLowerCase()}`}>
              {ref.type}
            </span>
            <button onClick={() => handleViewInPDF(ref)}>
              在 PDF 中查看
            </button>
          </div>
        </div>
      ))}
    </div>
  );
};
```

## 6. 模擬數據與測試

### 6.1 開發模式數據
```typescript
// 開發環境模擬數據
const mockData = {
  sampleSentences: [
    {
      content: "Learning is the acquisition of knowledge or skills through experience, study, or instruction.",
      type: "CD",
      reason: "This defines the concept of learning conceptually."
    },
    {
      content: "Learning effectiveness was measured by pre-test and post-test score improvements.",
      type: "OD", 
      reason: "This provides an operational way to measure learning."
    }
  ],
  
  sampleKeywords: ["learning", "education", "knowledge acquisition"],
  
  sampleResponse: "根據提供的定義，學習可以從概念性和操作性兩個角度來理解..."
};
```

### 6.2 錯誤處理策略
```typescript
const errorHandler = {
  apiTimeout: (apiName: string) => {
    showNotification(`${apiName} API 請求超時，請檢查網絡連接`, "error");
  },
  
  fileProcessingError: (error: Error) => {
    updateProgress("error", 0, `檔案處理失敗：${error.message}`);
  },
  
  networkError: () => {
    showNotification("網絡連接異常，請稍後重試", "error");
  }
};
```

## 7. 部署配置

### 7.1 Docker 配置
```dockerfile
# Dockerfile
FROM node:18-alpine as builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### 7.2 環境變量配置
```typescript
// .env 配置
const envConfig = {
  VITE_SPLIT_SENTENCES_API: "http://localhost:8000",
  VITE_N8N_BASE_URL: "https://n8n.hsueh.tw",
  VITE_APP_NAME: "文件分析 MVP",
  VITE_DEBUG_MODE: "true"
};
```

## 8. 開發時程規劃

### Phase 1 (Week 1): 基礎架構
- [ ] Vite + React + TypeScript 專案設置
- [ ] Zustand 狀態管理配置
- [ ] 基本 UI 佈局實現
- [ ] API 服務層封裝

### Phase 2 (Week 2): 核心功能
- [ ] 檔案上傳與處理流程
- [ ] split_sentences API 整合
- [ ] n8n API 整合 
- [ ] 本地數據儲存

### Phase 3 (Week 3): 進階功能
- [ ] PDF 預覽功能
- [ ] 句子高亮與跳轉
- [ ] 進度顯示系統
- [ ] 錯誤處理機制

### Phase 4 (Week 4): 完善與部署
- [ ] UI/UX 優化
- [ ] 效能優化
- [ ] 測試與除錯
- [ ] Docker 部署配置

這個 MVP 將完整保留原系統的所有用戶體驗流程，同時透過前端技術實現所有核心功能。
