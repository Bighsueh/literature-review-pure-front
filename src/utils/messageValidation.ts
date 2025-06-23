import { Message, Reference, SourceSummary, StrategyInfo, MessageMetadata } from '../types/chat';
import { v4 as uuidv4 } from 'uuid';

/**
 * 驗證訊息物件的完整性
 */
export const validateMessage = (message: unknown): message is Message => {
  if (!message || typeof message !== 'object') {
    return false;
  }
  
  const msg = message as Record<string, unknown>;
  return (
    typeof msg.id === 'string' &&
    typeof msg.type === 'string' &&
    ['user', 'system'].includes(msg.type) &&
    (msg.content === undefined || typeof msg.content === 'string') &&
    (msg.timestamp instanceof Date || typeof msg.timestamp === 'string')
  );
};

/**
 * 清理和標準化訊息內容
 */
export const sanitizeMessageContent = (content: unknown): string => {
  if (content === null || content === undefined) {
    return '';
  }
  
  if (typeof content === 'string') {
    return content.trim();
  }
  
  // 嘗試轉換其他類型為字符串
  try {
    const stringified = String(content);
    return stringified === '[object Object]' ? '' : stringified;
  } catch {
    return '';
  }
};

/**
 * 安全的訊息建構函數
 */
export const createMessage = (
  type: 'user' | 'system',
  content: any,
  options: Partial<Message> = {}
): Message => {
  const sanitizedContent = sanitizeMessageContent(content);
  
  return {
    id: options.id || uuidv4(),
    type,
    content: sanitizedContent,
    timestamp: options.timestamp || new Date(),
    references: Array.isArray(options.references) ? options.references : undefined,
    source_summary: options.source_summary || undefined,
    strategy_info: options.strategy_info || undefined,
    metadata: options.metadata || undefined
  };
};

/**
 * 安全的系統回應訊息建構函數
 */
export const createSystemMessage = (
  response: any,
  options: {
    references?: Reference[];
    source_summary?: SourceSummary;
    strategy_info?: StrategyInfo;
    metadata?: MessageMetadata;
    query?: string;
  } = {}
): Message => {
  const content = sanitizeMessageContent(response) || '系統未返回有效回應內容';
  
  return createMessage('system', content, {
    references: options.references,
    source_summary: options.source_summary,
    strategy_info: options.strategy_info,
    metadata: {
      query: options.query,
      ...options.metadata
    }
  });
};

/**
 * 安全的錯誤訊息建構函數
 */
export const createErrorMessage = (
  error: any,
  context?: string
): Message => {
  let errorContent = '';
  
  if (typeof error === 'string') {
    errorContent = error;
  } else if (error instanceof Error) {
    errorContent = error.message;
  } else {
    errorContent = '發生未知錯誤';
  }
  
  const finalContent = context 
    ? `${context}: ${errorContent}` 
    : errorContent;
  
  return createMessage('system', finalContent, {
    metadata: { 
      error: true,
      errorType: error?.constructor?.name || 'UnknownError'
    }
  });
};

/**
 * 修復現有訊息物件
 */
export const repairMessage = (message: any): Message => {
  if (validateMessage(message)) {
    // 如果訊息已經有效，只需要確保 content 不為 undefined
    return {
      ...message,
      content: sanitizeMessageContent(message.content),
      timestamp: message.timestamp instanceof Date ? message.timestamp : new Date(message.timestamp)
    };
  }
  
  // 如果訊息無效，嘗試修復
  return createMessage(
    message?.type === 'user' ? 'user' : 'system',
    message?.content,
    {
      id: message?.id,
      timestamp: message?.timestamp ? new Date(message.timestamp) : new Date(),
      references: message?.references,
      source_summary: message?.source_summary,
      strategy_info: message?.strategy_info,
      metadata: message?.metadata
    }
  );
}; 