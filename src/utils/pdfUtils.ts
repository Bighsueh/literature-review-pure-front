// utils/pdfUtils.ts
import * as pdfjs from 'pdfjs-dist';
import { TextPosition } from '../types/file';

// Ensure PDF.js worker is configured
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.mjs',
  import.meta.url
).toString();

/**
 * 從 Blob 或 URL 載入 PDF 文件
 */
export const loadPDFDocument = async (
  fileOrUrl: File | Blob | string
): Promise<pdfjs.PDFDocumentProxy> => {
  try {
    const loadingTask = typeof fileOrUrl === 'string'
      ? pdfjs.getDocument(fileOrUrl)
      : pdfjs.getDocument(new Uint8Array(await fileOrUrl.arrayBuffer()));
      
    return await loadingTask.promise;
  } catch (error) {
    console.error('Failed to load PDF:', error);
    throw new Error('Failed to load PDF document');
  }
};

/**
 * 從 PDF 頁面中提取文本內容
 */
export const extractTextFromPage = async (
  page: pdfjs.PDFPageProxy
): Promise<string> => {
  try {
    const textContent = await page.getTextContent();
    return textContent.items
      .map(item => 'str' in item ? item.str : '')
      .join(' ');
  } catch (error) {
    console.error('Failed to extract text from page:', error);
    return '';
  }
};

/**
 * 在 PDF 中搜尋文本
 */
export const searchTextInPDF = async (
  pdfDocument: pdfjs.PDFDocumentProxy,
  searchTerm: string
): Promise<{ pageIndex: number; positions: TextPosition[] }[]> => {
  const results: { pageIndex: number; positions: TextPosition[] }[] = [];
  
  for (let i = 1; i <= pdfDocument.numPages; i++) {
    const page = await pdfDocument.getPage(i);
    const textContent = await page.getTextContent();
    const pageText = textContent.items
      .map(item => 'str' in item ? item.str : '')
      .join(' ');
    
    if (pageText.toLowerCase().includes(searchTerm.toLowerCase())) {
      // 這裡是一個簡化的實現，實際上需要計算文本在頁面上的確切位置
      // 在完整實現中，我們需要使用 item.transform 和其他屬性來計算位置
      results.push({
        pageIndex: i - 1,
        positions: [{
          x: 0,
          y: 0,
          width: 100,
          height: 20
        }]
      });
    }
  }
  
  return results;
};

/**
 * 獲取 PDF 文件信息
 */
export const getPDFDocumentInfo = async (
  pdfDocument: pdfjs.PDFDocumentProxy
): Promise<{ numPages: number; title?: string; author?: string }> => {
  try {
    const metadata = await pdfDocument.getMetadata();
    const info = metadata.info as { Title?: string; Author?: string } || {};
    return {
      numPages: pdfDocument.numPages,
      title: info.Title,
      author: info.Author
    };
  } catch (error) {
    console.error('Failed to get PDF document info:', error);
    return { numPages: pdfDocument.numPages };
  }
};
