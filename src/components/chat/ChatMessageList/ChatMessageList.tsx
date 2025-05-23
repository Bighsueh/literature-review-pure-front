import React, { useEffect, useRef } from 'react';
import { useChatStore } from '../../../stores/chatStore';
import { useAppStore } from '../../../stores/appStore';
import MessageBubble from '../MessageBubble/MessageBubble';
import { ProcessedSentence } from '../../../types/file';

interface ChatMessageListProps {
  onReferenceClick?: (sentence: ProcessedSentence) => void;
}

const ChatMessageList: React.FC<ChatMessageListProps> = ({ onReferenceClick }) => {
  const { conversations, currentConversationId } = useChatStore();
  const { setSelectedReferences } = useAppStore();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  const currentConversation = currentConversationId 
    ? conversations.find(conv => conv.id === currentConversationId) 
    : null;
  
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

  if (!currentConversation) {
    return (
      <div className="flex flex-col items-center justify-center h-full bg-gray-50 text-gray-500">
        <p>開始新對話</p>
        <p className="text-sm mt-2">上傳檔案並輸入查詢</p>
      </div>
    );
  }
  
  if (currentConversation.messages.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full bg-gray-50 text-gray-500">
        <p>尚無訊息</p>
        <p className="text-sm mt-2">輸入查詢以開始對話</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full p-4 overflow-y-auto bg-gray-50">
      {currentConversation.messages.map((message, index) => (
        <MessageBubble
          key={message.id}
          message={message}
          isLatest={index === currentConversation.messages.length - 1}
          onReferenceClick={(refId) => handleMessageReferenceClick(message.id, refId)}
        />
      ))}
      <div ref={messagesEndRef} />
    </div>
  );
};

export default ChatMessageList;
