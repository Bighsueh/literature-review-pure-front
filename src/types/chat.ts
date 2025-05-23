// types/chat.ts
import { ProcessedSentence } from './file';

export interface Message {
  id: string;
  type: 'user' | 'system';
  content: string;
  timestamp: Date;
  references?: ProcessedSentence[];
  metadata?: MessageMetadata;
}

export interface MessageMetadata {
  query?: string;
  keywords?: string[];
  processingTime?: number;
  totalReferences?: number;
}

export interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
}
