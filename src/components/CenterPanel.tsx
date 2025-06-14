import React, { useEffect, useState, useCallback, useRef } from 'react';
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
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const lastCheckRef = useRef<number>(0);
  
  // 檢查是否有已完成處理的論文和句子
  const checkCompletedPapers = useCallback(async (forceUpdate = false) => {
    // 避免頻繁檢查，至少間隔2秒
    const now = Date.now();
    if (!forceUpdate && now - lastCheckRef.current < 2000) {
      return;
    }
    lastCheckRef.current = now;
    
    setIsCheckingPapers(true);
    try {
      console.log('🔍 檢查已完成的論文和句子...');
      
      // 同時檢查完成的論文和句子資料
      const [hasCompleted, sentencesData] = await Promise.all([
        paperService.hasAnyCompletedPapers(),
        paperService.getAllSelectedPapersSentences()
      ]);
      
      console.log('📊 檢查結果:', {
        hasCompleted,
        totalSentences: sentencesData.totalSentences,
        totalPapers: sentencesData.totalPapers
      });
      
      // 更新狀態
      const newHasCompleted = hasCompleted || sentencesData.totalSentences > 0;
      const newSentencesCount = sentencesData.totalSentences;
      
      // 只有在狀態真正改變時才更新，避免不必要的重渲染
      if (newHasCompleted !== hasCompletedPapers || newSentencesCount !== sentencesCount) {
        setHasCompletedPapers(newHasCompleted);
        setSentencesCount(newSentencesCount);
        
        console.log('✅ 狀態更新:', {
          wasEnabled: hasCompletedPapers && sentencesCount > 0,
          nowEnabled: newHasCompleted && newSentencesCount > 0,
          sentencesChange: newSentencesCount - sentencesCount
        });
        
        // 如果聊天從不可用變為可用，發送通知
        if (!hasCompletedPapers && newHasCompleted && newSentencesCount > 0) {
          console.log('🎉 聊天功能已啟用！');
        }
      }
      
    } catch (error) {
      console.error('❌ 檢查已完成論文時出錯:', error);
      // 降級到檢查本地句子資料
      const localSentenceCount = sentences.length;
      if (localSentenceCount !== sentencesCount) {
        setHasCompletedPapers(localSentenceCount > 0);
        setSentencesCount(localSentenceCount);
      }
    } finally {
      setIsCheckingPapers(false);
    }
  }, [hasCompletedPapers, sentencesCount, sentences.length]);

  // 啟動定期檢查
  const startPeriodicCheck = useCallback(() => {
    // 清除舊的定時器
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }
    
    // 設置新的定時器，每5秒檢查一次
    intervalRef.current = setInterval(() => {
      checkCompletedPapers();
    }, 5000);
    
    console.log('🔄 啟動定期檢查 (每5秒)');
  }, [checkCompletedPapers]);

  // 停止定期檢查
  const stopPeriodicCheck = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
      console.log('⏹️ 停止定期檢查');
    }
  }, []);

  // 組件掛載時初始化
  useEffect(() => {
    checkCompletedPapers(true);
    startPeriodicCheck();
    
    return () => {
      stopPeriodicCheck();
    };
  }, [checkCompletedPapers, startPeriodicCheck, stopPeriodicCheck]);

  // 監聽本地句子變化作為即時更新
  useEffect(() => {
    if (sentences.length > 0 && sentences.length !== sentencesCount) {
      console.log('📝 本地句子資料變化:', sentences.length);
      setSentencesCount(sentences.length);
      setHasCompletedPapers(true);
    }
  }, [sentences.length, sentencesCount]);

  // 監聽論文資料同步完成事件
  useEffect(() => {
    const handlePaperDataSynced = (event: CustomEvent) => {
      const { paperId, sentencesCount: newCount } = event.detail;
      console.log(`📥 Paper data synced for ${paperId}: ${newCount} sentences`);
      
      // 立即檢查更新
      checkCompletedPapers(true);
    };

    // 監聽窗口焦點事件，當用戶回到頁面時檢查更新
    const handleFocus = () => {
      console.log('👁️ 頁面獲得焦點，檢查更新');
      checkCompletedPapers(true);
    };

    window.addEventListener('paperDataSynced', handlePaperDataSynced as EventListener);
    window.addEventListener('focus', handleFocus);
    
    return () => {
      window.removeEventListener('paperDataSynced', handlePaperDataSynced as EventListener);
      window.removeEventListener('focus', handleFocus);
    };
  }, [checkCompletedPapers]);

  // 手動刷新處理函數
  const handleRefresh = async () => {
    console.log('🔄 手動刷新');
    
    // 清除所有聊天記錄（從 localStorage 和界面上）
    clearAllChats();
    
    // 重新檢查論文狀態
    await checkCompletedPapers(true);
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

  // 生成狀態顯示文字
  const getStatusText = () => {
    if (isCheckingPapers) {
      return "檢查中...";
    }
    if (!hasCompletedPapers) {
      return "等待論文處理完成";
    }
    if (sentencesCount === 0) {
      return "論文處理中...";
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
            {isChatEnabled && (
              <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                就緒
              </span>
            )}
          </p>
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
