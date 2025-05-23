import React, { useState, useRef, useEffect } from 'react';
import { PaperAirplaneIcon } from '@heroicons/react/24/solid';
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
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!query.trim() || disabled || isProcessing) {
      return;
    }
    
    try {
      onQueryStart?.();
      await processQuery(query.trim(), currentConversationId || undefined);
      setQuery('');
      onQueryComplete?.();
    } catch (error) {
      console.error('Error processing query:', error);
    }
  };
  
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="border-t bg-white p-3">
      <form onSubmit={handleSubmit} className="flex items-end">
        <textarea
          ref={inputRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled || isProcessing}
          className="flex-1 resize-none border rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent min-h-[40px] max-h-[120px] disabled:bg-gray-100"
          rows={1}
        />
        <button
          type="submit"
          disabled={!query.trim() || disabled || isProcessing}
          className="ml-2 p-2 rounded-full bg-blue-500 text-white disabled:bg-gray-300 disabled:cursor-not-allowed hover:bg-blue-600 transition-colors"
        >
          <PaperAirplaneIcon className="h-5 w-5" />
        </button>
      </form>
      
      {isProcessing && (
        <div className="mt-2 text-xs text-gray-500 flex items-center">
          <div className="mr-2 h-3 w-3 rounded-full bg-blue-500 animate-pulse"></div>
          <span>正在處理查詢...</span>
        </div>
      )}
    </div>
  );
};

export default ChatInput;
