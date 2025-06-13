import React, { useEffect, useRef } from 'react';
import { useChatStore } from '../../../stores/chatStore';
import { useAppStore } from '../../../stores/appStore';
import MessageBubble from '../MessageBubble/MessageBubble';
import { ProcessedSentence } from '../../../types/file';
import { ComputerDesktopIcon, QuestionMarkCircleIcon } from '@heroicons/react/24/outline';
import { useFileStore } from '../../../stores/fileStore';
import { Reference } from '../../../types/chat';

interface ChatMessageListProps {
  onReferenceClick?: (sentence: ProcessedSentence) => void;
}

const WelcomeMessage = () => (
  <div className="bg-gray-50 p-6 rounded-lg shadow-sm border border-gray-200 m-4">
    <div className="flex items-start">
      <div className="flex-shrink-0 mr-4">
        <div className="h-10 w-10 rounded-full flex items-center justify-center bg-gray-200">
          <ComputerDesktopIcon className="h-6 w-6 text-gray-600" />
        </div>
      </div>
      <div>
        <h3 className="text-lg font-semibold text-gray-800">歡迎使用定義查詢助手！</h3>
        <p className="mt-1 text-sm text-gray-600">
          我是您的學術論文定義查找助手，可以幫助您快速找到並理解論文中的重要概念。
        </p>
      </div>
    </div>

    <div className="mt-6">
      <h4 className="font-semibold text-gray-700 text-sm">📋 使用步驟：</h4>
      <ol className="mt-2 list-decimal list-inside text-sm text-gray-600 space-y-2">
        <li>首先上傳您的英文論文 PDF 檔案</li>
        <li>在右側面板觀察檔案處理進度 (通常需要 1-3 分鐘)</li>
        <li>處理完成後，在下方輸入框中輸入您想要查詢的名詞</li>
      </ol>
    </div>

    <div className="mt-6">
      <h4 className="font-semibold text-gray-700 text-sm">💡 查詢範例：</h4>
      <ul className="mt-2 list-disc list-inside text-sm text-gray-600 space-y-1">
        <li>"什麼是 Adaptive Expertise?"</li>
        <li>"Machine Learning 的定義是什麼？"</li>
        <li>"請解釋 Deep Learning"</li>
      </ul>
    </div>
    
    <div className="mt-6 text-sm text-gray-600">
      <p>🔍 系統會自動找到相關定義並提供詳細解釋，包含原文引用和上下文資訊。</p>
    </div>

    <div className="mt-6 border-t pt-4 flex items-center text-sm text-gray-500">
      <QuestionMarkCircleIcon className="h-5 w-5 mr-2"/>
      <span>需要詳細教學嗎？點擊右下角的幫助按鈕開始引導！</span>
    </div>
  </div>
);

const ChatMessageList: React.FC<ChatMessageListProps> = ({ onReferenceClick }) => {
  const { conversations, currentConversationId } = useChatStore();
  const { setSelectedReferences } = useAppStore();
  const { files } = useFileStore();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const currentConversation = currentConversationId 
    ? conversations.find(conv => conv.id === currentConversationId) 
    : null;
  
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [currentConversation?.messages]);
  
  const mapReferenceToProcessedSentence = (ref: Reference): ProcessedSentence | null => {
    const file = files.find(f => f.name === ref.file_name);
    if (!file) return null;

    return {
      id: ref.id,
      content: ref.sentence || ref.content_snippet || '',
      type: (ref.type === 'OD' || ref.type === 'CD') ? ref.type : 'OTHER',
      reason: '', // Not available in Reference
      fileId: file.id,
      pageNumber: ref.page_num,
      fileName: file.name,
    };
  };
  
  const handleMessageReferenceClick = (messageId: string, referenceId: string) => {
    if (!currentConversation) return;
    
    const message = currentConversation.messages.find(msg => msg.id === messageId);
    if (!message || !message.references) return;
    
    const reference = message.references.find(ref => ref.id === referenceId);
    if (!reference) return;
    
    const processedSentence = mapReferenceToProcessedSentence(reference);
    if (!processedSentence) return;

    setSelectedReferences([processedSentence]);
    onReferenceClick?.(processedSentence);
  };

  return (
    <div id="chat-messages" className="flex-1 overflow-y-auto bg-white">
      {currentConversation && currentConversation.messages.length > 0 ? (
        <div className="p-4 space-y-4">
          {currentConversation.messages.map((message) => (
            <MessageBubble
              key={message.id}
              message={message}
              onReferenceClick={(refId) => handleMessageReferenceClick(message.id, refId)}
            />
          ))}
        </div>
      ) : (
        <WelcomeMessage />
      )}
      <div ref={messagesEndRef} />
    </div>
  );
};

export default ChatMessageList;
