import React from 'react';
import { Message } from '../../../types/chat';
import { UserIcon } from '@heroicons/react/24/solid';
import { ComputerDesktopIcon } from '@heroicons/react/24/outline';

interface MessageBubbleProps {
  message: Message;
  onReferenceClick?: (referenceId: string) => void;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({
  message,
  onReferenceClick
}) => {
  const formatTimestamp = (date: Date) => {
    return new Date(date).toLocaleTimeString('zh-TW', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Split content by reference markers [[ref:id]] to highlight references
  const renderContentWithReferences = () => {
    // Simple regex to match reference patterns like [[ref:123]]
    const refRegex = /\[\[ref:([a-zA-Z0-9-]+)\]\]/g;
    const parts = message.content.split(refRegex);
    
    if (parts.length <= 1) {
      // No references found, return plain content
      return <p className="whitespace-pre-wrap">{message.content}</p>;
    }
    
    const result: React.ReactNode[] = [];
    for (let i = 0; i < parts.length; i++) {
      if (i % 2 === 0) {
        // Text part
        result.push(<span key={`text-${i}`}>{parts[i]}</span>);
      } else {
        // Reference ID
        const refId = parts[i];
        result.push(
          <button
            key={`ref-${refId}`}
            className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 mx-1 hover:bg-blue-200"
            onClick={() => onReferenceClick?.(refId)}
          >
            引用 #{refId.substring(0, 4)}
          </button>
        );
      }
    }
    
    return <p className="whitespace-pre-wrap">{result}</p>;
  };

  // 添加日誌以協助調試
  console.log('Rendering message bubble for:', message);

  return (
    <div className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'} mb-4`}>
      <div className={`flex max-w-[80%] ${message.type === 'user' ? 'flex-row-reverse' : ''}`}>
        <div className={`flex-shrink-0 ${message.type === 'user' ? 'ml-2' : 'mr-2'}`}>
          <div className={`h-8 w-8 rounded-full flex items-center justify-center ${message.type === 'user' ? 'bg-blue-500' : 'bg-gray-200'}`}>
            {message.type === 'user' 
              ? <UserIcon className="h-5 w-5 text-white" />
              : <ComputerDesktopIcon className="h-5 w-5 text-gray-600" />
            }
          </div>
        </div>
        
        <div className={`rounded-lg px-4 py-2 shadow-sm ${message.type === 'user' ? 'bg-blue-500 text-white rounded-tr-none' : 'bg-white text-gray-800 rounded-tl-none border border-gray-200'}`}>
          {renderContentWithReferences()}
          
          <div className={`text-xs mt-1 flex justify-between items-center ${message.type === 'user' ? 'text-blue-200' : 'text-gray-500'}`}>
            <span>{formatTimestamp(message.timestamp)}</span>
            
            {message.metadata?.keywords && message.type === 'system' && (
              <div className="ml-2">
                {message.metadata.keywords.slice(0, 3).map((keyword, index) => (
                  <span 
                    key={index} 
                    className="inline-block bg-gray-100 text-gray-800 text-xs px-1.5 py-0.5 rounded ml-1"
                  >
                    {keyword}
                  </span>
                ))}
              </div>
            )}
          </div>
          
          {message.references && message.references.length > 0 && (
            <div className={`text-xs mt-1 ${message.type === 'user' ? 'text-blue-200' : 'text-gray-500'}`}>
              <span>基於 {message.references.length} 個引用</span>
              {message.references.map(ref => (
                <button
                  key={ref.id}
                  onClick={() => onReferenceClick?.(ref.id)}
                  className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 mx-1 hover:bg-blue-200 ml-2"
                >
                  引用 #{ref.id.substring(0, 4)}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MessageBubble;
