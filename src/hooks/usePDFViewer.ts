// hooks/usePDFViewer.ts
import { useState, useCallback, useEffect } from 'react';
import * as pdfjs from 'pdfjs-dist';
import { TextPosition } from '../types/file';

// 已移除未使用的 PDFMetadata 接口

// Ensure PDF.js worker is configured
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.mjs',
  import.meta.url
).toString();

interface PDFDocumentInfo {
  numPages: number;
  title?: string;
}

export const usePDFViewer = () => {
  const [pdfDocument, setPdfDocument] = useState<pdfjs.PDFDocumentProxy | null>(null);
  const [documentInfo, setDocumentInfo] = useState<PDFDocumentInfo | null>(null);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageContent, setPageContent] = useState<string>('');
  const [highlightPositions, setHighlightPositions] = useState<TextPosition[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * 載入 PDF 檔案
   */
  const loadPDF = useCallback(async (fileOrUrl: File | string) => {
    setIsLoading(true);
    setError(null);
    
    try {
      let loadingTask;
      
      if (fileOrUrl instanceof File) {
        // 從 File 對象加載 PDF
        const arrayBuffer = await fileOrUrl.arrayBuffer();
        loadingTask = pdfjs.getDocument({ data: new Uint8Array(arrayBuffer) });
      } else if (typeof fileOrUrl === 'string') {
        // 從 URL 字符串加載 PDF
        loadingTask = pdfjs.getDocument({ url: fileOrUrl });
      } else {
        throw new Error('Invalid input: expected File object or URL string');
      }
      
      const pdf = await loadingTask.promise;
      setPdfDocument(pdf);
      
      // 獲取文檔信息
      const metadata = await pdf.getMetadata();
      const info = metadata.info as { Title?: string } || {};
      setDocumentInfo({
        numPages: pdf.numPages,
        title: info.Title
      });
      
      setCurrentPage(1);
      setIsLoading(false);
      return pdf;
    } catch (err) {
      console.error('Failed to load PDF:', err);
      setError(err instanceof Error ? err.message : 'Failed to load PDF');
      setIsLoading(false);
      return null;
    }
  }, []);

  /**
   * 渲染指定頁面
   */
  const renderPage = useCallback(async (pageNumber: number) => {
    if (!pdfDocument || pageNumber < 1 || pageNumber > pdfDocument.numPages) {
      return null;
    }
    
    try {
      const page = await pdfDocument.getPage(pageNumber);
      setCurrentPage(pageNumber);
      
      // 提取頁面文本內容
      const textContent = await page.getTextContent();
      const pageText = textContent.items.map(item => 'str' in item ? item.str : '').join(' ');
      setPageContent(pageText);
      
      return page;
    } catch (err) {
      console.error(`Error rendering page ${pageNumber}:`, err);
      setError(`Error rendering page ${pageNumber}`);
      return null;
    }
  }, [pdfDocument]);

  /**
   * 在 PDF 中搜尋文本
   */
  const searchText = useCallback(async (searchTerm: string) => {
    if (!pdfDocument || !searchTerm) {
      setHighlightPositions([]);
      return [];
    }
    
    const positions: TextPosition[] = [];
    
    for (let i = 1; i <= pdfDocument.numPages; i++) {
      const page = await pdfDocument.getPage(i);
      const textContent = await page.getTextContent();
      const pageText = textContent.items.map(item => 'str' in item ? item.str : '').join(' ');
      
      if (pageText.includes(searchTerm)) {
        // 找到匹配頁面，設置當前頁
        setCurrentPage(i);
        
        // 這裡我們應該計算文本在頁面上的位置
        // 簡化版本：僅標記有匹配項的頁面
        // 真實實現需要更複雜的文本位置計算
        positions.push({
          x: 0,
          y: 0,
          width: 0,
          height: 0
        });
        
        break; // 找到第一個匹配即停止
      }
    }
    
    setHighlightPositions(positions);
    return positions;
  }, [pdfDocument]);

  // 清理函數
  useEffect(() => {
    return () => {
      if (pdfDocument) {
        pdfDocument.destroy();
        setPdfDocument(null);
      }
    };
  }, [pdfDocument]);

  return {
    pdfDocument,
    documentInfo,
    currentPage,
    pageContent,
    highlightPositions,
    isLoading,
    error,
    loadPDF,
    renderPage,
    searchText,
    setCurrentPage
  };
};
