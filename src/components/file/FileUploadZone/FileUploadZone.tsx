import React, { useCallback, useState } from 'react';
import { 
  ArrowUpTrayIcon, 
  ExclamationTriangleIcon,
  CheckCircleIcon,
  XCircleIcon,
  ArrowPathIcon
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

    // 顯示完成狀態
    if (progress.currentStage === 'completed') {
      return (
        <div className="text-center">
          <CheckCircleIcon className="mx-auto h-12 w-12 text-green-500" />
          <h3 className="mt-2 text-sm font-medium text-green-900">上傳成功</h3>
          <p className="mt-1 text-xs text-green-600">
            {uploadState.currentFile?.name} 已成功處理
          </p>
        </div>
      );
    }

    // 顯示錯誤狀態
    if (uploadState.error) {
      return (
        <div className="text-center">
          <XCircleIcon className="mx-auto h-12 w-12 text-red-500" />
          <h3 className="mt-2 text-sm font-medium text-red-900">上傳失敗</h3>
          <p className="mt-1 text-xs text-red-600">{uploadState.error}</p>
          <div className="mt-4 flex justify-center space-x-2">
            <button
              onClick={handleRetry}
              className="inline-flex items-center px-3 py-1 border border-transparent text-xs font-medium rounded-md text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
            >
              <ArrowPathIcon className="w-4 h-4 mr-1" />
              重試
            </button>
            <button
              onClick={resetUploadState}
              className="inline-flex items-center px-3 py-1 border border-gray-300 text-xs font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
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
        <div className="text-center">
          <ExclamationTriangleIcon className="mx-auto h-12 w-12 text-yellow-500" />
          <h3 className="mt-2 text-sm font-medium text-yellow-900">發現重複檔案</h3>
          <p className="mt-1 text-xs text-yellow-600">
            系統中已存在相似的檔案：
          </p>
          <ul className="mt-2 text-xs text-yellow-700">
            {uploadState.duplicateFiles.map((fileName, index) => (
              <li key={index} className="truncate">• {fileName}</li>
            ))}
          </ul>
          <p className="mt-2 text-xs text-yellow-600">
            確定要繼續上傳嗎？
          </p>
          <div className="mt-4 flex justify-center space-x-2">
            <button
              onClick={handleConfirmDuplicate}
              className="inline-flex items-center px-3 py-1 border border-transparent text-xs font-medium rounded-md text-white bg-yellow-600 hover:bg-yellow-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-yellow-500"
            >
              繼續上傳
            </button>
            <button
              onClick={resetUploadState}
              className="inline-flex items-center px-3 py-1 border border-gray-300 text-xs font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            >
              取消
            </button>
          </div>
        </div>
      );
    }

    // 預設狀態
    return (
      <>
        <ArrowUpTrayIcon className="mx-auto h-12 w-12 text-gray-400" />
        <h3 className="mt-2 text-sm font-medium text-gray-900">拖放檔案到這裡</h3>
        <p className="mt-1 text-xs text-gray-500">
          或點擊上傳 PDF 檔案 (最大 50MB)
        </p>
        <div className="mt-4">
          <label htmlFor="file-upload" className="cursor-pointer bg-white py-2 px-3 border border-gray-300 rounded-md shadow-sm text-sm leading-4 font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500">
            選擇檔案
            <input
              id="file-upload"
              name="file-upload"
              type="file"
              className="sr-only"
              onChange={handleFileChange}
              accept="application/pdf"
              disabled={uploadState.isUploading}
            />
          </label>
        </div>
      </>
    );
  };

  return (
    <div 
      id="file-upload-zone"
      className={`
        border-2 border-dashed rounded-lg p-6 text-center min-h-[200px] flex flex-col justify-center
        ${getDragOverStyle()}
        transition-all duration-200 ease-in-out
        ${uploadState.isUploading ? 'pointer-events-none' : ''}
      `}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {renderContent()}
    </div>
  );
};

export default FileUploadZone;
