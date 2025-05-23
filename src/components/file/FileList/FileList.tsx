import React, { useState } from 'react';
import { 
  DocumentTextIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  ArrowPathIcon,
  TrashIcon
} from '@heroicons/react/24/outline';
import { useFileStore } from '../../../stores/fileStore';
import ProgressBar from '../../common/ProgressBar/ProgressBar';
import { FileData } from '../../../types/file';

interface FileListProps {
  onFileSelect?: (fileId: string) => void;
}

const FileList: React.FC<FileListProps> = ({ onFileSelect }) => {
  const { files, currentFileId, setCurrentFile, removeFile } = useFileStore();
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  
  const handleFileClick = (fileId: string) => {
    setCurrentFile(fileId);
    onFileSelect?.(fileId);
  };
  
  // 处理删除文件
  const handleDeleteClick = (e: React.MouseEvent, fileId: string) => {
    e.stopPropagation(); // 防止触发文件选择
    setDeleteConfirmId(fileId);
  };
  
  const confirmDelete = (e: React.MouseEvent, fileId: string) => {
    e.stopPropagation();
    removeFile(fileId);
    setDeleteConfirmId(null);
  };
  
  const cancelDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    setDeleteConfirmId(null);
  };
  
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };
  
  const formatDate = (date: Date): string => {
    return new Date(date).toLocaleString('zh-TW', {
      year: 'numeric',
      month: 'numeric',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };
  
  const renderFileStatusIcon = (file: FileData) => {
    switch (file.status) {
      case 'completed':
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />;
      case 'error':
        return <ExclamationCircleIcon className="h-5 w-5 text-red-500" />;
      case 'processing':
      case 'uploading':
        return <ArrowPathIcon className="h-5 w-5 text-blue-500 animate-spin" />;
      default:
        return <DocumentTextIcon className="h-5 w-5 text-gray-400" />;
    }
  };
  
  if (files.length === 0) {
    return (
      <div className="p-4 text-center text-gray-500">
        尚未上傳任何檔案
      </div>
    );
  }
  
  return (
    <div className="overflow-y-auto max-h-full">
      <ul className="divide-y divide-gray-200">
        {files.map((file) => (
          <li 
            key={file.id}
            className={`
              px-4 py-3 hover:bg-gray-50 cursor-pointer
              ${file.id === currentFileId ? 'bg-blue-50' : ''}
            `}
            onClick={() => handleFileClick(file.id)}
          >
            <div className="flex items-center">
              <div className="flex-shrink-0">
                {renderFileStatusIcon(file)}
              </div>
              <div className="ml-3 flex-1 overflow-hidden">
                <div className="flex justify-between items-start">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {file.name}
                  </p>
                  
                  {deleteConfirmId === file.id ? (
                    <div 
                      className="flex items-center space-x-1 text-xs" 
                      onClick={(e) => e.stopPropagation()}
                    >
                      <button 
                        className="text-red-500 hover:text-red-700"
                        onClick={(e) => confirmDelete(e, file.id)}
                      >
                        確認
                      </button>
                      <button 
                        className="text-gray-500 hover:text-gray-700"
                        onClick={cancelDelete}
                      >
                        取消
                      </button>
                    </div>
                  ) : (
                    <button 
                      className="text-gray-400 hover:text-red-500 p-1"
                      onClick={(e) => handleDeleteClick(e, file.id)}
                    >
                      <TrashIcon className="h-4 w-4" />
                    </button>
                  )}
                </div>
                
                <div className="flex items-center text-xs text-gray-500">
                  <span>{formatFileSize(file.size)}</span>
                  <span className="mx-1">•</span>
                  <span>{formatDate(file.uploadedAt)}</span>
                </div>
                
                {(file.status === 'uploading' || file.status === 'processing') && (
                  <div className="mt-2">
                    <ProgressBar 
                      progress={file.processingProgress || 0} 
                      stage={file.status === 'uploading' ? 'uploading' : 'analyzing'} 
                      size="sm"
                      showLabel={false}
                    />
                  </div>
                )}
                
                {file.status === 'error' && (
                  <p className="mt-1 text-xs text-red-500">
                    處理失敗，請重試
                  </p>
                )}
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default FileList;
