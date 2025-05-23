import React from 'react';
import ChatMessageList from './chat/ChatMessageList/ChatMessageList';
import ChatInput from './chat/ChatInput/ChatInput';
import { ProcessedSentence } from '../types/file';
import { useFileStore } from '../stores/fileStore';

interface CenterPanelProps {
  onReferenceClick?: (sentence: ProcessedSentence) => void;
}

const CenterPanel: React.FC<CenterPanelProps> = ({ onReferenceClick }) => {
  const { sentences } = useFileStore();
  const hasFiles = sentences.length > 0;
  
  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b bg-white">
        <h2 className="text-lg font-medium text-gray-900">定義查詢助手</h2>
      </div>
      
      <div className="flex-1 overflow-hidden">
        <ChatMessageList onReferenceClick={onReferenceClick} />
      </div>
      
      <ChatInput 
        disabled={!hasFiles}
        placeholder={hasFiles ? "輸入你的查詢..." : "請先上傳並處理 PDF 檔案"}
      />
    </div>
  );
};

export default CenterPanel;
