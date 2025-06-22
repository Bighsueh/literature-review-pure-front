// types/api.ts
export interface SentenceWithPage {
  sentence: string;
  page: number;
  fileName?: string; // 添加檔案名稱屬性
}

export interface SplitSentencesResponse {
  sentences: string[] | SentenceWithPage[];
  success?: boolean;
  data?: {
    sentences: string[] | SentenceWithPage[];
  };
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
  details?: Record<string, unknown>;
}

export type ProcessingStage = 
  | "idle"
  | "uploading"      // 上傳檔案
  | "analyzing"      // 分析句子類型
  | "saving"         // 儲存結果
  | "extracting"     // 提取關鍵詞
  | "searching"      // 搜尋相關句子  
  | "generating"     // 生成回答
  | "completed"      // 完成
  | "error";         // 錯誤

// ===== 基礎類型定義 =====

export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginationMeta {
  page: number;
  size: number;
  total: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface PaginatedResponse<T> {
  items: T[];
  meta: PaginationMeta;
}

export interface ApiError {
  type: string;
  title: string;
  status: number;
  detail: string;
  instance?: string;
  errors?: Record<string, string[]>;
}

// ===== 認證相關類型 =====

export interface User {
  id: string;
  google_id: string;
  email: string;
  name: string;
  picture_url?: string;
  created_at: string;
  updated_at: string;
}

export interface AuthTokens {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface AuthResponse {
  user: User;
  tokens: AuthTokens;
}

// ===== 工作區相關類型 =====

export interface Workspace {
  id: string;
  user_id: string;
  name: string;
  created_at: string;
  updated_at: string;
}

export interface WorkspaceCreate {
  name: string;
}

export interface WorkspaceUpdate {
  name?: string;
}

export interface UserWithWorkspaces extends User {
  workspaces: Workspace[];
}

// ===== 論文/檔案相關類型 =====

export type ProcessingStatus = 'uploading' | 'pending' | 'processing' | 'completed' | 'error';

export interface Paper {
  id: string;
  file_name: string;
  original_filename?: string;
  upload_timestamp: string;
  processing_status: ProcessingStatus;
  file_size?: number;
  file_hash?: string;
  grobid_processed: boolean;
  sentences_processed: boolean;
  od_cd_processed: boolean;
  pdf_deleted: boolean;
  error_message?: string;
  processing_completed_at?: string;
  created_at: string;
  is_selected?: boolean;
}

export interface PaperCreate {
  file_name: string;
  original_filename?: string;
  file_size?: number;
  file_hash: string;
}

export interface PaperUpdate {
  processing_status?: ProcessingStatus;
  grobid_processed?: boolean;
  sentences_processed?: boolean;
  od_cd_processed?: boolean;
  pdf_deleted?: boolean;
  error_message?: string;
  tei_xml?: string;
  tei_metadata?: Record<string, any>;
  processing_completed_at?: string;
}

// ===== 章節相關類型 =====

export interface PaperSection {
  id: string;
  paper_id: string;
  section_type: string;
  page_num?: number;
  content: string;
  section_order?: number;
  word_count?: number;
  tei_coordinates?: Record<string, any>;
  created_at: string;
}

export interface SectionCreate {
  section_type: string;
  page_num?: number;
  content: string;
  section_order?: number;
  word_count?: number;
  tei_coordinates?: Record<string, any>;
}

// ===== 句子相關類型 =====

export type DetectionStatus = 'unknown' | 'detected' | 'not_detected' | 'error';

export interface Sentence {
  id: string;
  paper_id: string;
  section_id: string;
  content: string;
  sentence_order?: number;
  word_count?: number;
  char_count?: number;
  has_objective?: boolean;
  has_dataset?: boolean;
  has_contribution?: boolean;
  detection_status: DetectionStatus;
  error_message?: string;
  retry_count: number;
  explanation?: string;
  created_at: string;
  updated_at: string;
}

export interface SentenceCreate {
  paper_id: string;
  section_id: string;
  content: string;
  sentence_order?: number;
  word_count?: number;
  char_count?: number;
}

// ===== 論文選擇相關類型 =====

export interface PaperSelection {
  id: string;
  paper_id: string;
  is_selected: boolean;
  selected_timestamp: string;
}

export interface PaperSelectionUpdate {
  is_selected: boolean;
}

// ===== 處理佇列相關類型 =====

export interface ProcessingQueue {
  id: string;
  paper_id: string;
  processing_stage: string;
  status: string;
  priority: number;
  retry_count: number;
  max_retries: number;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  error_message?: string;
  processing_details?: Record<string, any>;
}

export interface ProcessingQueueCreate {
  paper_id: string;
  processing_stage: string;
  priority?: number;
}

export interface ProcessingQueueUpdate {
  status?: string;
  retry_count?: number;
  started_at?: string;
  completed_at?: string;
  error_message?: string;
  processing_details?: Record<string, any>;
}

// ===== 對話相關類型 =====

export interface ChatHistory {
  id: string;
  workspace_id: string;
  user_question: string;
  ai_response: string;
  context_papers?: string[];
  context_sentences?: string[];
  query_metadata?: Record<string, any>;
  created_at: string;
}

export interface ChatHistoryCreate {
  workspace_id: string;
  user_question: string;
  ai_response: string;
  context_papers?: string[];
  context_sentences?: string[];
  query_metadata?: Record<string, any>;
}

export interface ChatContextInfo {
  paper_titles: string[];
  sentence_count: number;
  source_papers: Array<Record<string, any>>;
}

export interface ChatWithContext extends ChatHistory {
  context_info?: ChatContextInfo;
}

// ===== 查詢相關類型 =====

export interface QueryRequest {
  query: string;
  query_type?: string;
  selected_paper_ids?: string[];
  options?: Record<string, any>;
}

export interface QueryResult {
  response: string;
  references?: Array<Record<string, any>>;
  selected_sections?: Array<Record<string, any>>;
  analysis_focus?: string;
  source_summary?: Record<string, any>;
}

// ===== 複合類型 =====

export interface PaperWithSections extends Paper {
  sections: PaperSection[];
}

export interface SectionSummary {
  section_type: string;
  page_num?: number;
  word_count?: number;
  brief_content: string;
  od_count: number;
  cd_count: number;
  total_sentences: number;
}

export interface PaperSectionSummary {
  file_name: string;
  sections: SectionSummary[];
}

// ===== 上傳相關類型 =====

export interface UploadResponse {
  paper_id: string;
  task_id?: string;
  message: string;
  duplicate?: boolean;
  filename?: string;
  original_filename?: string;
  file_size?: number;
  file_hash?: string;
}

// ===== 任務狀態相關類型 =====

export interface TaskProgress {
  current_step: number;
  total_steps: number;
  step_name: string;
  percentage: number;
  details: Record<string, unknown>;
}

export interface TaskStatus {
  task_id: string;
  task_type: string;
  status: string;
  priority: string;
  progress: TaskProgress;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  error_message?: string;
  retry_count: number;
  file_id?: string;
  result?: Record<string, unknown>;
}

// ===== 系統健康檢查類型 =====

export interface HealthCheckResponse {
  status: string;
  services: Record<string, boolean>;
}

export interface ServiceStatus {
  grobid: boolean;
  n8n: boolean;
  split_sentences: boolean;
  database: boolean;
}

// ===== 處理進度相關類型 =====

export interface ProcessingProgress {
  current_stage: string;
  percentage: number;
  details: Record<string, unknown>;
  is_processing: boolean;
  error: string | null;
}

export interface PaperProcessingStatus {
  paper_id: string;
  status: string;
  progress?: number;
  current_stage?: string;
  error_message?: string;
  can_retry?: boolean;
}

// ===== WebSocket 相關類型 =====

export interface WebSocketMessage {
  type: string;
  data: any;
  timestamp: string;
}

export interface ProcessingWebSocketData {
  paper_id: string;
  status: ProcessingStatus;
  progress: TaskProgress;
  message?: string;
  error?: string;
}

// ===== 向後相容性類型 (待移除) =====

/** @deprecated 使用 Paper 替代 */
export interface LegacyPaperInfo extends Paper {}

/** @deprecated 使用 WorkspaceFile 替代 */
export interface WorkspaceFile extends Paper {
  workspace_id: string;
  title: string;
  file_path: string;
  selected: boolean;
  section_count: number;
  sentence_count: number;
}
