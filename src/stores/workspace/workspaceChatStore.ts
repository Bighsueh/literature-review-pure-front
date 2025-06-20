/**
 * 工作區對話狀態管理 - FE-02 多工作區狀態管理重構
 * 負責特定工作區的對話、查詢和AI互動管理
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { ChatHistory, QueryRequest, QueryResult } from '../../types/api';
import { workspaceApiService } from '../../services/workspace_api_service';
import { useWorkspaceStore } from './workspaceStore';

// 本地對話狀態接口
interface LocalMessage extends ChatHistory {
  isStreaming?: boolean;
  localId?: string;
}

interface WorkspaceChatState {
  // 對話資料
  messages: LocalMessage[];
  currentConversationId: string | null;
  
  // 查詢狀態
  isQuerying: boolean;
  lastQuery: string | null;
  queryError: string | null;
  
  // 串流狀態
  streamingMessageId: string | null;
  
  // UI 狀態
  isLoading: boolean;
  error: string | null;
  
  // 動作
  setMessages: (messages: LocalMessage[]) => void;
  addMessage: (message: LocalMessage) => void;
  updateMessage: (messageId: string, updates: Partial<LocalMessage>) => void;
  removeMessage: (messageId: string) => void;
  
  // 對話管理
  startNewConversation: () => void;
  clearConversation: () => void;
  
  // 查詢和AI互動
  sendQuery: (query: string, selectedPaperIds?: string[]) => Promise<QueryResult | null>;
  stopStreaming: () => void;
  
  // 載入狀態
  setLoading: (isLoading: boolean) => void;
  setError: (error: string | null) => void;
  
  // API 操作
  refreshChatHistory: () => Promise<void>;
  saveChatMessage: (message: Omit<LocalMessage, 'id' | 'workspace_id' | 'created_at'>) => Promise<string | null>;
  
  // 清理
  clearAllData: () => void;
}

// 創建工作區對話狀態管理工廠
const createWorkspaceChatStore = (workspaceId: string) => {
  return create<WorkspaceChatState>()(
    devtools(
      persist(
        (set, get) => ({
          // 初始狀態
          messages: [],
          currentConversationId: null,
          isQuerying: false,
          lastQuery: null,
          queryError: null,
          streamingMessageId: null,
          isLoading: false,
          error: null,
          
          // 基礎訊息操作
          setMessages: (messages) => set({ messages }),
          
          addMessage: (message) => set((state) => ({
            messages: [...state.messages, message]
          })),
          
          updateMessage: (messageId, updates) => set((state) => ({
            messages: state.messages.map(message =>
              message.id === messageId || message.localId === messageId
                ? { ...message, ...updates }
                : message
            )
          })),
          
          removeMessage: (messageId) => set((state) => ({
            messages: state.messages.filter(message => 
              message.id !== messageId && message.localId !== messageId
            )
          })),
          
          // 對話管理
          startNewConversation: () => {
            const conversationId = `conv_${Date.now()}`;
            set({ 
              currentConversationId: conversationId,
              messages: [],
              queryError: null
            });
          },
          
          clearConversation: () => set({
            messages: [],
            currentConversationId: null,
            lastQuery: null,
            queryError: null,
            streamingMessageId: null
          }),
          
          // 查詢和AI互動
          sendQuery: async (query, selectedPaperIds) => {
            set({ 
              isQuerying: true, 
              queryError: null,
              lastQuery: query
            });
            
            // 添加用戶訊息
            const userLocalId = `user_${Date.now()}`;
            const userMessage: LocalMessage = {
              id: userLocalId,
              localId: userLocalId,
              workspace_id: workspaceId,
              user_question: query,
              ai_response: '',
              context_papers: selectedPaperIds || [],
              created_at: new Date().toISOString()
            };
            
            get().addMessage(userMessage);
            
            // 添加AI回應佔位符
            const aiLocalId = `ai_${Date.now()}`;
            const aiMessage: LocalMessage = {
              id: aiLocalId,
              localId: aiLocalId,
              workspace_id: workspaceId,
              user_question: '',
              ai_response: '思考中...',
              isStreaming: true,
              created_at: new Date().toISOString()
            };
            
            get().addMessage(aiMessage);
            set({ streamingMessageId: aiLocalId });
            
            try {
              const queryRequest: QueryRequest = {
                query,
                selected_paper_ids: selectedPaperIds
              };
              
              const response = await workspaceApiService.query(queryRequest);
              
              if (response.success && response.data) {
                // 更新AI回應
                get().updateMessage(aiLocalId, {
                  ai_response: response.data.response,
                  isStreaming: false,
                  context_papers: selectedPaperIds || [],
                  query_metadata: {
                    references: response.data.references,
                    source_summary: response.data.source_summary
                  }
                });
                
                set({ 
                  isQuerying: false,
                  streamingMessageId: null
                });
                
                return response.data;
              } else {
                // 查詢失敗
                get().updateMessage(aiLocalId, {
                  ai_response: `查詢失敗: ${response.error || 'Unknown error'}`,
                  isStreaming: false
                });
                
                set({ 
                  isQuerying: false,
                  streamingMessageId: null,
                  queryError: response.error || 'Query failed'
                });
                
                return null;
              }
            } catch (error) {
              const errorMessage = error instanceof Error ? error.message : 'Unknown error';
              
              get().updateMessage(aiLocalId, {
                ai_response: `錯誤: ${errorMessage}`,
                isStreaming: false
              });
              
              set({ 
                isQuerying: false,
                streamingMessageId: null,
                queryError: errorMessage
              });
              
              return null;
            }
          },
          
          stopStreaming: () => {
            const { streamingMessageId } = get();
            if (streamingMessageId) {
              get().updateMessage(streamingMessageId, {
                isStreaming: false,
                ai_response: '回應已停止'
              });
              set({ 
                streamingMessageId: null,
                isQuerying: false
              });
            }
          },
          
          // 載入狀態
          setLoading: (isLoading) => set({ isLoading }),
          setError: (error) => set({ error }),
          
          // API 操作
          refreshChatHistory: async () => {
            set({ isLoading: true, error: null });
            
            try {
              const response = await workspaceApiService.getChatHistory(1, 50);
              
              if (response.success && response.data) {
                const chatHistory = response.data.items.map(chat => ({
                  ...chat,
                  isStreaming: false
                }));
                
                set({ 
                  messages: chatHistory,
                  isLoading: false
                });
              } else {
                set({ 
                  isLoading: false, 
                  error: response.error || 'Failed to fetch chat history' 
                });
              }
            } catch (error) {
              const errorMessage = error instanceof Error ? error.message : 'Unknown error';
              set({ isLoading: false, error: errorMessage });
            }
          },
          
          saveChatMessage: async (message) => {
            try {
              const response = await workspaceApiService.saveChatHistory(message);
              
              if (response.success && response.data) {
                return response.data.id;
              } else {
                set({ error: response.error || 'Failed to save chat message' });
                return null;
              }
            } catch (error) {
              const errorMessage = error instanceof Error ? error.message : 'Save error';
              set({ error: errorMessage });
              return null;
            }
          },
          
          // 清理
          clearAllData: () => set({
            messages: [],
            currentConversationId: null,
            isQuerying: false,
            lastQuery: null,
            queryError: null,
            streamingMessageId: null,
            isLoading: false,
            error: null
          })
        }),
        {
          name: `workspace-chat-${workspaceId}`,
          partialize: (state) => ({
            messages: state.messages.filter(msg => !msg.isStreaming),
            currentConversationId: state.currentConversationId,
            lastQuery: state.lastQuery
          })
        }
      ),
      { name: `WorkspaceChatStore-${workspaceId}` }
    )
  );
};

// 工作區對話 stores 快取
const workspaceChatStores: Record<string, ReturnType<typeof createWorkspaceChatStore>> = {};

// 獲取或創建工作區對話 store
export const getWorkspaceChatStore = (workspaceId: string) => {
  if (!workspaceChatStores[workspaceId]) {
    workspaceChatStores[workspaceId] = createWorkspaceChatStore(workspaceId);
  }
  return workspaceChatStores[workspaceId];
};

// Hook：使用當前工作區的對話 store
export const useCurrentWorkspaceChatStore = () => {
  const currentWorkspaceId = useWorkspaceStore((state) => state.currentWorkspaceId);
  
  if (!currentWorkspaceId) {
    throw new Error('No current workspace selected');
  }
  
  return getWorkspaceChatStore(currentWorkspaceId)();
}; 