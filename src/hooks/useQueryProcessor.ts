// hooks/useQueryProcessor.ts
import { useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { useAppStore } from '../stores/appStore';
import { useFileStore } from '../stores/fileStore';
import { useChatStore } from '../stores/chatStore';
import { n8nAPI } from '../services/n8nAPI';
import { ProcessedSentence } from '../types/file';
import { Message, Conversation } from '../types/chat';

export const useQueryProcessor = () => {
  const { setProgress, setSelectedReferences } = useAppStore();
  const { sentences } = useFileStore();
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

      const userMessageId = uuidv4();
      const userMessage: Message = {
        id: userMessageId,
        type: 'user',
        content: queryText,
        timestamp: new Date()
      };
      addMessage(activeConversationId, userMessage);
      console.log('Added user message to conversation:', activeConversationId, userMessage);

      const startTime = Date.now();
      setProgress({
        currentStage: 'extracting',
        percentage: 10,
        details: '提取查詢關鍵詞...',
        isProcessing: true
      });

      const keywordResult = await n8nAPI.extractKeywords(queryText);
      const keywords = keywordResult[0].output.keywords;

      setProgress({
        currentStage: 'extracting',
        percentage: 30,
        details: { stage: '關鍵詞提取完成', keywords },
        isProcessing: true
      });

      setProgress({
        currentStage: 'searching',
        percentage: 40,
        details: '搜尋相關定義句子...',
        isProcessing: true
      });

      const relevantSentences = searchLocalSentences(keywords, sentences);
      const odSentences = relevantSentences.filter(s => s.type === 'OD');
      const cdSentences = relevantSentences.filter(s => s.type === 'CD');

      setProgress({
        currentStage: 'searching',
        percentage: 60,
        details: { stage: '找到相關句子', odSentences, cdSentences, total: relevantSentences.length },
        isProcessing: true
      });

      if (relevantSentences.length === 0) {
        const noResultsMessage: Message = {
          id: uuidv4(),
          type: 'system',
          content: '抱歉，根據您的查詢，在當前文件中找不到相關的定義。請嘗試不同的關鍵詞或上傳其他文件。',
          timestamp: new Date(),
          metadata: { query: queryText, keywords, processingTime: (Date.now() - startTime) / 1000 }
        };
        addMessage(activeConversationId, noResultsMessage);
        setProgress({ currentStage: 'completed', percentage: 100, details: '找不到相關定義', isProcessing: false });
        setSelectedReferences([]);
        return;
      }

      setProgress({
        currentStage: 'generating',
        percentage: 70,
        details: '生成定義摘要...',
        isProcessing: true
      });

      const organizeApiResult = await n8nAPI.organizeResponse({
        "operational definition": odSentences.map(s => s.content),
        "conceptual definition": cdSentences.map(s => s.content),
        "query": queryText
      });

      const organizedContent = organizeApiResult[0]?.output?.response || '無法生成摘要。';

      setProgress({
        currentStage: 'generating',
        percentage: 90,
        details: { stage: '回應生成完成', response: organizedContent },
        isProcessing: true
      });

      const systemMessage: Message = {
        id: uuidv4(),
        type: 'system',
        content: organizedContent,
        references: relevantSentences,
        metadata: {
          query: queryText,
          keywords,
          relevantSentencesCount: relevantSentences.length,
          processingTime: (Date.now() - startTime) / 1000,
        },
        timestamp: new Date()
      };
      addMessage(activeConversationId, systemMessage);
      console.log('Added system message to conversation:', activeConversationId, systemMessage);

      setProgress({
        currentStage: 'completed',
        percentage: 100,
        details: '處理完成！',
        isProcessing: false
      });
      setSelectedReferences(relevantSentences || []);

    } catch (error) {
      console.error('Error in processQuery:', error);
      const errorMessage = error instanceof Error ? error.message : String(error);
      addMessage(activeConversationId, {
        id: uuidv4(),
        type: 'system',
        content: `處理查詢時發生錯誤: ${errorMessage}`,
        timestamp: new Date(),
        metadata: { error: true }
      });
      setProgress({
        currentStage: 'error',
        percentage: 100,
        details: `處理查詢時發生錯誤: ${errorMessage}`,
        isProcessing: false,
        error: errorMessage,
      });
    }
  }, [addMessage, addConversation, sentences, setProgress, setSelectedReferences]);

  const searchLocalSentences = (keywords: string[], allSentences: ProcessedSentence[]): ProcessedSentence[] => {
    if (!keywords || keywords.length === 0 || !allSentences || allSentences.length === 0) {
      return [];
    }
  
    const uniqueSentences = new Map<string, ProcessedSentence>();
  
    keywords.forEach(keyword => {
      const regex = new RegExp(keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i'); // Escape special characters for regex
      allSentences.forEach(sentence => {
        if (regex.test(sentence.content)) {
          if (!uniqueSentences.has(sentence.id)) {
            uniqueSentences.set(sentence.id, sentence);
          }
        }
      });
    });
  
    const results = Array.from(uniqueSentences.values());
    
    results.sort((a, b) => {
      const countA = keywords.filter(k => new RegExp(k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i').test(a.content)).length;
      const countB = keywords.filter(k => new RegExp(k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i').test(b.content)).length;
      if (countB !== countA) return countB - countA; // Higher count first
      if (a.type === 'OD' && b.type !== 'OD') return -1; // OD prioritized
      if (b.type === 'OD' && a.type !== 'OD') return 1;
      return 0;
    });

    return results.slice(0, 20); // Limit to top 20 relevant sentences
  };

  return { processQuery };
};
