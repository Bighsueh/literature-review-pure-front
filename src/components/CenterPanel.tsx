import React, { useEffect, useState, useCallback } from 'react';
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
  const [sentencesCount, setSentencesCount] = useState(0);
  const [isInitializing, setIsInitializing] = useState(true);
  const [isUnlocked, setIsUnlocked] = useState(false); // 一旦解鎖就永遠解鎖
  
  // 初始檢查論文和句子資料
  const initializeData = useCallback(async () => {
    setIsInitializing(true);
    try {
      console.log('🔍 初始化檢查論文和句子...');
      
      // 檢查完成的論文和句子資料
      const [hasCompleted, sentencesData] = await Promise.all([
        paperService.hasAnyCompletedPapers(),
        paperService.getAllSelectedPapersSentences()
      ]);
      
      console.log('📊 初始化結果:', {
        hasCompleted,
        totalSentences: sentencesData.totalSentences,
        totalPapers: sentencesData.totalPapers
      });
      
      const newSentencesCount = sentencesData.totalSentences;
      setSentencesCount(newSentencesCount);
      
      // 一旦有句子就永久解鎖
      if (newSentencesCount > 0) {
        setIsUnlocked(true);
        console.log('🎉 聊天功能已解鎖！');
      }
      
    } catch (error) {
      console.error('❌ 初始化檢查時出錯:', error);
      // 降級到檢查本地句子資料
      const localSentenceCount = sentences.length;
      setSentencesCount(localSentenceCount);
      if (localSentenceCount > 0) {
        setIsUnlocked(true);
      }
    } finally {
      setIsInitializing(false);
    }
  }, [sentences.length]);

  // 組件掛載時初始化
  useEffect(() => {
    initializeData();
  }, [initializeData]);

  // 監聽本地句子變化
  useEffect(() => {
    if (sentences.length > 0) {
      const newCount = sentences.length;
      if (newCount !== sentencesCount) {
        console.log('📝 本地句子資料變化:', newCount);
        setSentencesCount(newCount);
      }
      
      // 一旦有句子就解鎖
      if (!isUnlocked) {
        setIsUnlocked(true);
        console.log('🎉 聊天功能已解鎖（本地資料）！');
      }
    }
  }, [sentences.length, sentencesCount, isUnlocked]);

  // 監聽論文資料同步完成事件
  useEffect(() => {
    const handlePaperDataSynced = (event: CustomEvent) => {
      const { paperId, sentencesCount: newCount } = event.detail;
      console.log(`📥 Paper data synced for ${paperId}: ${newCount} sentences`);
      
      if (newCount !== sentencesCount) {
        setSentencesCount(newCount);
      }
      
      // 一旦有句子就解鎖
      if (newCount > 0 && !isUnlocked) {
        setIsUnlocked(true);
        console.log('🎉 聊天功能已解鎖（同步資料）！');
      }
    };

    window.addEventListener('paperDataSynced', handlePaperDataSynced as EventListener);
    
    return () => {
      window.removeEventListener('paperDataSynced', handlePaperDataSynced as EventListener);
    };
  }, [sentencesCount, isUnlocked]);

  // 手動刷新處理函數
  const handleRefresh = async () => {
    console.log('🔄 手動刷新');
    
    // 清除所有聊天記錄
    clearAllChats();
    
    // 重新初始化
    await initializeData();
  };

  // 生成占位符文字（只依賴sentencesCount和isUnlocked，減少重渲染）
  const getPlaceholder = () => {
    if (isInitializing) {
      return "正在檢查論文處理狀態...";
    }
    if (!isUnlocked) {
      return "請先上傳並完成論文處理";
    }
    return `輸入你的查詢... (已處理 ${sentencesCount} 個句子)`;
  };

  // 生成狀態顯示文字（只依賴sentencesCount和isUnlocked，減少重渲染）
  const getStatusText = () => {
    if (isInitializing) {
      return "檢查中...";
    }
    if (!isUnlocked) {
      return "等待論文處理完成";
    }
    return `已就緒 - ${sentencesCount} 個句子可用於查詢`;
  };

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b bg-white flex justify-between items-center">
        <div>
          <h2 className="text-lg font-medium text-gray-900">定義查詢助手</h2>
          <p className="text-sm text-gray-500">
            {getStatusText()}
            {isUnlocked && (
              <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                就緒
              </span>
            )}
          </p>
        </div>
        <button 
          onClick={handleRefresh}
          disabled={isInitializing}
          className="p-1 text-gray-500 hover:text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 rounded-md disabled:opacity-50"
          title="刷新對話狀態並檢查論文處理進度"
        >
          <ArrowPathIcon className={`h-5 w-5 ${isInitializing ? 'animate-spin' : ''}`} />
        </button>
      </div>
      
      <div className="flex-1 overflow-y-auto">
        <ChatMessageList onReferenceClick={onReferenceClick} />
      </div>
      
      <ChatInput 
        disabled={!isUnlocked}
        placeholder={getPlaceholder()}
      />
    </div>
  );
};

export default CenterPanel;
