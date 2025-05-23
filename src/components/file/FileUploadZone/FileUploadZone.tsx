import React, { useCallback, useState } from 'react';
import { ArrowUpTrayIcon } from '@heroicons/react/24/outline';
import { useFileProcessor } from '../../../hooks/useFileProcessor';

interface FileUploadZoneProps {
  onUploadStart?: () => void;
  onUploadComplete?: () => void;
  onUploadError?: (error: any) => void;
}

const FileUploadZone: React.FC<FileUploadZoneProps> = ({
  onUploadStart,
  onUploadComplete,
  onUploadError
}) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const { processFile } = useFileProcessor();
  
  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  }, []);
  
  const handleDragLeave = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  }, []);
  
  const handleDrop = useCallback(async (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    
    const files = Array.from(e.dataTransfer.files);
    if (files.length === 0) return;
    
    // 只處理第一個檔案
    const file = files[0];
    
    // 檢查檔案類型 (只接受 PDF)
    if (file.type !== 'application/pdf') {
      alert('只接受 PDF 檔案');
      return;
    }
    
    handleFileUpload(file);
  }, []);
  
  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    
    const file = files[0];
    
    // 檢查檔案類型 (只接受 PDF)
    if (file.type !== 'application/pdf') {
      alert('只接受 PDF 檔案');
      return;
    }
    
    handleFileUpload(file);
    
    // 重置 input 值，讓相同檔案可以再次上傳
    e.target.value = '';
  }, []);
  
  const handleFileUpload = async (file: File) => {
    try {
      onUploadStart?.();
      await processFile(file);
      onUploadComplete?.();
    } catch (error) {
      console.error('File upload error:', error);
      onUploadError?.(error);
    }
  };
  
  return (
    <div 
      className={`
        border-2 border-dashed rounded-lg p-6 text-center
        ${isDragOver ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'}
        transition-colors duration-200 ease-in-out
      `}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <ArrowUpTrayIcon className="mx-auto h-12 w-12 text-gray-400" />
      <h3 className="mt-2 text-sm font-medium text-gray-900">拖放檔案到這裡</h3>
      <p className="mt-1 text-xs text-gray-500">或點擊上傳 PDF 檔案</p>
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
          />
        </label>
      </div>
    </div>
  );
};

export default FileUploadZone;
