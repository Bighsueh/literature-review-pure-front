// hooks/useQueryProcessor.ts
import { useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { useAppStore } from '../stores/appStore';
import { useChatStore } from '../stores/chatStore';
import { apiService } from '../services/api_service';
import { Conversation, Reference } from '../types/chat';
import { createMessage, createSystemMessage, createErrorMessage } from '../utils/messageValidation';

export const useQueryProcessor = () => {
  const { setProgress, setSelectedReferences } = useAppStore();
  const addMessage = useChatStore((state) => state.addMessage);
  const addConversation = useChatStore((state) => state.addConversation);

  const processQuery = useCallback(async (queryText: string, conversationIdFromInput?: string) => {
    let activeConversationId = conversationIdFromInput;
    const currentConversationsFromStore = useChatStore.getState().conversations;

    if (!activeConversationId) {
      // No conversation ID provided by ChatInput (currentConversationId in store was null).
      // Create a new conversation.
      const newConvId = uuidv4();
      const title = queryText.length > 30 ? `${queryText.substring(0, 30)}...` : queryText;
      const newConversation: Conversation = {
        id: newConvId,
        title,
        messages: [],
        createdAt: new Date(),
        updatedAt: new Date(),
      };
      addConversation(newConversation); // This action also sets currentConversationId in the store.
      activeConversationId = newConvId; // Use this new ID for adding messages.
      console.log('Created new conversation with ID:', activeConversationId);
    } else {
      // A conversation ID was provided. Let's ensure it actually exists in the store.
      // This is a defensive check; ideally, it should always exist if provided.
      const conversationExists = currentConversationsFromStore.some(c => c.id === activeConversationId);
      if (!conversationExists) {
        console.warn(`Provided conversationId ${activeConversationId} not found in store. Creating a new one.`);
        const newConvId = uuidv4();
        const title = queryText.length > 30 ? `${queryText.substring(0, 30)}...` : queryText;
        const newConversation: Conversation = {
          id: newConvId,
          title,
          messages: [],
          createdAt: new Date(),
          updatedAt: new Date(),
        };
        addConversation(newConversation);
        activeConversationId = newConvId;
      } else {
        // If the provided ID exists, make sure it's set as the current one in the store,
        // in case it wasn't already (e.g., if user switched conversations then submitted to an old one).
        if (useChatStore.getState().currentConversationId !== activeConversationId) {
            useChatStore.getState().setCurrentConversation(activeConversationId);
            console.log('Set current conversation ID to existing:', activeConversationId);
        }
      }
    }

    // At this point, activeConversationId is guaranteed to be a valid ID
    // for a conversation that exists in the store. If it was newly created,
    // addConversation has already set it as the currentConversationId in the store.

    try {
      setProgress({
        currentStage: 'idle',
        percentage: 0,
        details: '開始處理查詢...',
        isProcessing: true,
        error: null
      });

      const userMessage = createMessage('user', queryText);
      addMessage(activeConversationId, userMessage);
      console.log('Added user message to conversation:', activeConversationId, userMessage);

      setProgress({
        currentStage: 'extracting',
        percentage: 20,
        details: '查詢已送出，等待後端回應...',
        isProcessing: true
      });

      // 呼叫後端工作區化查詢端點 /workspaces/{id}/query/unified
      const apiResult = await apiService.query({ query: queryText });

      if (!apiResult.success || !apiResult.data) {
        throw new Error(apiResult.error || '後端查詢失敗');
      }

      // 修正數據路徑：從 results 中讀取實際的回應數據
      const apiData = apiResult.data as unknown as Record<string, unknown>;
      const results = (apiData.results || apiData) as { response: string; references: Reference[] };
      const { response, references } = results;

      console.log('API 回應數據:', { response, references, fullData: apiResult.data });

      const systemMessage = createSystemMessage(response, {
        references: references as unknown as Reference[],
        query: queryText
      });
      addMessage(activeConversationId, systemMessage);
      console.log('Added system message to conversation:', activeConversationId, systemMessage);

      setProgress({
        currentStage: 'completed',
        percentage: 100,
        details: '處理完成！',
        isProcessing: false
      });
      setSelectedReferences([]);

    } catch (error) {
      console.error('Error in processQuery:', error);
      const errorString = error instanceof Error ? error.message : String(error);
      
      const errorMsg = createErrorMessage(error, '處理查詢時發生錯誤');
      addMessage(activeConversationId, errorMsg);
      setProgress({
        currentStage: 'error',
        percentage: 100,
        details: `處理查詢時發生錯誤: ${errorString}`,
        isProcessing: false,
        error: errorString,
      });
    }
  }, [addMessage, addConversation, setProgress, setSelectedReferences]);

  return { processQuery };
};
