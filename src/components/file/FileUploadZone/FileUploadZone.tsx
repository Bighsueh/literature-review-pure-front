import React, { useCallback, useState } from 'react';
import { 
  ArrowUpTrayIcon, 
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon
} from '@heroicons/react/24/outline';
import { useAppStore } from '../../../stores/app_store';
import ProgressBar from '../../common/ProgressBar/ProgressBar';

interface FileUploadZoneProps {
  onUploadStart?: () => void;
  onUploadComplete?: () => void;
  onUploadError?: (error: Error) => void;
}

interface UploadState {
  isUploading: boolean;
  isDragOver: boolean;
  currentFile: File | null;
  error: string | null;
  isDuplicate: boolean;
  duplicateFiles: string[];
}

const FileUploadZone: React.FC<FileUploadZoneProps> = ({
  onUploadStart,
  onUploadComplete,
  onUploadError
}) => {
  const [uploadState, setUploadState] = useState<UploadState>({
    isUploading: false,
    isDragOver: false,
    currentFile: null,
    error: null,
    isDuplicate: false,
    duplicateFiles: []
  });

  const { progress, papers, uploadPaper, resetProgress } = useAppStore();

  const resetUploadState = useCallback(() => {
    setUploadState({
      isUploading: false,
      isDragOver: false,
      currentFile: null,
      error: null,
      isDuplicate: false,
      duplicateFiles: []
    });
    resetProgress();
  }, [resetProgress]);

  const checkDuplicateFile = useCallback((file: File): { isDuplicate: boolean; duplicateFiles: string[] } => {
    const duplicateFiles = papers.list.filter(paper => 
      paper.title === file.name || 
      paper.title.includes(file.name.replace('.pdf', ''))
    ).map(paper => paper.title);
    
    return {
      isDuplicate: duplicateFiles.length > 0,
      duplicateFiles
    };
  }, [papers.list]);

  const validateFile = useCallback((file: File): { valid: boolean; error?: string } => {
    // 檢查檔案類型
    if (file.type !== 'application/pdf') {
      return { valid: false, error: '只接受 PDF 檔案格式' };
    }

    // 檢查檔案大小 (限制 50MB)
    const maxSize = 50 * 1024 * 1024; // 50MB
    if (file.size > maxSize) {
      return { valid: false, error: '檔案大小不能超過 50MB' };
    }

    // 檢查檔案名稱
    if (file.name.length > 255) {
      return { valid: false, error: '檔案名稱過長' };
    }

    return { valid: true };
  }, []);
  
  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    if (!uploadState.isUploading) {
      setUploadState(prev => ({ ...prev, isDragOver: true }));
    }
  }, [uploadState.isUploading]);
  
  const handleDragLeave = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setUploadState(prev => ({ ...prev, isDragOver: false }));
  }, []);
  
  const handleDrop = useCallback(async (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setUploadState(prev => ({ ...prev, isDragOver: false }));
    
    if (uploadState.isUploading) return;
    
    const files = Array.from(e.dataTransfer.files);
    if (files.length === 0) return;
    
    // 只處理第一個檔案
    const file = files[0];
    await processFileUpload(file);
  }, [uploadState.isUploading]);
  
  const handleFileChange = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    
    const file = files[0];
    await processFileUpload(file);
    
    // 重置 input 值
    e.target.value = '';
  }, []);

  const processFileUpload = useCallback(async (file: File) => {
    // 驗證檔案
    const validation = validateFile(file);
    if (!validation.valid) {
      setUploadState(prev => ({ 
        ...prev, 
        error: validation.error || '檔案驗證失敗',
        currentFile: file
      }));
      return;
    }

    // 檢查重複檔案
    const duplicateCheck = checkDuplicateFile(file);
    
    setUploadState(prev => ({ 
      ...prev, 
      currentFile: file,
      isDuplicate: duplicateCheck.isDuplicate,
      duplicateFiles: duplicateCheck.duplicateFiles,
      error: null
    }));

    // 如果是重複檔案，顯示警告但不阻止上傳
    if (duplicateCheck.isDuplicate) {
      // 讓用戶決定是否繼續
      return;
    }

    // 開始上傳
    await startFileUpload(file);
  }, [validateFile, checkDuplicateFile]);

  const startFileUpload = useCallback(async (file: File) => {
    setUploadState(prev => ({ 
      ...prev, 
      isUploading: true,
      error: null
    }));

    try {
      onUploadStart?.();
      
      const result = await uploadPaper(file);
      
      if (result.success) {
        setUploadState(prev => ({ 
          ...prev, 
          isUploading: false
        }));
        onUploadComplete?.();
        
        // 延遲重置狀態以顯示成功訊息
        setTimeout(() => {
          resetUploadState();
        }, 2000);
      } else {
        throw new Error(result.error || '上傳失敗');
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '上傳過程中發生錯誤';
      setUploadState(prev => ({ 
        ...prev, 
        isUploading: false,
        error: errorMessage
      }));
             onUploadError?.(error instanceof Error ? error : new Error(String(error)));
    }
  }, [uploadPaper, onUploadStart, onUploadComplete, onUploadError, resetUploadState]);

  const handleRetry = useCallback(() => {
    if (uploadState.currentFile) {
      startFileUpload(uploadState.currentFile);
    }
  }, [uploadState.currentFile, startFileUpload]);

  const handleConfirmDuplicate = useCallback(() => {
    if (uploadState.currentFile) {
      startFileUpload(uploadState.currentFile);
    }
  }, [uploadState.currentFile, startFileUpload]);

  const getDragOverStyle = () => {
    if (uploadState.isDragOver && !uploadState.isUploading) {
      return 'border-blue-500 bg-blue-50 scale-102';
    }
    if (uploadState.isUploading) {
      return 'border-green-500 bg-green-50';
    }
    if (uploadState.error) {
      return 'border-red-500 bg-red-50';
    }
    if (progress.currentStage === 'completed') {
      return 'border-green-500 bg-green-50';
    }
    return 'border-gray-300 hover:border-gray-400';
  };

  const renderContent = () => {
    // 顯示進度
    if (uploadState.isUploading || progress.isProcessing) {
      return (
        <div className="w-full">
          <div className="flex flex-col items-center mb-4">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mb-2"></div>
            <h3 className="text-sm font-medium text-gray-900">
              {uploadState.currentFile?.name}
            </h3>
            <p className="text-xs text-gray-500">正在處理中...</p>
          </div>
          
          <ProgressBar 
            progress={progress.percentage}
            stage={progress.currentStage}
            size="md"
            showLabel={true}
          />
          
          {typeof progress.details === 'object' && progress.details && 'message' in progress.details && typeof progress.details.message === 'string' && (
            <p className="mt-2 text-xs text-gray-600 text-center">
              {progress.details.message}
            </p>
          )}
        </div>
      );
    }

    // 顯示錯誤
    if (uploadState.error) {
      return (
        <div className="flex flex-col items-center justify-center h-full text-center">
          <XCircleIcon className="w-12 h-12 text-red-400 mb-4" />
          <h3 className="text-sm font-medium text-gray-900 mb-2">上傳失敗</h3>
          <p className="text-xs text-red-600 mb-4 max-w-xs">{uploadState.error}</p>
          <div className="flex gap-2">
            <button
              onClick={handleRetry}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
            >
              重試
            </button>
            <button
              onClick={resetUploadState}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-200 rounded-md hover:bg-gray-300"
            >
              取消
            </button>
          </div>
        </div>
      );
    }
    
    // 顯示重複檔案警告
    if (uploadState.isDuplicate) {
      return (
        <div className="flex flex-col items-center justify-center h-full text-center">
          <ExclamationTriangleIcon className="w-12 h-12 text-yellow-400 mb-4" />
          <h3 className="text-sm font-medium text-gray-900 mb-2">檔案可能已存在</h3>
          <p className="text-xs text-gray-500 mb-4 max-w-xs">
            系統中已存在名為 "{uploadState.duplicateFiles.join(', ')}" 的相似檔案。
          </p>
          <div className="flex gap-2">
            <button
              onClick={handleConfirmDuplicate}
              className="px-4 py-2 text-sm font-medium text-white bg-yellow-500 rounded-md hover:bg-yellow-600"
            >
              繼續上傳
            </button>
            <button
              onClick={resetUploadState}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-200 rounded-md hover:bg-gray-300"
            >
              取消
            </button>
          </div>
        </div>
      );
    }

    // 上傳成功
    if (progress.currentStage === 'completed' && !uploadState.isUploading) {
      return (
        <div className="flex flex-col items-center justify-center h-full text-center">
          <CheckCircleIcon className="w-12 h-12 text-green-400 mb-4" />
          <h3 className="text-sm font-medium text-gray-900">處理成功</h3>
          <p className="text-xs text-gray-500">
            檔案 "{uploadState.currentFile?.name}" 已成功上傳並處理。
          </p>
        </div>
      );
    }

    // 預設狀態
    return (
      <div className="flex flex-col items-center justify-center h-full text-center" id="file-upload-zone">
        <ArrowUpTrayIcon className="w-12 h-12 text-gray-400" />
        <p className="mt-4 text-sm font-medium text-gray-900">
          拖放檔案到這裡
        </p>
        <p className="mt-1 text-xs text-gray-500">
          或點擊上傳 PDF 檔案
        </p>
        <label htmlFor="file-upload" className="mt-4 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 cursor-pointer">
          選擇檔案
        </label>
      </div>
    );
  };

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={`relative border-2 border-dashed rounded-xl p-4 transition-all duration-300 ease-in-out h-64 flex items-center justify-center ${getDragOverStyle()}`}
    >
      <input
        type="file"
        id="file-upload"
        className="hidden"
        onChange={handleFileChange}
        accept="application/pdf"
        disabled={uploadState.isUploading}
      />
      {renderContent()}
    </div>
  );
};

export default FileUploadZone;
