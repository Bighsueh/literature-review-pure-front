import React, { useEffect, useState } from 'react';
import ChatMessageList from './chat/ChatMessageList/ChatMessageList';
import ChatInput from './chat/ChatInput/ChatInput';
import { ProcessedSentence } from '../types/file';
import { useFileStore } from '../stores/fileStore';
import { useChatStore } from '../stores/chatStore';
import { paperService } from '../services/paper_service';
import { ArrowPathIcon } from '@heroicons/react/24/outline';

interface CenterPanelProps {
  onReferenceClick?: (sentence: ProcessedSentence) => void;
}

const CenterPanel: React.FC<CenterPanelProps> = ({ onReferenceClick }) => {
  const { sentences } = useFileStore();
  const { clearAllChats } = useChatStore();
  const [hasCompletedPapers, setHasCompletedPapers] = useState(false);
  const [isCheckingPapers, setIsCheckingPapers] = useState(true);
  const [sentencesCount, setSentencesCount] = useState(0);
  
  // 檢查是否有已完成處理的論文
  const checkCompletedPapers = async () => {
    setIsCheckingPapers(true);
    try {
      const hasCompleted = await paperService.hasAnyCompletedPapers();
      setHasCompletedPapers(hasCompleted);
      
      // 如果有已完成的論文，嘗試同步句子資料
      if (hasCompleted) {
        const sentencesData = await paperService.getAllSelectedPapersSentences();
        setSentencesCount(sentencesData.totalSentences);
      } else {
        setSentencesCount(0);
      }
    } catch (error) {
      console.error('Error checking completed papers:', error);
      // 降級到檢查本地句子資料
      setHasCompletedPapers(sentences.length > 0);
      setSentencesCount(sentences.length);
    } finally {
      setIsCheckingPapers(false);
    }
  };

  // 組件掛載時檢查狀態
  useEffect(() => {
    checkCompletedPapers();
  }, []);

  // 監聽本地句子變化作為備援
  useEffect(() => {
    if (!isCheckingPapers && !hasCompletedPapers && sentences.length > 0) {
      setHasCompletedPapers(true);
      setSentencesCount(sentences.length);
    }
  }, [sentences, isCheckingPapers, hasCompletedPapers]);

  // 監聽論文資料同步完成事件
  useEffect(() => {
    const handlePaperDataSynced = (event: CustomEvent) => {
      const { paperId, sentencesCount } = event.detail;
      console.log(`Paper data synced for ${paperId}: ${sentencesCount} sentences`);
      
      // 重新檢查論文狀態
      checkCompletedPapers();
    };

    window.addEventListener('paperDataSynced', handlePaperDataSynced as EventListener);
    
    return () => {
      window.removeEventListener('paperDataSynced', handlePaperDataSynced as EventListener);
    };
  }, []);

  const handleRefresh = async () => {
    // 清除所有聊天記錄（從 localStorage 和界面上）
    clearAllChats();
    
    // 重新檢查論文狀態
    await checkCompletedPapers();
  };

  // 決定是否啟用聊天輸入
  const isChatEnabled = hasCompletedPapers && sentencesCount > 0;
  
  // 生成占位符文字
  const getPlaceholder = () => {
    if (isCheckingPapers) {
      return "正在檢查論文處理狀態...";
    }
    if (!hasCompletedPapers) {
      return "請先上傳並完成論文處理";
    }
    if (sentencesCount === 0) {
      return "論文處理中，請稍候...";
    }
    return `輸入你的查詢... (已處理 ${sentencesCount} 個句子)`;
  };

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b bg-white flex justify-between items-center">
        <div>
          <h2 className="text-lg font-medium text-gray-900">定義查詢助手</h2>
          {!isCheckingPapers && (
            <p className="text-sm text-gray-500">
              {hasCompletedPapers 
                ? `已就緒 - ${sentencesCount} 個句子可用於查詢`
                : "等待論文處理完成"
              }
            </p>
          )}
        </div>
        <button 
          onClick={handleRefresh}
          disabled={isCheckingPapers}
          className="p-1 text-gray-500 hover:text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 rounded-md disabled:opacity-50"
          title="刷新對話狀態並檢查論文處理進度"
        >
          <ArrowPathIcon className={`h-5 w-5 ${isCheckingPapers ? 'animate-spin' : ''}`} />
        </button>
      </div>
      
      <div className="flex-1 overflow-y-auto">
        <ChatMessageList onReferenceClick={onReferenceClick} />
      </div>
      
      <ChatInput 
        disabled={!isChatEnabled || isCheckingPapers}
        placeholder={getPlaceholder()}
      />
    </div>
  );
};

export default CenterPanel;
