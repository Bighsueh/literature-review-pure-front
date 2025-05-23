import React, { useState } from 'react';
import ProgressDisplay from './progress/ProgressDisplay/ProgressDisplay';
import ReferencesPanel from './progress/ReferencesPanel/ReferencesPanel';
import { useAppStore } from '../stores/appStore';

interface RightPanelProps {
  onResize?: (newWidth: number) => void;
  onViewInPDF?: (sentenceId: string) => void;
}

const RightPanel: React.FC<RightPanelProps> = ({ onResize, onViewInPDF }) => {
  const [isResizing, setIsResizing] = useState(false);
  const { progress } = useAppStore();
  
  const handleResizeStart = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
    
    const handleResizeMove = (moveEvent: MouseEvent) => {
      if (onResize) {
        // 計算從右側往左的寬度
        const newWidth = Math.max(200, window.innerWidth - moveEvent.clientX);
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
        <h2 className="text-lg font-medium text-gray-900">處理進度 & 引用</h2>
      </div>
      
      {/* 進度顯示區域 */}
      <div className="p-4">
        <ProgressDisplay />
      </div>
      
      {/* 引用面板 */}
      <div className="flex-1 overflow-hidden">
        <ReferencesPanel onViewInPDF={onViewInPDF} />
      </div>
      
      {/* Resize handle */}
      <div
        className="absolute top-0 left-0 w-1 h-full bg-gray-300 cursor-ew-resize hover:bg-blue-500"
        onMouseDown={handleResizeStart}
      />
    </div>
  );
};

export default RightPanel;
