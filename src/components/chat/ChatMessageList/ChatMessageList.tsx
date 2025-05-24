import React, { useEffect, useRef } from 'react';
import { useChatStore } from '../../../stores/chatStore';
import { useAppStore } from '../../../stores/appStore';
import MessageBubble from '../MessageBubble/MessageBubble';
import { ProcessedSentence } from '../../../types/file';
import { Message } from '../../../types/chat';
import { ComputerDesktopIcon } from '@heroicons/react/24/outline';

interface ChatMessageListProps {
  onReferenceClick?: (sentence: ProcessedSentence) => void;
}

const ChatMessageList: React.FC<ChatMessageListProps> = ({ onReferenceClick }) => {
  // 直接使用 store hook，不使用選擇器函數
  const { conversations, currentConversationId, updateConversation } = useChatStore();
  const { setSelectedReferences } = useAppStore();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  // 取得當前對話
  const currentConversation = currentConversationId 
    ? conversations.find(conv => conv.id === currentConversationId) 
    : null;
  
  // 打印調試信息
  useEffect(() => {
    if (currentConversation) {
      console.log('Current conversation ID:', currentConversationId);
      console.log('Current conversation:', currentConversation);
      console.log('Messages count:', currentConversation.messages.length);
      console.log('Messages:', currentConversation.messages);
    } else {
      console.log('No current conversation found');
      console.log('All conversations:', conversations);
      console.log('Current conversation ID:', currentConversationId);
    }
  }, [currentConversation, conversations, currentConversationId]);
  
  // 自動滾動到最新訊息
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [currentConversation?.messages]);
  
  const handleMessageReferenceClick = (messageId: string, referenceId: string) => {
    if (!currentConversation) return;
    
    const message = currentConversation.messages.find(msg => msg.id === messageId);
    if (!message || !message.references) return;
    
    const reference = message.references.find(ref => ref.id === referenceId);
    if (!reference) return;
    
    // 設置當前選中的引用句子，顯示在右側面板
    setSelectedReferences([reference]);
    
    // 回調通知父組件
    onReferenceClick?.(reference);
  };

  // 创建默認的歡迎消息
  const createWelcomeMessage = (): Message => ({
    id: 'welcome',
    type: 'system',
    content: '歡迎使用定義查詢助手！\n\n我可以幫助您在學術論文中查找定義。使用方法：\n1. 首先上傳您的 PDF 論文\n2. 等待檔案處理完成\n3. 在下方輸入框中輸入您的查詢，例如："什麼是技術接受模型？"',
    timestamp: new Date()
  });

  // 編譯歡迎消息 - 給所有對話均顯示
  const welcomeMessage = createWelcomeMessage();

  // 使用可視化的調試信息
  const debugInfo = process.env.NODE_ENV === 'development' ? (
    <div className="hidden bg-yellow-100 p-2 text-xs rounded mb-2">
      <div>Conversation ID: {currentConversationId || 'None'}</div>
      <div>Messages count: {currentConversation ? currentConversation.messages.length : 0}</div>
    </div>
  ) : null;
  
  // 格式化時間戳
  const formatTimestamp = (date: Date) => {
    return new Date(date).toLocaleTimeString('zh-TW', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const handleRefreshChat = () => {
    if (currentConversationId) {
      if (window.confirm('確定要清空當前對話記錄嗎？此操作無法復原。')) {
        updateConversation(currentConversationId, { messages: [] });
      }
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      <div className="flex justify-end mb-2">
        <button
          onClick={handleRefreshChat}
          className="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded-md text-gray-700 bg-gray-100 hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
          title="刷新聊天記錄"
        >
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="h-4 w-4 mr-1">
            <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
          </svg>
          刷新聊天記錄
        </button>
      </div>
      {debugInfo}
      
      {/* 歡迎消息始終顯示在頂部 */}
      <div className="flex justify-start mb-4">
        <div className="flex max-w-[80%]">
          <div className="flex-shrink-0 mr-2">
            <div className="h-8 w-8 rounded-full flex items-center justify-center bg-gray-200">
              <ComputerDesktopIcon className="h-5 w-5 text-gray-600" />
            </div>
          </div>
          <div className="rounded-lg px-4 py-2 shadow-sm bg-white text-gray-800 rounded-tl-none border border-gray-200">
            <p className="whitespace-pre-wrap">{welcomeMessage.content}</p>
            <div className="text-xs mt-1 flex justify-between items-center text-gray-500">
              <span>{formatTimestamp(welcomeMessage.timestamp)}</span>
            </div>
          </div>
        </div>
      </div>
      
      {/* 用戶對話或提示文本 */}
      {currentConversation && currentConversation.messages.length > 0 ? (
        currentConversation.messages.map((message) => (
          <MessageBubble
            key={message.id}
            message={message}
            onReferenceClick={(refId) => handleMessageReferenceClick(message.id, refId)}
          />
        ))
      ) : (
        <div className="text-center text-gray-500 my-4 mt-2 border-t pt-4">
          開始新對話，請在下方輸入框中輸入您的查詢
        </div>
      )}
      
      <div ref={messagesEndRef} />
    </div>
  );
};

export default ChatMessageList;
