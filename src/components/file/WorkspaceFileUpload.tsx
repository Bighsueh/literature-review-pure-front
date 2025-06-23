/**
 * 工作區檔案上傳組件 - FE-04 檔案管理系統重構
 * 支援工作區隔離的檔案上傳和批量處理
 */

import React, { useCallback, useState, useRef } from 'react';
import { 
  ArrowUpTrayIcon, 
  CheckCircleIcon,
  XCircleIcon,
  DocumentTextIcon,
  XMarkIcon
} from '@heroicons/react/24/outline';
import { useWorkspaceFileStore } from '../../stores/workspace/workspaceFileStore';
import { useWorkspace } from '../../contexts/WorkspaceContext';
import ProgressBar from '../common/ProgressBar/ProgressBar';

interface WorkspaceFileUploadProps {
  onUploadStart?: () => void;
  onUploadComplete?: () => void;
  onUploadError?: (error: Error) => void;
  className?: string;
  compact?: boolean;
  multiple?: boolean;
  maxFiles?: number;
  maxFileSize?: number; // in MB
}

interface UploadItem {
  id: string;
  file: File;
  status: 'pending' | 'uploading' | 'success' | 'error';
  progress: number;
  error?: string;
  isDuplicate?: boolean;
  duplicateFiles?: string[];
}

const WorkspaceFileUpload: React.FC<WorkspaceFileUploadProps> = ({
  onUploadStart,
  onUploadComplete,
  onUploadError,
  className = '',
  compact = false,
  multiple = true,
  maxFiles = 10,
  maxFileSize = 50 // 50MB
}) => {
  const { currentWorkspace } = useWorkspace();
  const { 
    papers, 
    uploadingFiles,
    uploadFile,
    refreshPapers
  } = useWorkspaceFileStore(currentWorkspace?.id || '');

  // 本地狀態
  const [isDragOver, setIsDragOver] = useState(false);
  const [uploadQueue, setUploadQueue] = useState<UploadItem[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // 檔案驗證
  const validateFile = useCallback((file: File): { valid: boolean; error?: string } => {
    // 檢查檔案類型
    if (file.type !== 'application/pdf') {
      return { valid: false, error: '只接受 PDF 檔案格式' };
    }

    // 檢查檔案大小
    const maxSizeBytes = maxFileSize * 1024 * 1024;
    if (file.size > maxSizeBytes) {
      return { valid: false, error: `檔案大小不能超過 ${maxFileSize}MB` };
    }

    // 檢查檔案名稱
    if (file.name.length > 255) {
      return { valid: false, error: '檔案名稱過長' };
    }

    return { valid: true };
  }, [maxFileSize]);

  // 檢查重複檔案
  const checkDuplicateFile = useCallback((file: File): { isDuplicate: boolean; duplicateFiles: string[] } => {
    // 確保 papers 是有效的陣列
    if (!Array.isArray(papers) || papers.length === 0) {
      return {
        isDuplicate: false,
        duplicateFiles: []
      };
    }
    
    const duplicateFiles = papers.filter(paper => 
      paper?.file_name && (
        paper.file_name === file.name || 
        paper.file_name.includes(file.name.replace('.pdf', ''))
      )
    ).map(paper => paper.file_name);
    
    return {
      isDuplicate: duplicateFiles.length > 0,
      duplicateFiles
    };
  }, [papers]);

  // 處理檔案選擇
  const handleFiles = useCallback(async (files: FileList | File[]) => {
    if (!currentWorkspace) {
      alert('請先選擇工作區');
      return;
    }

    const fileArray = Array.from(files);
    
    // 檢查檔案數量限制
    if (fileArray.length > maxFiles) {
      alert(`一次最多只能上傳 ${maxFiles} 個檔案`);
      return;
    }

    const newUploadItems: UploadItem[] = [];

    fileArray.forEach(file => {
      const validation = validateFile(file);
      const duplicateCheck = checkDuplicateFile(file);
      
      const uploadItem: UploadItem = {
        id: `upload_${Date.now()}_${Math.random()}`,
        file,
        status: validation.valid ? 'pending' : 'error',
        progress: 0,
        error: validation.error,
        isDuplicate: duplicateCheck.isDuplicate,
        duplicateFiles: duplicateCheck.duplicateFiles
      };
      
      newUploadItems.push(uploadItem);
    });

    setUploadQueue(prev => [...prev, ...newUploadItems]);
    
    // 開始上傳有效的檔案
    const validItems = newUploadItems.filter(item => item.status === 'pending');
    if (validItems.length > 0) {
      await processUploadQueue(validItems);
    }
  }, [currentWorkspace, maxFiles, validateFile, checkDuplicateFile]);

  // 處理上傳隊列
  const processUploadQueue = useCallback(async (items: UploadItem[]) => {
    setIsUploading(true);
    onUploadStart?.();

    for (const item of items) {
      try {
        // 更新狀態為上傳中
        setUploadQueue(prev => 
          prev.map(qItem => 
            qItem.id === item.id 
              ? { ...qItem, status: 'uploading' as const, progress: 0 }
              : qItem
          )
        );

        // 執行上傳
        const result = await uploadFile(item.file);
        
        if (result) {
          // 上傳成功
          setUploadQueue(prev => 
            prev.map(qItem => 
              qItem.id === item.id 
                ? { ...qItem, status: 'success' as const, progress: 100 }
                : qItem
            )
          );
          
          console.log(`✅ 檔案上傳成功: ${item.file.name}, Paper ID: ${result.paper_id}`);
        } else {
          // 上傳失敗
          setUploadQueue(prev => 
            prev.map(qItem => 
              qItem.id === item.id 
                ? { ...qItem, status: 'error' as const, error: '上傳失敗' }
                : qItem
            )
          );
        }
      } catch (error) {
        // 處理錯誤
        const errorMessage = error instanceof Error ? error.message : '上傳錯誤';
        setUploadQueue(prev => 
          prev.map(qItem => 
            qItem.id === item.id 
              ? { ...qItem, status: 'error' as const, error: errorMessage }
              : qItem
          )
        );
        onUploadError?.(error instanceof Error ? error : new Error(errorMessage));
      }
    }

    setIsUploading(false);
    onUploadComplete?.();
    
    // 刷新檔案列表
    await refreshPapers();
    
    // 清理成功的上傳項目（延遲清理以顯示成功狀態）
    setTimeout(() => {
      setUploadQueue(prev => prev.filter(item => item.status !== 'success'));
    }, 3000);
  }, [uploadFile, refreshPapers, onUploadStart, onUploadComplete, onUploadError]);

  // 拖放事件處理
  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    if (!isUploading) {
      setIsDragOver(true);
    }
  }, [isUploading]);
  
  const handleDragLeave = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  }, []);
  
  const handleDrop = useCallback(async (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    
    if (isUploading) return;
    
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      await handleFiles(files);
    }
  }, [isUploading, handleFiles]);
  
  const handleFileInputChange = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      await handleFiles(files);
    }
    
    // 重置 input 值
    e.target.value = '';
  }, [handleFiles]);

  // 點擊選擇檔案
  const handleClick = () => {
    if (!isUploading && fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  // 移除上傳項目
  const removeUploadItem = useCallback((itemId: string) => {
    setUploadQueue(prev => prev.filter(item => item.id !== itemId));
  }, []);

  // 重試上傳
  const retryUpload = useCallback(async (item: UploadItem) => {
    await processUploadQueue([item]);
  }, [processUploadQueue]);

  // 確認重複檔案上傳
  const confirmDuplicateUpload = useCallback(async (item: UploadItem) => {
    const updatedItem = { ...item, isDuplicate: false, status: 'pending' as const };
    setUploadQueue(prev => 
      prev.map(qItem => qItem.id === item.id ? updatedItem : qItem)
    );
    await processUploadQueue([updatedItem]);
  }, [processUploadQueue]);

  if (!currentWorkspace) {
    return (
      <div className="flex items-center justify-center p-4 bg-gray-100 rounded-lg text-gray-500">
        請先選擇工作區以上傳檔案
      </div>
    );
  }

  return (
    <div className={`w-full ${className}`}>
      {/* 上傳區域 */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleClick}
        className={`
          relative border-2 border-dashed rounded-lg transition-all duration-200 cursor-pointer
          ${compact ? 'p-4' : 'p-6'}
          ${isDragOver 
            ? 'border-blue-400 bg-blue-50' 
            : isUploading
              ? 'border-gray-300 bg-gray-50 cursor-not-allowed'
              : 'border-gray-300 hover:border-blue-400 hover:bg-blue-50'
          }
        `}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          multiple={multiple}
          onChange={handleFileInputChange}
          className="hidden"
          disabled={isUploading}
        />
        
        <div className="flex flex-col items-center justify-center text-center">
          <ArrowUpTrayIcon 
            className={`${compact ? 'w-8 h-8' : 'w-12 h-12'} text-gray-400 mb-2`} 
          />
          
          {compact ? (
            <div className="space-y-1">
              <p className="text-sm text-gray-600">
                點擊或拖放 PDF 檔案
              </p>
              <p className="text-xs text-gray-500">
                最大 {maxFileSize}MB
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              <p className="text-lg font-medium text-gray-900">
                上傳 PDF 檔案到 "{currentWorkspace.name}"
              </p>
              <p className="text-sm text-gray-600">
                點擊選擇檔案或直接拖放到此處
              </p>
              <p className="text-xs text-gray-500">
                支援 PDF 格式，單檔最大 {maxFileSize}MB，一次最多 {maxFiles} 個檔案
              </p>
            </div>
          )}
        </div>
        
        {isUploading && (
          <div className="absolute inset-0 bg-white bg-opacity-80 flex items-center justify-center rounded-lg">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
              <p className="text-sm text-gray-600">上傳中...</p>
            </div>
          </div>
        )}
      </div>

      {/* 上傳隊列 */}
      {uploadQueue.length > 0 && (
        <div className={`${compact ? 'mt-3' : 'mt-4'} space-y-2`}>
          <h4 className="text-sm font-medium text-gray-900">上傳進度</h4>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {uploadQueue.map((item) => (
              <UploadItem
                key={item.id}
                item={item}
                onRemove={removeUploadItem}
                onRetry={retryUpload}
                onConfirmDuplicate={confirmDuplicateUpload}
                compact={compact}
              />
            ))}
          </div>
        </div>
      )}

      {/* 進行中的上傳 */}
      {Object.keys(uploadingFiles).length > 0 && (
        <div className={`${compact ? 'mt-3' : 'mt-4'} space-y-2`}>
          <h4 className="text-sm font-medium text-gray-900">處理中</h4>
          <div className="space-y-2">
            {Object.entries(uploadingFiles).map(([uploadId, upload]) => (
              <div key={uploadId} className="p-3 bg-blue-50 rounded-md">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-900">{upload.fileName}</span>
                  <span className="text-sm text-blue-600">{upload.progress}%</span>
                </div>
                <ProgressBar progress={upload.progress} stage="uploading" />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

// 上傳項目組件
const UploadItem: React.FC<{
  item: UploadItem;
  onRemove: (itemId: string) => void;
  onRetry: (item: UploadItem) => void;
  onConfirmDuplicate: (item: UploadItem) => void;
  compact: boolean;
}> = ({ item, onRemove, onRetry, onConfirmDuplicate, compact }) => {
  const getStatusIcon = () => {
    switch (item.status) {
      case 'success':
        return <CheckCircleIcon className="w-5 h-5 text-green-500" />;
      case 'error':
        return <XCircleIcon className="w-5 h-5 text-red-500" />;
      case 'uploading':
        return <div className="w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />;
      default:
        return <DocumentTextIcon className="w-5 h-5 text-gray-400" />;
    }
  };

  const getStatusText = () => {
    if (item.isDuplicate && item.status === 'pending') {
      return '檔案可能重複';
    }
    
    switch (item.status) {
      case 'success':
        return '上傳成功';
      case 'error':
        return item.error || '上傳失敗';
      case 'uploading':
        return `上傳中 ${item.progress}%`;
      default:
        return '等待上傳';
    }
  };

  return (
    <div className={`flex items-center space-x-3 p-3 bg-white border rounded-lg ${
      item.status === 'error' ? 'border-red-200 bg-red-50' : 
      item.status === 'success' ? 'border-green-200 bg-green-50' :
      item.isDuplicate ? 'border-yellow-200 bg-yellow-50' :
      'border-gray-200'
    }`}>
      {/* 狀態圖標 */}
      <div className="flex-shrink-0">
        {getStatusIcon()}
      </div>
      
      {/* 檔案資訊 */}
      <div className="flex-1 min-w-0">
        <p className={`${compact ? 'text-xs' : 'text-sm'} font-medium text-gray-900 truncate`}>
          {item.file.name}
        </p>
        <p className={`${compact ? 'text-xs' : 'text-sm'} text-gray-500`}>
          {getStatusText()}
        </p>
        
        {/* 重複檔案警告 */}
        {item.isDuplicate && item.duplicateFiles && (
          <div className="mt-1">
            <p className="text-xs text-yellow-700">
              可能與以下檔案重複：{item.duplicateFiles.join(', ')}
            </p>
          </div>
        )}
        
        {/* 進度條 */}
        {item.status === 'uploading' && (
          <div className="mt-2">
            <ProgressBar progress={item.progress} stage="uploading" />
          </div>
        )}
      </div>
      
      {/* 操作按鈕 */}
      <div className="flex-shrink-0 flex items-center space-x-1">
        {item.isDuplicate && item.status === 'pending' && (
          <button
            onClick={() => onConfirmDuplicate(item)}
            className="px-2 py-1 text-xs bg-yellow-600 text-white rounded hover:bg-yellow-700"
          >
            仍要上傳
          </button>
        )}
        
        {item.status === 'error' && (
          <button
            onClick={() => onRetry(item)}
            className="px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            重試
          </button>
        )}
        
        {item.status !== 'uploading' && (
          <button
            onClick={() => onRemove(item.id)}
            className="p-1 text-gray-400 hover:text-red-600 rounded"
          >
            <XMarkIcon className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
};

export default WorkspaceFileUpload;