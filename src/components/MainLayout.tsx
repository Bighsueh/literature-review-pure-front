import React, { useState, useEffect } from 'react';
import { useAppStore } from '../stores/appStore';
import LeftPanel from './LeftPanel';
import CenterPanel from './CenterPanel';
import RightPanel from './RightPanel';
import Modal from './common/Modal/Modal';
import PDFPreview from './file/PDFPreview/PDFPreview';
import { useFileStore } from '../stores/fileStore';
import { ProcessedSentence } from '../types/file';

const MainLayout: React.FC = () => {
  const { ui, setUI, selectedReferences } = useAppStore();
  const { files, currentFileId } = useFileStore();
  const [highlightedSentence, setHighlightedSentence] = useState<ProcessedSentence | null>(null);
  
  // Resize handlers for panels
  const handleLeftPanelResize = (newWidth: number) => {
    setUI({ leftPanelWidth: newWidth });
  };
  
  const handleRightPanelResize = (newWidth: number) => {
    setUI({ rightPanelWidth: newWidth });
  };
  
  // PDF Modal handlers
  const handleOpenPDFModal = () => {
    setUI({ isPDFModalOpen: true });
  };
  
  const handleClosePDFModal = () => {
    setUI({ isPDFModalOpen: false });
  };
  
  // Reference click handler
  const handleReferenceClick = (sentence: ProcessedSentence) => {
    setHighlightedSentence(sentence);
    handleOpenPDFModal();
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
          onViewInPDF={handleReferenceClick} 
        />
      </div>
      
      {/* PDF Preview Modal */}
      <Modal 
        isOpen={ui.isPDFModalOpen} 
        onClose={handleClosePDFModal}
        title="PDF 預覽"
        size="xl"
      >
        <div className="h-[80vh]">
          <PDFPreview 
            fileId={currentFileId || undefined}
            highlightText={highlightedSentence?.content}
          />
        </div>
      </Modal>
    </div>
  );
};

export default MainLayout;
