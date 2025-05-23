import React, { useState } from 'react';
import { useAppStore } from '../../../stores/appStore';
import { useFileStore } from '../../../stores/fileStore'; 
import PDFViewer from '../../common/PDFViewer'; 
import { ProcessedSentence } from '../../../types/file'; 
import { XMarkIcon } from '@heroicons/react/24/outline'; 

const ReferencesPanel: React.FC = () => {
  const { selectedReferences } = useAppStore();
  const { files } = useFileStore(); 

  const [showPDFModal, setShowPDFModal] = useState(false);
  const [pdfFileToView, setPdfFileToView] = useState<File | Blob | null>(null);
  const [pdfPageToView, setPdfPageToView] = useState<number | undefined>(undefined);

  const handleViewInPDFClick = (reference: ProcessedSentence) => {
    if (!reference.fileId || typeof reference.pageNumber !== 'number') {
      console.error('File ID or Page Number is missing for this reference.');
      return;
    }

    const fileData = files.find(f => f.id === reference.fileId);

    if (fileData && fileData.blob) {
      setPdfFileToView(fileData.blob);
      setPdfPageToView(reference.pageNumber);
      setShowPDFModal(true);
    } else {
      console.error('PDF file data or blob not found for this reference.');
    }
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
  
  if (selectedReferences.length === 0 && !showPDFModal) { 
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
                onClick={() => handleViewInPDFClick(reference)} 
              >
                在 PDF 中查看
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

      {showPDFModal && pdfFileToView && (
        <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl h-[90vh] flex flex-col">
            <div className="flex justify-between items-center p-4 border-b">
              <h4 className="text-lg font-medium">PDF 預覽</h4>
              <button 
                onClick={() => setShowPDFModal(false)} 
                className="text-gray-500 hover:text-gray-700"
              >
                <XMarkIcon className="h-6 w-6" />
              </button>
            </div>
            <div className="flex-grow overflow-hidden">
              <PDFViewer 
                file={pdfFileToView} 
                pageNumber={pdfPageToView} 
                onDocumentLoadError={(err) => console.error('PDF Load Error in Modal:', err)}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ReferencesPanel;
