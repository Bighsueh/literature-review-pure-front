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
  skipped?: boolean; // 標記是否因錯誤而被跳過
  fileName?: string; // 檔案名稱
}

export interface TextPosition {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface FileMetadata {
  id: string;
  name: string;
  size: number;
  type: string;
  uploadedAt: Date;
}
