// stores/chatStore.ts
import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { Conversation, Message } from '../types/chat';

interface ChatState {
  // 對話列表
  conversations: Conversation[];
  currentConversationId: string | null;
  
  // 動作
  addConversation: (conversation: Conversation) => void;
  updateConversation: (id: string, updates: Partial<Conversation>) => void;
  removeConversation: (id: string) => void;
  setCurrentConversation: (id: string | null) => void;
  
  addMessage: (conversationId: string, message: Message) => void;
  updateMessage: (conversationId: string, messageId: string, updates: Partial<Message>) => void;
  removeMessage: (conversationId: string, messageId: string) => void;
}

export const useChatStore = create<ChatState>()(
  devtools(
    persist(
      (set) => ({
        conversations: [],
        currentConversationId: null,
        
        addConversation: (conversation) => set((state) => ({
          conversations: [...state.conversations, conversation],
          currentConversationId: conversation.id
        })),
        
        updateConversation: (id, updates) => set((state) => ({
          conversations: state.conversations.map(conversation => 
            conversation.id === id ? { ...conversation, ...updates } : conversation
          )
        })),
        
        removeConversation: (id) => set((state) => ({
          conversations: state.conversations.filter(conversation => conversation.id !== id),
          currentConversationId: state.currentConversationId === id ? null : state.currentConversationId
        })),
        
        setCurrentConversation: (id) => set({
          currentConversationId: id
        }),
        
        addMessage: (conversationId, message) => set((state) => ({
          conversations: state.conversations.map(conversation => 
            conversation.id === conversationId 
              ? { 
                  ...conversation, 
                  messages: [...conversation.messages, message],
                  updatedAt: new Date()
                } 
              : conversation
          )
        })),
        
        updateMessage: (conversationId, messageId, updates) => set((state) => ({
          conversations: state.conversations.map(conversation => 
            conversation.id === conversationId 
              ? { 
                  ...conversation, 
                  messages: conversation.messages.map(message => 
                    message.id === messageId ? { ...message, ...updates } : message
                  ),
                  updatedAt: new Date()
                } 
              : conversation
          )
        })),
        
        removeMessage: (conversationId, messageId) => set((state) => ({
          conversations: state.conversations.map(conversation => 
            conversation.id === conversationId 
              ? { 
                  ...conversation, 
                  messages: conversation.messages.filter(message => message.id !== messageId),
                  updatedAt: new Date()
                } 
              : conversation
          )
        }))
      }),
      { name: 'chat-storage' }
    )
  )
);
