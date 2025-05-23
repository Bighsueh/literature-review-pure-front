import React from 'react';
import { 
  DocumentTextIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  ArrowPathIcon
} from '@heroicons/react/24/outline';
import { useFileStore } from '../../../stores/fileStore';
import ProgressBar from '../../common/ProgressBar/ProgressBar';
import { FileData } from '../../../types/file';

interface FileListProps {
  onFileSelect?: (fileId: string) => void;
}

const FileList: React.FC<FileListProps> = ({ onFileSelect }) => {
  const { files, currentFileId, setCurrentFile } = useFileStore();
  
  const handleFileClick = (fileId: string) => {
    setCurrentFile(fileId);
    onFileSelect?.(fileId);
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
                <p className="text-sm font-medium text-gray-900 truncate">
                  {file.name}
                </p>
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
