import React from 'react';
import ChatMessageList from './chat/ChatMessageList/ChatMessageList';
import ChatInput from './chat/ChatInput/ChatInput';
import { ProcessedSentence } from '../types/file';
import { useFileStore } from '../stores/fileStore';
import { useChatStore } from '../stores/chatStore';
import { ArrowPathIcon } from '@heroicons/react/24/outline';

interface CenterPanelProps {
  onReferenceClick?: (sentence: ProcessedSentence) => void;
}

const CenterPanel: React.FC<CenterPanelProps> = ({ onReferenceClick }) => {
  const { sentences } = useFileStore();
  const { resetStuckAssistantMessage } = useChatStore();
  const hasFiles = sentences.length > 0;

  const handleRefresh = () => {
    resetStuckAssistantMessage();
  };

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b bg-white flex justify-between items-center">
        <h2 className="text-lg font-medium text-gray-900">定義查詢助手</h2>
        <button 
          onClick={handleRefresh}
          className="p-1 text-gray-500 hover:text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 rounded-md"
          title="刷新對話狀態"
        >
          <ArrowPathIcon className="h-5 w-5" />
        </button>
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
