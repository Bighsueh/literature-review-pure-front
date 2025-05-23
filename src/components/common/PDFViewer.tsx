// src/components/common/PDFViewer.tsx
import React, { useState, useEffect } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/esm/Page/AnnotationLayer.css';
import 'react-pdf/dist/esm/Page/TextLayer.css';

// Configure PDF.js worker
// Using absolute path to PDF worker in the public directory
pdfjs.GlobalWorkerOptions.workerSrc = '/pdf.worker.js';

interface PDFViewerProps {
  file: File | Blob | null; // PDF file blob or File object
  pageNumber?: number;
  onDocumentLoadSuccess?: ({ numPages }: { numPages: number }) => void;
  onDocumentLoadError?: (error: Error) => void;
}

const PDFViewer: React.FC<PDFViewerProps> = ({ 
  file,
  pageNumber = 1,
  onDocumentLoadSuccess,
  onDocumentLoadError 
}) => {
  const [numPages, setNumPages] = useState<number | null>(null);
  const [internalPageNumber, setInternalPageNumber] = useState<number>(pageNumber);
  const [documentError, setDocumentError] = useState<Error | null>(null);

  useEffect(() => {
    setInternalPageNumber(pageNumber);
  }, [pageNumber]);

  function handleDocumentLoadSuccess({ numPages: nextNumPages }: { numPages: number }) {
    setNumPages(nextNumPages);
    setDocumentError(null);
    if (onDocumentLoadSuccess) {
      onDocumentLoadSuccess({ numPages: nextNumPages });
    }
  }

  function handleDocumentLoadError(error: Error) {
    console.error('Failed to load PDF document:', error);
    setDocumentError(error);
    if (onDocumentLoadError) {
      onDocumentLoadError(error);
    }
  }

  if (!file) {
    return <div className="p-4 text-center text-gray-500">No PDF file provided.</div>;
  }

  return (
    <div className="pdf-viewer-container w-full h-full overflow-auto">
      {documentError ? (
        <div className="p-4 text-center text-red-500">
          <p>Error loading PDF: {documentError.message}</p>
          <p>Please ensure the PDF worker is correctly configured and accessible.</p>
        </div>
      ) : (
        <Document
          file={file}
          onLoadSuccess={handleDocumentLoadSuccess}
          onLoadError={handleDocumentLoadError}
          options={{
            cMapUrl: `https://unpkg.com/pdfjs-dist@${pdfjs.version}/cmaps/`,
            cMapPacked: true,
            standardFontDataUrl: `https://unpkg.com/pdfjs-dist@${pdfjs.version}/standard_fonts/`
          }}
          className="flex justify-center"
        >
          {numPages !== null && (
            <Page 
              pageNumber={internalPageNumber} 
              renderTextLayer={true}
              renderAnnotationLayer={true}
              width={Math.min(window.innerWidth * 0.8, 800)} // Adjust width as needed
            />
          )}
        </Document>
      )}
      {numPages && (
        <div className="p-2 text-center text-sm text-gray-700">
          Page {internalPageNumber} of {numPages}
        </div>
      )}
    </div>
  );
};

export default PDFViewer;
