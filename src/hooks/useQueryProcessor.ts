// hooks/useQueryProcessor.ts
import { useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { useAppStore } from '../stores/appStore';
import { useFileStore } from '../stores/fileStore';
import { useChatStore } from '../stores/chatStore';
import { n8nAPI } from '../services/n8nAPI';
import { ProcessedSentence } from '../types/file';
import { Message } from '../types/chat';

export const useQueryProcessor = () => {
  const { setProgress, setSelectedReferences } = useAppStore();
  const { sentences } = useFileStore();
  const { addMessage, setCurrentConversation, conversations } = useChatStore();

  const processQuery = useCallback(async (query: string, conversationId?: string) => {
    // 確保有對話 ID
    const currentConversationId = conversationId || (() => {
      // 如果沒有提供對話 ID，創建一個新對話或使用最近的對話
      if (!conversations.length) {
        const newConversationId = uuidv4();
        const title = query.length > 30 ? `${query.substring(0, 30)}...` : query;
        
        const newConversation = {
          id: newConversationId,
          title,
          messages: [],
          createdAt: new Date(),
          updatedAt: new Date()
        };
        
        setCurrentConversation(newConversationId);
        return newConversationId;
      }
      
      return conversations[0].id;
    })();

    try {
      // 添加使用者訊息
      const userMessageId = uuidv4();
      const userMessage: Message = {
        id: userMessageId,
        type: 'user',
        content: query,
        timestamp: new Date()
      };
      
      addMessage(currentConversationId, userMessage);

      // 階段 1: 關鍵詞提取
      setProgress({
        currentStage: 'extracting',
        percentage: 10,
        details: '提取查詢關鍵詞...',
        isProcessing: true,
        error: null
      });

      const startTime = Date.now();
      const keywordResult = await n8nAPI.extractKeywords(query);
      const keywords = keywordResult[0].output.keywords;

      setProgress({
        currentStage: 'extracting',
        percentage: 30,
        details: {
          stage: '關鍵詞提取完成',
          keywords
        },
        isProcessing: true
      });

      // 階段 2: 本地搜尋相關句子
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
        details: {
          stage: '找到相關句子',
          odSentences,
          cdSentences,
          total: relevantSentences.length
        },
        isProcessing: true
      });

      // 階段 3: 生成回答
      setProgress({
        currentStage: 'generating',
        percentage: 70,
        details: '生成智能回答...',
        isProcessing: true
      });

      const response = await n8nAPI.organizeResponse({
        "operational definition": odSentences.map(s => s.content),
        "conceptual definition": cdSentences.map(s => s.content),
        "query": query
      });

      // 階段 4: 顯示結果
      const processingTime = Date.now() - startTime;
      
      setProgress({
        currentStage: 'completed',
        percentage: 100,
        details: {
          response: response[0].output.response,
          references: relevantSentences
        },
        isProcessing: false
      });

      // 更新引用句子
      setSelectedReferences(relevantSentences);

      // 添加系統回答訊息
      const systemMessageId = uuidv4();
      const systemMessage: Message = {
        id: systemMessageId,
        type: 'system',
        content: response[0].output.response,
        timestamp: new Date(),
        references: relevantSentences,
        metadata: {
          query,
          keywords,
          processingTime,
          totalReferences: relevantSentences.length
        }
      };

      addMessage(currentConversationId, systemMessage);
      
      return {
        response: response[0].output.response,
        references: relevantSentences,
        keywords
      };
    } catch (error) {
      console.error('Query processing error:', error);
      
      // 設置進度狀態為錯誤
      setProgress({
        currentStage: 'error',
        percentage: 0,
        details: error,
        isProcessing: false,
        error: error instanceof Error ? error.message : String(error)
      });
      
      // 添加錯誤訊息
      const errorMessageId = uuidv4();
      const errorMessage: Message = {
        id: errorMessageId,
        type: 'system',
        content: '處理查詢時發生錯誤，請稍後再試。',
        timestamp: new Date()
      };
      
      addMessage(currentConversationId, errorMessage);
      
      throw error;
    }
  }, [setProgress, sentences, addMessage, setCurrentConversation, conversations, setSelectedReferences]);

  // 本地句子搜尋功能
  const searchLocalSentences = (keywords: string[], allSentences: ProcessedSentence[]): ProcessedSentence[] => {
    return allSentences.filter(sentence => 
      keywords.some(keyword => 
        sentence.content.toLowerCase().includes(keyword.toLowerCase())
      )
    );
  };

  return { processQuery };
};
