import React, { useState, useRef, useEffect } from 'react';
import { 
  PaperAirplaneIcon, 
  ExclamationCircleIcon,
  ArrowPathIcon,
  ChevronDownIcon
} from '@heroicons/react/24/solid';
import { useQueryProcessor } from '../../hooks/useQueryProcessor';
import { useResponsive, useVirtualKeyboard } from '../../hooks/useResponsive';
import { useChatStore } from '../../stores/chatStore';
import { useAppStore } from '../../stores/appStore';

interface ResponsiveChatInputProps {
  disabled?: boolean;
  placeholder?: string;
  onQueryStart?: () => void;
  onQueryComplete?: () => void;
  className?: string;
}

const ResponsiveChatInput: React.FC<ResponsiveChatInputProps> = ({
  disabled = false,
  placeholder = '輸入查詢...',
  onQueryStart,
  onQueryComplete,
  className = ""
}) => {
  const [query, setQuery] = useState('');
  const [isRetrying, setIsRetrying] = useState(false);
  const [lastError, setLastError] = useState<string | null>(null);
  const [isInputFocused, setIsInputFocused] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  
  const { processQuery } = useQueryProcessor();
  const { currentConversationId } = useChatStore();
  const { progress } = useAppStore();
  const { isMobile } = useResponsive();
  const { isVirtualKeyboardOpen, keyboardHeight } = useVirtualKeyboard();
  
  const isProcessing = progress.isProcessing;
  
  // 動態計算輸入區域高度
  const getInputHeight = () => {
    if (isMobile) {
      if (isVirtualKeyboardOpen) {
        return 'auto';
      }
      return isExpanded ? '120px' : '44px';
    }
    return 'auto';
  };

  // 自動調整 textarea 高度
  useEffect(() => {
    if (inputRef.current && !isMobile) {
      inputRef.current.style.height = 'auto';
      inputRef.current.style.height = `${Math.min(inputRef.current.scrollHeight, 120)}px`;
    }
  }, [query, isMobile]);

  // 處理虛擬鍵盤開啟時的容器位置調整
  useEffect(() => {
    if (isMobile && isVirtualKeyboardOpen && containerRef.current) {
      const container = containerRef.current;
      const containerHeight = container.offsetHeight;
      const viewportHeight = window.innerHeight;
      const availableHeight = viewportHeight - keyboardHeight;
      
      // 確保輸入框在可視區域內
      const containerTop = container.getBoundingClientRect().top;
      if (containerTop + containerHeight > availableHeight) {
        container.style.position = 'fixed';
        container.style.bottom = `${keyboardHeight + 8}px`;
        container.style.left = '16px';
        container.style.right = '16px';
        container.style.zIndex = '50';
      } else {
        container.style.position = '';
        container.style.bottom = '';
        container.style.left = '';
        container.style.right = '';
        container.style.zIndex = '';
      }
    }
  }, [isMobile, isVirtualKeyboardOpen, keyboardHeight]);

  // 清除錯誤
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
      setIsExpanded(false);
      
      // 移動裝置上提交後失去焦點
      if (isMobile && inputRef.current) {
        inputRef.current.blur();
      }
      
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

  const handleFocus = () => {
    setIsInputFocused(true);
    if (isMobile) {
      setIsExpanded(true);
    }
  };

  const handleBlur = () => {
    setIsInputFocused(false);
    // 延遲收合以避免點擊按鈕時立即收合
    setTimeout(() => {
      if (!query.trim() && isMobile) {
        setIsExpanded(false);
      }
    }, 200);
  };

  // 切換展開狀態
  const toggleExpanded = () => {
    setIsExpanded(!isExpanded);
    if (!isExpanded && inputRef.current) {
      inputRef.current.focus();
    }
  };

  // 獲取處理階段顯示文字
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

  // 渲染錯誤提示
  const renderError = () => {
    if (!lastError) return null;
    
    return (
      <div className={`mb-3 flex ${isMobile ? 'flex-col space-y-2' : 'items-center justify-between'} bg-red-50 border border-red-200 rounded-md p-3`}>
        <div className="flex items-center">
          <ExclamationCircleIcon className="h-5 w-5 text-red-500 mr-2 flex-shrink-0" />
          <div className="flex-1">
            <p className="text-sm text-red-800 break-words">{lastError}</p>
            <p className="text-xs text-red-600 mt-1">請檢查網路連線或稍後重試</p>
          </div>
        </div>
        <button
          onClick={handleRetry}
          disabled={isProcessing}
          className={`flex items-center px-3 py-1 text-sm bg-red-100 text-red-700 rounded hover:bg-red-200 disabled:opacity-50 ${isMobile ? 'self-end' : 'ml-3'} min-h-[32px] min-w-[60px] justify-center`}
        >
          <ArrowPathIcon className="h-4 w-4 mr-1" />
          重試
        </button>
      </div>
    );
  };

  // 渲染處理狀態
  const renderProcessingStatus = () => {
    if (!isProcessing) return null;
    
    return (
      <div className="mt-3 bg-blue-50 border border-blue-200 rounded-md p-3">
        <div className={`flex items-center ${isMobile ? 'flex-col space-y-2' : 'justify-between'}`}>
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
              <div className={`${isMobile ? 'w-32' : 'w-20'} bg-blue-200 rounded-full h-2 mr-2`}>
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
        

      </div>
    );
  };

  return (
    <div 
      ref={containerRef}
      className={`border-t bg-white transition-all duration-300 ${className} ${
        isMobile ? 'px-4 py-3' : 'p-3'
      } ${isVirtualKeyboardOpen && isMobile ? 'shadow-lg' : ''}`}
      style={{
        paddingBottom: isMobile && isVirtualKeyboardOpen ? '8px' : undefined
      }}
    >
      {renderError()}
      
      <form onSubmit={handleSubmit} className="flex items-end space-x-2">
        <div className="flex-1 relative">
          <textarea
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={handleFocus}
            onBlur={handleBlur}
            placeholder={isProcessing ? '正在處理中...' : placeholder}
            disabled={disabled || (isProcessing && !isRetrying)}
            className={`w-full resize-none border rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 ${
              disabled || isProcessing 
                ? 'bg-gray-100 cursor-not-allowed' 
                : 'bg-white'
            } ${lastError ? 'border-red-300' : 'border-gray-300'} ${
              isMobile ? 'text-16px' : 'text-sm'
            }`}
            style={{
              height: getInputHeight(),
              maxHeight: isMobile ? '120px' : '120px',
              fontSize: isMobile ? '16px' : '14px' // 防止 iOS Safari 自動縮放
            }}
            rows={isMobile && !isExpanded ? 1 : undefined}
          />
          
          {/* 移動版展開/收合按鈕 */}
          {isMobile && query.length > 20 && (
            <button
              type="button"
              onClick={toggleExpanded}
              className="absolute right-2 top-2 p-1 text-gray-400 hover:text-gray-600 transition-colors"
            >
              <ChevronDownIcon 
                className={`h-4 w-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`} 
              />
            </button>
          )}
        </div>
        
        <button
          type="submit"
          disabled={!query.trim() || disabled || (isProcessing && !isRetrying)}
          className={`p-3 rounded-full transition-all duration-200 ${
            !query.trim() || disabled || (isProcessing && !isRetrying)
              ? 'bg-gray-300 cursor-not-allowed'
              : 'bg-blue-500 hover:bg-blue-600 active:scale-95'
          } text-white min-h-[48px] min-w-[48px] flex items-center justify-center touch-manipulation`}
          aria-label="發送訊息"
        >
          {isProcessing && !isRetrying ? (
            <ArrowPathIcon className="h-5 w-5 animate-spin" />
          ) : (
            <PaperAirplaneIcon className="h-5 w-5" />
          )}
        </button>
      </form>
      
      {renderProcessingStatus()}
      
      {/* 移動版鍵盤提示 */}
      {isMobile && isInputFocused && !isProcessing && (
        <div className="mt-2 text-xs text-gray-500 text-center">
          按 Enter 發送，Shift + Enter 換行
        </div>
      )}
    </div>
  );
};

export default ResponsiveChatInput; 