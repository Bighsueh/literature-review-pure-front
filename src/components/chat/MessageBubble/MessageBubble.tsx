import React, { useState } from 'react';
import { Message, Reference } from '../../../types/chat';
import { UserIcon } from '@heroicons/react/24/solid';
import { 
  ComputerDesktopIcon, 
  DocumentTextIcon, 
  InformationCircleIcon,
  ChevronDownIcon,
  ChevronUpIcon
} from '@heroicons/react/24/outline';
import { useAppStore } from '../../../stores/appStore';
import SourceSummary from '../SourceSummary/SourceSummary';

interface MessageBubbleProps {
  message: Message;
  onReferenceClick?: (referenceId: string) => void;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({
  message,
  onReferenceClick
}) => {
  const [showReferences, setShowReferences] = useState(false);
  const [showSourceSummary, setShowSourceSummary] = useState(false);
  const { setSelectedMessage, selectedMessage } = useAppStore();

  // 處理系統回答點擊事件
  const handleMessageClick = () => {
    if (message.type === 'system') {
      setSelectedMessage(message);
    }
  };

  // 檢查是否為當前選中的訊息
  const isSelected = selectedMessage?.id === message.id;

  const formatTimestamp = (date: Date) => {
    return new Date(date).toLocaleTimeString('zh-TW', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // 渲染引用按鈕的詳細資訊
  const renderReferenceTooltip = (reference: Reference) => {
    const fileName = reference.paper_name || reference.file_name || '未知檔案';
    const section = reference.section_type || reference.section || '未知章節';
    const content = reference.content_snippet || reference.sentence || '無內容預覽';
    
    return (
      <div className="absolute z-10 bottom-full left-0 mb-2 p-3 bg-black text-white text-xs rounded-lg shadow-lg max-w-xs">
        <div className="font-medium mb-1">{fileName}</div>
        <div className="text-gray-300 mb-1">{section} - 第 {reference.page_num} 頁</div>
        {reference.type && (
          <div className="text-blue-300 mb-1">類型: {reference.type}</div>
        )}
        <div className="text-gray-200">{content.substring(0, 100)}...</div>
      </div>
    );
  };

  // 更新的引用內容渲染
  const renderContentWithReferences = () => {
    const refRegex = /\[\[ref:([a-zA-Z0-9-_]+)\]\]/g;
    const parts = message.content.split(refRegex);
    
    if (parts.length <= 1) {
      return <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>;
    }
    
    const result: React.ReactNode[] = [];
    for (let i = 0; i < parts.length; i++) {
      if (i % 2 === 0) {
        // 文字部分
        result.push(<span key={`text-${i}`}>{parts[i]}</span>);
      } else {
        // 引用 ID
        const refId = parts[i];
        const reference = message.references?.find(ref => ref.id === refId);
        
        result.push(
          <span key={`ref-${refId}`} className="relative inline-block group">
            <button
              className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 mx-0.5 hover:bg-blue-200 transition-colors"
              onClick={(e) => {
                e.stopPropagation(); // 防止觸發父層點擊事件
                onReferenceClick?.(refId);
              }}
            >
              <DocumentTextIcon className="h-3 w-3 mr-1" />
              引用 #{refId.substring(0, 6)}
            </button>
            {reference && (
              <div className="hidden group-hover:block">
                {renderReferenceTooltip(reference)}
              </div>
            )}
          </span>
        );
      }
    }
    
    return <div className="whitespace-pre-wrap leading-relaxed">{result}</div>;
  };

  // 渲染載入狀態
  const renderLoadingState = () => {
    if (!message.metadata?.loading) return null;
    
    return (
      <div className="mt-2 flex items-center space-x-2">
        <div className="flex space-x-1">
          <div className="h-2 w-2 bg-blue-400 rounded-full animate-bounce"></div>
          <div className="h-2 w-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
          <div className="h-2 w-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
        </div>
        <span className="text-xs text-blue-600">
          {message.metadata.analysis_focus ? `正在進行${message.metadata.analysis_focus}分析...` : '正在分析...'}
        </span>
      </div>
    );
  };

  return (
    <div className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'} mb-4`}>
      <div className={`flex max-w-[85%] ${message.type === 'user' ? 'flex-row-reverse' : ''}`}>
        <div className={`flex-shrink-0 ${message.type === 'user' ? 'ml-3' : 'mr-3'}`}>
          <div className={`h-8 w-8 rounded-full flex items-center justify-center ${message.type === 'user' ? 'bg-blue-500' : 'bg-gray-200'}`}>
            {message.type === 'user' 
              ? <UserIcon className="h-5 w-5 text-white" />
              : <ComputerDesktopIcon className="h-5 w-5 text-gray-600" />
            }
          </div>
        </div>
        
        <div 
          className={`rounded-lg px-4 py-3 shadow-sm transition-all duration-200 ${
            message.type === 'user' 
              ? 'bg-blue-500 text-white rounded-tr-none' 
              : `bg-white text-gray-800 rounded-tl-none border-2 ${
                  isSelected 
                    ? 'border-blue-500 shadow-lg' 
                    : 'border-gray-200 hover:border-blue-300'
                } ${message.type === 'system' ? 'cursor-pointer' : ''}`
          }`}
          onClick={handleMessageClick}
        >
          {/* 選中狀態提示 */}
          {isSelected && message.type === 'system' && (
            <div className="mb-2 flex items-center text-xs text-blue-600">
              <InformationCircleIcon className="h-3 w-3 mr-1" />
              <span>已選中此回答 - 查看右側面板了解AI策略</span>
            </div>
          )}

          {/* 主要內容 */}
          {renderContentWithReferences()}
          
          {/* 載入狀態 */}
          {renderLoadingState()}
          
          {/* 時間戳和基本資訊 */}
          <div className={`text-xs mt-2 flex justify-between items-center ${message.type === 'user' ? 'text-blue-200' : 'text-gray-500'}`}>
            <span>{formatTimestamp(message.timestamp)}</span>
            
            {/* 關鍵字 */}
            {message.metadata?.keywords && message.type === 'system' && (
              <div className="flex flex-wrap gap-1 ml-2">
                {message.metadata.keywords.slice(0, 3).map((keyword, index) => (
                  <span 
                    key={index} 
                    className="bg-gray-100 text-gray-800 text-xs px-1.5 py-0.5 rounded"
                  >
                    {keyword}
                  </span>
                ))}
              </div>
            )}
          </div>
          
          {/* 錯誤狀態 */}
          {message.metadata?.error && (
            <div className="mt-2 text-xs text-red-600 bg-red-50 px-2 py-1 rounded">
              <InformationCircleIcon className="h-3 w-3 inline mr-1" />
              {typeof message.metadata.error === 'string' ? message.metadata.error : '處理過程中發生錯誤'}
            </div>
          )}
          
          {/* 引用列表展開按鈕 */}
          {message.references && message.references.length > 0 && (
            <div className="mt-2">
              <button
                onClick={(e) => {
                  e.stopPropagation(); // 防止觸發父層點擊事件
                  setShowReferences(!showReferences);
                }}
                className={`text-xs flex items-center ${message.type === 'user' ? 'text-blue-200 hover:text-blue-100' : 'text-blue-600 hover:text-blue-800'}`}
              >
                <DocumentTextIcon className="h-3 w-3 mr-1" />
                <span>引用來源 ({message.references.length})</span>
                {showReferences ? (
                  <ChevronUpIcon className="h-3 w-3 ml-1" />
                ) : (
                  <ChevronDownIcon className="h-3 w-3 ml-1" />
                )}
              </button>
              
              {/* 引用列表 */}
              {showReferences && (
                <div className="mt-2 space-y-1">
                  {message.references.map((ref, index) => (
                    <div 
                      key={ref.id}
                      className={`text-xs p-2 rounded border cursor-pointer ${message.type === 'user' ? 'bg-blue-400 border-blue-300 hover:bg-blue-300' : 'bg-gray-50 border-gray-200 hover:bg-gray-100'}`}
                      onClick={(e) => {
                        e.stopPropagation(); // 防止觸發父層點擊事件
                        onReferenceClick?.(ref.id);
                      }}
                    >
                      <div className="font-medium">
                        {ref.paper_name || ref.file_name || `引用 ${index + 1}`}
                      </div>
                      <div className={`${message.type === 'user' ? 'text-blue-100' : 'text-gray-600'}`}>
                        {ref.section_type || ref.section} • 第 {ref.page_num} 頁
                        {ref.type && <span> • {ref.type}</span>}
                      </div>
                      {(ref.content_snippet || ref.sentence) && (
                        <div className={`mt-1 ${message.type === 'user' ? 'text-blue-100' : 'text-gray-600'}`}>
                          {(ref.content_snippet || ref.sentence)!.substring(0, 80)}...
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
          
          {/* 來源摘要 */}
          {message.source_summary && message.type === 'system' && (
            <div className="mt-3">
              <button
                onClick={(e) => {
                  e.stopPropagation(); // 防止觸發父層點擊事件
                  setShowSourceSummary(!showSourceSummary);
                }}
                className="text-xs flex items-center text-blue-600 hover:text-blue-800"
              >
                <InformationCircleIcon className="h-3 w-3 mr-1" />
                <span>來源摘要</span>
                {showSourceSummary ? (
                  <ChevronUpIcon className="h-3 w-3 ml-1" />
                ) : (
                  <ChevronDownIcon className="h-3 w-3 ml-1" />
                )}
              </button>
              
              {showSourceSummary && (
                <div className="mt-2">
                  <SourceSummary sourceSummary={message.source_summary} />
                </div>
              )}
            </div>
          )}
          
          {/* 處理時間 */}
          {message.metadata?.processingTime && (
            <div className={`text-xs mt-1 ${message.type === 'user' ? 'text-blue-200' : 'text-gray-500'}`}>
              處理時間: {message.metadata.processingTime}ms
            </div>
          )}

          {/* 系統回答點擊提示 */}
          {message.type === 'system' && !isSelected && (
            <div className="mt-2 text-xs text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity">
              💡 點擊此回答查看AI策略詳情
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MessageBubble;
