import React, { useState } from 'react';
import FileUploadZone from './file/FileUploadZone/FileUploadZone';
import FileList from './file/FileList/FileList';

interface LeftPanelProps {
  onResize?: (newWidth: number) => void;
}

const LeftPanel: React.FC<LeftPanelProps> = ({ onResize }) => {
  const [isResizing, setIsResizing] = useState(false);
  
  const handleResizeStart = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
    
    const handleResizeMove = (moveEvent: MouseEvent) => {
      if (onResize) {
        // 限制最小寬度為 200px
        const newWidth = Math.max(200, moveEvent.clientX);
        onResize(newWidth);
      }
    };
    
    const handleResizeEnd = () => {
      setIsResizing(false);
      document.removeEventListener('mousemove', handleResizeMove);
      document.removeEventListener('mouseup', handleResizeEnd);
    };
    
    document.addEventListener('mousemove', handleResizeMove);
    document.addEventListener('mouseup', handleResizeEnd);
  };
  
  return (
    <div className="flex flex-col h-full relative">
      <div className="p-4 border-b">
        <h2 className="text-lg font-medium text-gray-900">檔案管理</h2>
      </div>
      
      <div className="p-4">
        <FileUploadZone />
      </div>
      
      <div className="flex-1 overflow-hidden">
        <FileList />
      </div>
      
      {/* Resize handle */}
      <div
        className="absolute top-0 right-0 w-1 h-full bg-gray-300 cursor-ew-resize hover:bg-blue-500"
        onMouseDown={handleResizeStart}
      />
    </div>
  );
};

export default LeftPanel;
