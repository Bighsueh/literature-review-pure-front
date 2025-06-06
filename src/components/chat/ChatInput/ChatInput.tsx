import React, { useState, useRef, useEffect } from 'react';
import { 
  PaperAirplaneIcon, 
  ExclamationCircleIcon,
  ArrowPathIcon 
} from '@heroicons/react/24/solid';
import { useQueryProcessor } from '../../../hooks/useQueryProcessor';
import { useChatStore } from '../../../stores/chatStore';
import { useAppStore } from '../../../stores/appStore';

interface ChatInputProps {
  disabled?: boolean;
  placeholder?: string;
  onQueryStart?: () => void;
  onQueryComplete?: () => void;
}

const ChatInput: React.FC<ChatInputProps> = ({
  disabled = false,
  placeholder = '輸入查詢...',
  onQueryStart,
  onQueryComplete
}) => {
  const [query, setQuery] = useState('');
  const [isRetrying, setIsRetrying] = useState(false);
  const [lastError, setLastError] = useState<string | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const { processQuery } = useQueryProcessor();
  const { currentConversationId } = useChatStore();
  const { progress } = useAppStore();
  
  const isProcessing = progress.isProcessing;
  
  // 自動調整高度
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
      inputRef.current.style.height = `${inputRef.current.scrollHeight}px`;
    }
  }, [query]);
  
  // 清除錯誤當用戶開始輸入
  useEffect(() => {
    if (query.trim() && lastError) {
      setLastError(null);
    }
  }, [query, lastError]);
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!query.trim() || disabled || (isProcessing && !isRetrying)) {
      return;
    }
    
    const currentQuery = query.trim();
    
    try {
      setLastError(null);
      onQueryStart?.();
      
      await processQuery(currentQuery, currentConversationId || undefined);
      setQuery('');
      setIsRetrying(false);
      onQueryComplete?.();
    } catch (error) {
      console.error('Error processing query:', error);
      const errorMessage = error instanceof Error ? error.message : '查詢處理失敗，請重試';
      setLastError(errorMessage);
      setIsRetrying(false);
    }
  };
  
  const handleRetry = () => {
    if (lastError) {
      setIsRetrying(true);
      const fakeEvent = {
        preventDefault: () => {}
      } as React.FormEvent;
      handleSubmit(fakeEvent);
    }
  };
  
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  // 取得處理階段顯示文字
  const getProcessingStageText = () => {
    if (progress.currentStage) {
      switch (progress.currentStage) {
        case 'extracting':
          return '正在提取關鍵字...';
        case 'searching':
          return '正在搜尋相關章節...';
        case 'analyzing':
          return '正在分析內容...';
        case 'generating':
          return '正在生成回應...';
        case 'uploading':
          return '正在上傳檔案...';
        case 'saving':
          return '正在儲存結果...';
        default:
          return '正在處理查詢...';
      }
    }
    return '正在處理查詢...';
  };

  return (
    <div id="chat-input" className="border-t bg-white p-3">
      {/* 錯誤顯示 */}
      {lastError && (
        <div className="mb-3 flex items-center justify-between bg-red-50 border border-red-200 rounded-md p-3">
          <div className="flex items-center">
            <ExclamationCircleIcon className="h-5 w-5 text-red-500 mr-2" />
            <div>
              <p className="text-sm text-red-800">{lastError}</p>
              <p className="text-xs text-red-600 mt-1">請檢查網路連線或稍後重試</p>
            </div>
          </div>
          <button
            onClick={handleRetry}
            disabled={isProcessing}
            className="ml-3 flex items-center px-3 py-1 text-sm bg-red-100 text-red-700 rounded hover:bg-red-200 disabled:opacity-50"
          >
            <ArrowPathIcon className="h-4 w-4 mr-1" />
            重試
          </button>
        </div>
      )}
      
      <form onSubmit={handleSubmit} className="flex items-end">
        <textarea
          ref={inputRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={isProcessing ? '正在處理中...' : placeholder}
          disabled={disabled || (isProcessing && !isRetrying)}
          className={`flex-1 resize-none border rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent min-h-[40px] max-h-[120px] transition-colors ${
            disabled || isProcessing 
              ? 'bg-gray-100 cursor-not-allowed' 
              : 'bg-white'
          } ${lastError ? 'border-red-300' : 'border-gray-300'}`}
          rows={1}
        />
        <button
          type="submit"
          disabled={!query.trim() || disabled || (isProcessing && !isRetrying)}
          className={`ml-2 p-2 rounded-full transition-all duration-200 ${
            !query.trim() || disabled || (isProcessing && !isRetrying)
              ? 'bg-gray-300 cursor-not-allowed'
              : 'bg-blue-500 hover:bg-blue-600 hover:scale-105'
          } text-white`}
        >
          {isProcessing && !isRetrying ? (
            <ArrowPathIcon className="h-5 w-5 animate-spin" />
          ) : (
            <PaperAirplaneIcon className="h-5 w-5" />
          )}
        </button>
      </form>
      
      {/* 詳細載入狀態 */}
      {isProcessing && (
        <div className="mt-3 bg-blue-50 border border-blue-200 rounded-md p-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <div className="flex space-x-1 mr-3">
                <div className="h-2 w-2 rounded-full bg-blue-500 animate-bounce"></div>
                <div className="h-2 w-2 rounded-full bg-blue-500 animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                <div className="h-2 w-2 rounded-full bg-blue-500 animate-bounce" style={{ animationDelay: '0.2s' }}></div>
              </div>
              <span className="text-sm text-blue-800 font-medium">
                {getProcessingStageText()}
              </span>
            </div>
            
            {/* 進度條 */}
            {progress.percentage !== undefined && (
              <div className="flex items-center">
                <div className="w-20 bg-blue-200 rounded-full h-2 mr-2">
                  <div 
                    className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${progress.percentage}%` }}
                  ></div>
                </div>
                <span className="text-xs text-blue-600 font-mono">
                  {Math.round(progress.percentage)}%
                </span>
              </div>
            )}
          </div>
          
          {/* 處理時間提示 */}
          <div className="mt-2 text-xs text-blue-600">
            <p>多論文分析需要較長時間，預計 30-60 秒</p>
          </div>
        </div>
      )}
      
      {/* 使用提示 */}
      {!isProcessing && !lastError && query.length === 0 && (
        <div className="mt-2 text-xs text-gray-500">
          <p>💡 提示：您可以詢問論文中的定義、方法、結果比較等問題</p>
        </div>
      )}
    </div>
  );
};

export default ChatInput;
