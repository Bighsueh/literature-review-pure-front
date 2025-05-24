import React, { useState } from 'react';
import { useAppStore } from '../stores/appStore';
import LeftPanel from './LeftPanel';
import CenterPanel from './CenterPanel';
import RightPanel from './RightPanel';
import Modal from './common/Modal/Modal';
import { useFileStore } from '../stores/fileStore';
import { ProcessedSentence } from '../types/file';

const MainLayout: React.FC = () => {
  const { ui, setUI } = useAppStore();
  const { files } = useFileStore();
  const [highlightedSentence, setHighlightedSentence] = useState<ProcessedSentence | null>(null);
  
  // Resize handlers for panels
  const handleLeftPanelResize = (newWidth: number) => {
    setUI({ leftPanelWidth: newWidth });
  };
  
  const handleRightPanelResize = (newWidth: number) => {
    setUI({ rightPanelWidth: newWidth });
  };
  
  // Reference info modal handlers
  const handleOpenInfoModal = () => {
    setUI({ isPDFModalOpen: true });
  };
  
  const handleCloseInfoModal = () => {
    setUI({ isPDFModalOpen: false });
  };
  
  // Reference click handler
  const handleReferenceClick = (sentence: ProcessedSentence) => {
    setHighlightedSentence(sentence);
    handleOpenInfoModal();
  };
  
  // 獲取類型標籤
  const getTypeLabel = (type: string) => {
    switch (type) {
      case 'OD': return '操作型定義';
      case 'CD': return '概念型定義';
      default: return '其他';
    }
  };
  
  // 獲取類型顏色
  const getTypeColor = (type: string) => {
    switch (type) {
      case 'OD': return 'bg-blue-100 text-blue-800';
      case 'CD': return 'bg-purple-100 text-purple-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };
  
  // 獲取文件名稱
  const getFileName = (fileId?: string) => {
    if (!fileId) return '未知檔案';
    const file = files.find(f => f.id === fileId);
    return file?.name || '未知檔案';
  };
  
  return (
    <div className="flex h-screen bg-gray-100 overflow-hidden">
      {/* Left Panel - File Management */}
      <div 
        className="h-full bg-white shadow-sm" 
        style={{ width: `${ui.leftPanelWidth}px` }}
      >
        <LeftPanel onResize={handleLeftPanelResize} />
      </div>
      
      {/* Center Panel - Chat */}
      <div className="flex-1 h-full flex flex-col">
        <CenterPanel onReferenceClick={handleReferenceClick} />
      </div>
      
      {/* Right Panel - Progress & References */}
      <div 
        className="h-full bg-white shadow-sm" 
        style={{ width: `${ui.rightPanelWidth}px` }}
      >
        <RightPanel 
          onResize={handleRightPanelResize} 
        />
      </div>
      
      {/* Reference Info Modal */}
      {highlightedSentence && (
        <Modal 
          isOpen={ui.isPDFModalOpen} 
          onClose={handleCloseInfoModal}
          title="文件資訊"
          size="lg"
        >
          <div className="p-6">
            <div className="grid grid-cols-3 gap-4 mb-4">
              <div>
                <p className="text-sm font-medium text-gray-500">檔案名稱</p>
                <p className="mt-1">{getFileName(highlightedSentence.fileId)}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-500">頁碼</p>
                <p className="mt-1">{typeof highlightedSentence.pageNumber === 'number' ? highlightedSentence.pageNumber : '未知'}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-500">類型</p>
                <p className="mt-1">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${getTypeColor(highlightedSentence.type)}`}>
                    {getTypeLabel(highlightedSentence.type)}
                  </span>
                </p>
              </div>
            </div>
            
            <div className="mb-4">
              <p className="text-sm font-medium text-gray-500">句子內容</p>
              <p className="mt-1 p-3 bg-gray-50 rounded-md">{highlightedSentence.content}</p>
            </div>
            
            {highlightedSentence.reason && (
              <div>
                <p className="text-sm font-medium text-gray-500">分類原因</p>
                <p className="mt-1 p-3 bg-gray-50 rounded-md italic">{highlightedSentence.reason}</p>
              </div>
            )}
          </div>
        </Modal>
      )}
    </div>
  );
};

export default MainLayout;
