// utils/fileUtils.ts
import { v4 as uuidv4 } from 'uuid';
import { FileData } from '../types/file';

/**
 * 生成唯一 ID
 */
export const generateUUID = (): string => {
  return uuidv4();
};

/**
 * 格式化檔案大小
 */
export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

/**
 * 從 File 物件創建 FileData
 */
export const createFileData = (file: File): FileData => {
  return {
    id: generateUUID(),
    name: file.name,
    size: file.size,
    type: file.type,
    uploadedAt: new Date(),
    status: 'uploading',
    processingProgress: 0,
    blob: file
  };
};

/**
 * 檢查檔案類型是否為 PDF
 */
export const isPdfFile = (file: File): boolean => {
  return file.type === 'application/pdf';
};

/**
 * 檢查檔案大小是否在允許範圍內
 */
export const isFileSizeValid = (file: File, maxSizeMB: number = 10): boolean => {
  return file.size <= maxSizeMB * 1024 * 1024;
};
