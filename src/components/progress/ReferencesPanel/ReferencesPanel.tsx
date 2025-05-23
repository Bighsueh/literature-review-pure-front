import React, { useState } from 'react';
import { useAppStore } from '../../../stores/appStore';
import { useFileStore } from '../../../stores/fileStore'; 
import { ProcessedSentence } from '../../../types/file'; 
import { XMarkIcon, DocumentTextIcon } from '@heroicons/react/24/outline'; 

const ReferencesPanel: React.FC = () => {
  const { selectedReferences } = useAppStore();
  const { files } = useFileStore(); 

  const [showInfoModal, setShowInfoModal] = useState(false);
  const [selectedReference, setSelectedReference] = useState<ProcessedSentence | null>(null);
  const [fileName, setFileName] = useState<string>("");

  const handleViewInfoClick = (reference: ProcessedSentence) => {
    setSelectedReference(reference);
    
    // 獲取檔案名稱（如果有）
    if (reference.fileId) {
      const fileData = files.find(f => f.id === reference.fileId);
      if (fileData) {
        setFileName(fileData.name || '未知檔案');
      } else {
        setFileName('未知檔案');
      }
    } else {
      setFileName('未知檔案');
    }
    
    setShowInfoModal(true);
  };
  
  const getTypeLabel = (type: string) => {
    switch (type) {
      case 'OD': return '操作型定義';
      case 'CD': return '概念型定義';
      default: return '其他';
    }
  };
  
  const getTypeColor = (type: string) => {
    switch (type) {
      case 'OD': return 'bg-blue-100 text-blue-800';
      case 'CD': return 'bg-purple-100 text-purple-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };
  
  if (selectedReferences.length === 0 && !showInfoModal) { 
    return (
      <div className="p-4 text-center text-gray-500">
        <p>尚未選擇任何引用句子</p>
        <p className="text-sm mt-2">點擊回答中的引用來查看詳情</p>
      </div>
    );
  }

  return (
    <div className="overflow-y-auto h-full"> 
      <div className="p-4">
        <h3 className="text-lg font-medium text-gray-900 mb-4">引用原文</h3>
        
        {selectedReferences.map((reference) => (
          <div 
            key={reference.id} 
            className="mb-4 p-3 bg-white rounded-lg shadow-sm border border-gray-200"
          >
            <div className="flex justify-between items-start mb-2">
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${getTypeColor(reference.type)}`}>
                {getTypeLabel(reference.type)}
              </span>
              
              <button
                className="text-xs text-blue-600 hover:text-blue-800"
                onClick={() => handleViewInfoClick(reference)} 
              >
                查看詳細資訊
              </button>
            </div>
            
            <p className="text-sm text-gray-800 mb-2">{reference.content}</p>
            
            {reference.reason && (
              <div className="text-xs text-gray-600 border-t pt-2 mt-2">
                <p className="font-medium">分類原因:</p>
                <p className="mt-1 italic">{reference.reason}</p>
              </div>
            )}
          </div>
        ))}
      </div>

      {showInfoModal && selectedReference && (
        <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-lg flex flex-col">
            <div className="flex justify-between items-center p-4 border-b">
              <h4 className="text-lg font-medium flex items-center">
                <DocumentTextIcon className="h-5 w-5 mr-2 text-gray-600" />
                文件資訊
              </h4>
              <button 
                onClick={() => setShowInfoModal(false)} 
                className="text-gray-500 hover:text-gray-700"
              >
                <XMarkIcon className="h-6 w-6" />
              </button>
            </div>
            <div className="p-6">
              <div className="grid grid-cols-3 gap-4 mb-4">
                <div>
                  <p className="text-sm font-medium text-gray-500">檔案名稱</p>
                  <p className="mt-1">{fileName}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-500">頁碼</p>
                  <p className="mt-1">{typeof selectedReference.pageNumber === 'number' ? selectedReference.pageNumber : '未知'}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-500">類型</p>
                  <p className="mt-1">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getTypeColor(selectedReference.type)}`}>
                      {getTypeLabel(selectedReference.type)}
                    </span>
                  </p>
                </div>
              </div>
              
              <div className="mb-4">
                <p className="text-sm font-medium text-gray-500">句子內容</p>
                <p className="mt-1 p-3 bg-gray-50 rounded-md">{selectedReference.content}</p>
              </div>
              
              {selectedReference.reason && (
                <div>
                  <p className="text-sm font-medium text-gray-500">分類原因</p>
                  <p className="mt-1 p-3 bg-gray-50 rounded-md italic">{selectedReference.reason}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ReferencesPanel;
