import React, { useEffect, useRef, useState } from 'react';
import * as pdfjs from 'pdfjs-dist';

// Configure PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = '/pdf.worker.js';
import { usePDFViewer } from '../../../hooks/usePDFViewer';
import { 
  ChevronLeftIcon, 
  ChevronRightIcon,
  MagnifyingGlassIcon,
  DocumentArrowDownIcon
} from '@heroicons/react/24/outline';
import { useFileStore } from '../../../stores/fileStore';

interface PDFPreviewProps {
  fileId?: string;
  highlightText?: string;
  onTextHighlighted?: (text: string, position: { x: number; y: number; width: number; height: number }) => void;
}

const PDFPreview: React.FC<PDFPreviewProps> = ({
  fileId,
  highlightText,
  // onTextHighlighted // Not used in this component
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { files } = useFileStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [scale, setScale] = useState(1.2);
  
  const {
    pdfDocument,
    documentInfo,
    currentPage,
    isLoading,
    error,
    loadPDF,
    // renderPage, // Not used in this component
    searchText,
    setCurrentPage
  } = usePDFViewer();

  // 當 fileId 改變時載入 PDF
  useEffect(() => {
    if (!fileId) return;
    
    const file = files.find(f => f.id === fileId);
    if (file?.blob) {
      loadPDF(file.blob);
    }
  }, [fileId, files, loadPDF]);

  // 當頁面或縮放比例改變時重新渲染
  useEffect(() => {
    const renderCurrentPage = async () => {
      if (!pdfDocument || !canvasRef.current) return;
      
      const page = await pdfDocument.getPage(currentPage);
      const viewport = page.getViewport({ scale });
      
      const canvas = canvasRef.current;
      const context = canvas.getContext('2d');
      
      if (!context) return;
      
      canvas.height = viewport.height;
      canvas.width = viewport.width;
      
      const renderContext = {
        canvasContext: context,
        viewport
      };
      
      page.render(renderContext);
    };
    
    renderCurrentPage();
  }, [pdfDocument, currentPage, scale]);

  // 當 highlightText 改變時搜尋文本
  useEffect(() => {
    if (highlightText && pdfDocument) {
      searchText(highlightText);
    }
  }, [highlightText, pdfDocument, searchText]);

  const handlePreviousPage = () => {
    if (currentPage > 1) {
      setCurrentPage(currentPage - 1);
    }
  };

  const handleNextPage = () => {
    if (pdfDocument && currentPage < pdfDocument.numPages) {
      setCurrentPage(currentPage + 1);
    }
  };
  
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      searchText(searchQuery);
    }
  };
  
  const handleZoomIn = () => {
    setScale(prevScale => Math.min(prevScale + 0.2, 3));
  };
  
  const handleZoomOut = () => {
    setScale(prevScale => Math.max(prevScale - 0.2, 0.5));
  };
  
  if (!fileId) {
    return (
      <div className="flex flex-col items-center justify-center h-full bg-gray-50 text-gray-500">
        <DocumentArrowDownIcon className="h-12 w-12 mb-4" />
        <p>請選擇 PDF 檔案以預覽</p>
      </div>
    );
  }
  
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-red-500">
        <p>載入 PDF 時發生錯誤</p>
        <p className="text-sm mt-2">{error}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* 工具列 */}
      <div className="flex items-center justify-between p-2 border-b">
        <div className="flex items-center space-x-2">
          <button
            onClick={handlePreviousPage}
            disabled={currentPage <= 1}
            className="p-1 rounded-md hover:bg-gray-100 disabled:opacity-50"
          >
            <ChevronLeftIcon className="h-5 w-5" />
          </button>
          
          <span className="text-sm">
            {currentPage} / {documentInfo?.numPages || 1}
          </span>
          
          <button
            onClick={handleNextPage}
            disabled={!pdfDocument || currentPage >= pdfDocument.numPages}
            className="p-1 rounded-md hover:bg-gray-100 disabled:opacity-50"
          >
            <ChevronRightIcon className="h-5 w-5" />
          </button>
        </div>
        
        <form onSubmit={handleSearch} className="flex items-center">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="搜尋文本..."
            className="text-sm border rounded-md px-2 py-1 w-36"
          />
          <button
            type="submit"
            className="ml-1 p-1 rounded-md hover:bg-gray-100"
          >
            <MagnifyingGlassIcon className="h-5 w-5" />
          </button>
        </form>
        
        <div className="flex items-center space-x-2">
          <button
            onClick={handleZoomOut}
            className="p-1 rounded-md hover:bg-gray-100"
          >
            -
          </button>
          
          <span className="text-sm">{Math.round(scale * 100)}%</span>
          
          <button
            onClick={handleZoomIn}
            className="p-1 rounded-md hover:bg-gray-100"
          >
            +
          </button>
        </div>
      </div>
      
      {/* PDF 渲染區域 */}
      <div className="flex-1 overflow-auto bg-gray-300 flex justify-center p-4">
        <canvas
          ref={canvasRef}
          className="shadow-lg bg-white"
        />
      </div>
      
      {/* 高亮文本顯示 */}
      {highlightText && (
        <div className="p-2 bg-yellow-100 border-t text-sm">
          <p className="font-medium">已高亮:</p>
          <p className="mt-1 text-gray-700">{highlightText}</p>
        </div>
      )}
    </div>
  );
};

export default PDFPreview;
