import React from 'react';
import { useAppStore } from '../stores/appStore';
import StrategyDisplay from './RightPanel/StrategyDisplay';

interface RightPanelProps {
  onResize?: (newWidth: number) => void;
}

const RightPanel: React.FC<RightPanelProps> = ({ onResize }) => {
  const { selectedMessage } = useAppStore();

  const handleResizeStart = (e: React.MouseEvent) => {
    e.preventDefault();
    
    const handleResizeMove = (moveEvent: MouseEvent) => {
      if (onResize) {
        // 計算從右側往左的寬度
        const newWidth = Math.max(200, window.innerWidth - moveEvent.clientX);
        onResize(newWidth);
      }
    };
    
    const handleResizeEnd = () => {
      document.removeEventListener('mousemove', handleResizeMove);
      document.removeEventListener('mouseup', handleResizeEnd);
    };
    
    document.addEventListener('mousemove', handleResizeMove);
    document.addEventListener('mouseup', handleResizeEnd);
  };
  
  return (
    <div id="strategy-panel" className="flex flex-col h-full relative bg-gray-50">
      <div className="p-4 border-b bg-white">
        <h2 className="text-lg font-medium text-gray-900">AI 策略 & 引用詳情</h2>
        <p className="text-sm text-gray-600 mt-1">
          {selectedMessage 
            ? '顯示所選回答的分析策略和引用詳情' 
            : '點擊系統回答以查看詳情'
          }
        </p>
      </div>
      
      {/* 策略顯示區域 - 替換原有的進度顯示 */}
      <div className="flex-1 overflow-hidden">
        <div className="h-full overflow-y-auto">
          <StrategyDisplay 
            selectedMessage={selectedMessage}
            visible={true}
          />
        </div>
      </div>
      
      {/* Resize handle */}
      <div
        className="absolute top-0 left-0 w-1 h-full bg-gray-300 cursor-ew-resize hover:bg-blue-500 transition-colors"
        onMouseDown={handleResizeStart}
      />
    </div>
  );
};

export default RightPanel;
