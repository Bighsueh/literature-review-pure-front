import React, { useState, useRef, useCallback } from 'react';
import { 
  CloudArrowUpIcon, 
  DocumentTextIcon,
  XCircleIcon,
  CheckCircleIcon,
  ExclamationCircleIcon
} from '@heroicons/react/24/outline';
import { useResponsive } from '../../hooks/useResponsive';

interface FileUploadItem {
  id: string;
  file: File;
  status: 'pending' | 'uploading' | 'success' | 'error';
  progress: number;
  error?: string;
}

interface ResponsiveFileUploadProps {
  onFileSelect?: (files: File[]) => void;
  onFileRemove?: (fileId: string) => void;
  acceptedTypes?: string[];
  maxFileSize?: number; // in bytes
  maxFiles?: number;
  disabled?: boolean;
  className?: string;
}

const ResponsiveFileUpload: React.FC<ResponsiveFileUploadProps> = ({
  onFileSelect,
  onFileRemove,
  acceptedTypes = ['.pdf', '.doc', '.docx', '.txt'],
  maxFileSize = 10 * 1024 * 1024, // 10MB
  maxFiles = 5,
  disabled = false,
  className = ""
}) => {
  const [dragActive, setDragActive] = useState(false);
  const [uploadItems, setUploadItems] = useState<FileUploadItem[]>([]);
  const [showHelp, setShowHelp] = useState(false);
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dropZoneRef = useRef<HTMLDivElement>(null);
  const { isMobile } = useResponsive();

  // 驗證檔案
  const validateFile = useCallback((file: File): string | null => {
    // 檢查檔案類型
    const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!acceptedTypes.includes(fileExtension)) {
      return `不支援的檔案格式，僅支援: ${acceptedTypes.join(', ')}`;
    }

    // 檢查檔案大小
    if (file.size > maxFileSize) {
      const maxSizeMB = maxFileSize / (1024 * 1024);
      return `檔案大小不能超過 ${maxSizeMB}MB`;
    }

    // 檢查檔案數量
    if (uploadItems.length >= maxFiles) {
      return `最多只能上傳 ${maxFiles} 個檔案`;
    }

    return null;
  }, [acceptedTypes, maxFileSize, maxFiles, uploadItems.length]);

  // 處理檔案選擇
  const handleFiles = useCallback((files: FileList | File[]) => {
    const fileArray = Array.from(files);
    const validFiles: File[] = [];
    const newUploadItems: FileUploadItem[] = [];

    fileArray.forEach(file => {
      const error = validateFile(file);
      const fileItem: FileUploadItem = {
        id: `${file.name}-${Date.now()}-${Math.random()}`,
        file,
        status: error ? 'error' : 'pending',
        progress: 0,
        error: error || undefined
      };
      
      if (!error) {
        validFiles.push(file);
      }
      
      newUploadItems.push(fileItem);
    });

    setUploadItems(prev => [...prev, ...newUploadItems]);
    
    if (validFiles.length > 0) {
      onFileSelect?.(validFiles);
    }
  }, [validateFile, onFileSelect]);

  // 拖放事件處理
  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDragIn = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
      setDragActive(true);
    }
  }, []);

  const handleDragOut = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (disabled) return;
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files);
    }
  }, [disabled, handleFiles]);

  // 點擊選擇檔案
  const handleClick = () => {
    if (!disabled && fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  // 檔案輸入變化
  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(e.target.files);
      // 清除輸入值以允許重複選擇同一檔案
      e.target.value = '';
    }
  };

  // 移除檔案
  const handleRemoveFile = (fileId: string) => {
    setUploadItems(prev => prev.filter(item => item.id !== fileId));
    onFileRemove?.(fileId);
  };

  // 格式化檔案大小
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // 渲染狀態圖示
  const renderStatusIcon = (status: FileUploadItem['status']) => {
    switch (status) {
      case 'success':
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />;
      case 'error':
        return <ExclamationCircleIcon className="h-5 w-5 text-red-500" />;
      case 'uploading':
        return (
          <div className="h-5 w-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        );
      default:
        return <DocumentTextIcon className="h-5 w-5 text-gray-400" />;
    }
  };

  // 渲染檔案列表
  const renderFileList = () => {
    if (uploadItems.length === 0) return null;

    return (
      <div className="mt-4 space-y-2">
        <h4 className="text-sm font-medium text-gray-700">
          已選擇的檔案 ({uploadItems.length}/{maxFiles})
        </h4>
        <div className="space-y-2 max-h-40 overflow-y-auto">
          {uploadItems.map((item) => (
            <div
              key={item.id}
              className={`flex items-center justify-between p-3 rounded-lg border ${
                item.status === 'error' ? 'border-red-200 bg-red-50' : 'border-gray-200 bg-gray-50'
              }`}
            >
              <div className="flex items-center flex-1 min-w-0">
                {renderStatusIcon(item.status)}
                <div className="ml-3 flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {item.file.name}
                  </p>
                  <p className="text-xs text-gray-500">
                    {formatFileSize(item.file.size)}
                  </p>
                  {item.error && (
                    <p className="text-xs text-red-600 mt-1">{item.error}</p>
                  )}
                </div>
              </div>
              
              {/* 進度條 */}
              {item.status === 'uploading' && (
                <div className="flex items-center ml-4">
                  <div className="w-20 bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${item.progress}%` }}
                    />
                  </div>
                  <span className="ml-2 text-xs text-gray-500 font-mono">
                    {item.progress}%
                  </span>
                </div>
              )}
              
              {/* 移除按鈕 */}
              <button
                onClick={() => handleRemoveFile(item.id)}
                className="ml-2 p-1 text-gray-400 hover:text-red-500 transition-colors min-h-[32px] min-w-[32px] flex items-center justify-center"
                aria-label="移除檔案"
              >
                <XCircleIcon className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
      </div>
    );
  };

  // 渲染幫助訊息
  const renderHelp = () => {
    if (!showHelp) return null;

    return (
      <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
        <h4 className="text-sm font-medium text-blue-900 mb-2">上傳說明</h4>
        <ul className="text-xs text-blue-800 space-y-1">
          <li>• 支援格式: {acceptedTypes.join(', ')}</li>
          <li>• 檔案大小限制: {formatFileSize(maxFileSize)}</li>
          <li>• 最多可上傳: {maxFiles} 個檔案</li>
          {isMobile && <li>• 點擊上傳區域選擇檔案</li>}
          {!isMobile && <li>• 可拖放檔案到上傳區域</li>}
        </ul>
      </div>
    );
  };

  return (
    <div className={`relative ${className}`}>
      {/* 主要上傳區域 */}
      <div
        ref={dropZoneRef}
        onDragEnter={handleDragIn}
        onDragLeave={handleDragOut}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={handleClick}
        className={`
          relative border-2 border-dashed rounded-lg transition-all duration-200 cursor-pointer
          ${isMobile ? 'p-6' : 'p-8'}
          ${dragActive 
            ? 'border-blue-500 bg-blue-50' 
            : disabled 
              ? 'border-gray-200 bg-gray-50 cursor-not-allowed' 
              : 'border-gray-300 hover:border-blue-400 hover:bg-blue-50'
          }
        `}
        role="button"
        tabIndex={0}
        aria-label="選擇檔案上傳"
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            handleClick();
          }
        }}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={acceptedTypes.join(',')}
          onChange={handleFileInput}
          className="hidden"
          disabled={disabled}
        />
        
        <div className="text-center">
          <CloudArrowUpIcon 
            className={`mx-auto ${isMobile ? 'h-8 w-8' : 'h-12 w-12'} ${
              disabled ? 'text-gray-300' : 'text-gray-400'
            }`} 
          />
          
          <div className="mt-4">
            <h3 className={`${isMobile ? 'text-base' : 'text-lg'} font-medium ${
              disabled ? 'text-gray-400' : 'text-gray-900'
            }`}>
              {isMobile ? '點擊選擇檔案' : '拖放檔案到此處，或點擊選擇'}
            </h3>
            
            <p className={`mt-2 text-sm ${disabled ? 'text-gray-400' : 'text-gray-500'}`}>
              支援 {acceptedTypes.join(', ')} 格式
            </p>
            
            <p className="text-xs text-gray-400 mt-1">
              最大 {formatFileSize(maxFileSize)}，最多 {maxFiles} 個檔案
            </p>
          </div>
          
          {/* 移動版額外提示 */}
          {isMobile && (
            <div className="mt-4 p-3 bg-gray-50 rounded-lg">
              <p className="text-xs text-gray-600">
                💡 提示：選擇多個檔案可一次上傳
              </p>
            </div>
          )}
        </div>
        
        {/* 拖放活動指示器 */}
        {dragActive && (
          <div className="absolute inset-0 bg-blue-100 bg-opacity-50 flex items-center justify-center rounded-lg">
            <div className="text-blue-600 text-lg font-medium">
              放開以上傳檔案
            </div>
          </div>
        )}
      </div>
      
      {/* 幫助按鈕 */}
      <div className="mt-4 flex justify-between items-center">
        <button
          onClick={() => setShowHelp(!showHelp)}
          className="text-sm text-blue-600 hover:text-blue-700 transition-colors"
        >
          {showHelp ? '隱藏說明' : '顯示上傳說明'}
        </button>
        
        {uploadItems.length > 0 && (
          <button
            onClick={() => setUploadItems([])}
            className="text-sm text-red-600 hover:text-red-700 transition-colors"
          >
            清除所有檔案
          </button>
        )}
      </div>
      
      {renderHelp()}
      {renderFileList()}
    </div>
  );
};

export default ResponsiveFileUpload; 