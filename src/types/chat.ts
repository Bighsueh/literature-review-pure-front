// types/chat.ts

// 新增引用來源資訊類型
export interface Reference {
  id: string;
  paper_name?: string;  // 來自 unified API
  file_name?: string;   // 來自 enhanced API
  section_type?: string;
  section?: string;     // 來自 enhanced API
  page_num: number;
  content_snippet?: string;
  sentence?: string;    // 來自 enhanced API
  type?: string;        // 來自 enhanced API (OD/CD)
}

// 新增來源摘要類型
export interface SourceSummary {
  total_papers: number;
  papers_used: string[];
  sections_analyzed?: string[];
  analysis_type?: string;
}

export interface Message {
  id: string;
  type: 'user' | 'system';
  content: string;
  timestamp: Date;
  references?: Reference[];          // 更新為新的引用格式
  source_summary?: SourceSummary;    // 新增來源摘要
  metadata?: MessageMetadata;
}

export interface MessageMetadata {
  query?: string;
  keywords?: string[];
  processingTime?: number;
  totalReferences?: number;
  relevantSentencesCount?: number;
  stages?: Record<string, unknown>;  // 修復 any 類型
  error?: boolean | string;
  loading?: boolean;                 // 新增載入狀態
  analysis_focus?: string;           // 新增分析重點
}

export interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
}

// 新增查詢處理狀態
export interface QueryProcessingState {
  isLoading: boolean;
  currentStage?: string;
  progress?: number;
  error?: string | null;
}
