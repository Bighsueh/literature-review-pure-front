// hooks/useFileProcessor.ts
import { useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { useAppStore } from '../stores/appStore';
import { useFileStore } from '../stores/fileStore';
import { splitSentencesAPI } from '../services/splitSentencesAPI';
import { n8nAPI } from '../services/n8nAPI';
import { localStorageService } from '../services/localStorageService';
import { FileData, ProcessedSentence } from '../types/file';
import { SentenceWithPage } from '../types/api';

export const useFileProcessor = () => {
  const { setProgress } = useAppStore();
  const { addFile, updateFile, setSentences } = useFileStore();

  const processFile = useCallback(async (file: File) => {
    // 生成唯一ID並創建檔案對象
    const fileId = uuidv4();
    const fileData: FileData = {
      id: fileId,
      name: file.name,
      size: file.size,
      type: file.type,
      uploadedAt: new Date(),
      status: 'uploading',
      processingProgress: 0,
      blob: file
    };

    // 添加檔案到 store
    addFile(fileData);
    
    try {
      // 階段 1: 上傳檔案到 split_sentences API
      setProgress({ 
        currentStage: 'uploading', 
        percentage: 10, 
        details: '正在上傳檔案...',
        isProcessing: true,
        error: null
      });
      
      updateFile(fileId, { status: 'processing', processingProgress: 10 });
      
      const sentences = await splitSentencesAPI.processFile(file);
      
      // 保存檔案元數據
      await localStorageService.saveFileMetadata({
        id: fileId,
        name: file.name,
        size: file.size,
        type: file.type,
        uploadedAt: new Date()
      });
      
      // 階段 2: 逐句分析 OD/CD
      setProgress({ 
        currentStage: 'analyzing', 
        percentage: 20, 
        details: '開始分析句子類型...',
        isProcessing: true
      });
      
      const processedSentences: ProcessedSentence[] = [];
      
      for (let i = 0; i < sentences.length; i++) {
        const sentence = sentences[i];
        const progress = 20 + (i / sentences.length) * 70;
        
        // 確保 currentSentence 是字符串類型
        const sentenceText = typeof sentence === 'string' 
          ? sentence 
          : typeof sentence === 'object' && sentence && 'sentence' in sentence 
            ? (sentence as SentenceWithPage).sentence 
            : JSON.stringify(sentence);

        setProgress({ 
          currentStage: 'analyzing', 
          percentage: progress, 
          details: {
            message: `分析第 ${i+1}/${sentences.length} 個句子`,
            currentSentence: sentenceText,
            processed: i + 1,
            total: sentences.length
          },
          isProcessing: true
        });
        
        updateFile(fileId, { processingProgress: progress });
        
        // 呼叫 n8n API 檢查句子類型
        const result = await n8nAPI.checkOdCd(sentence);
        
        const processedSentence: ProcessedSentence = {
          id: uuidv4(),
          content: sentence,
          type: result.defining_type.toUpperCase() as 'OD' | 'CD' | 'OTHER',
          reason: result.reason,
          fileId
        };
        
        processedSentences.push(processedSentence);
      }
      
      // 階段 3: 儲存到 LocalStorage
      setProgress({ 
        currentStage: 'saving', 
        percentage: 95, 
        details: '儲存處理結果...',
        isProcessing: true
      });
      
      await localStorageService.saveSentences(processedSentences);
      
      // 更新檔案狀態為完成
      updateFile(fileId, { 
        status: 'completed', 
        processingProgress: 100 
      });
      
      // 更新句子 store
      setSentences(processedSentences);
      
      // 完成處理
      setProgress({ 
        currentStage: 'completed', 
        percentage: 100, 
        details: '檔案處理完成！',
        isProcessing: false
      });
      
      return processedSentences;
    } catch (error) {
      console.error('File processing error:', error);
      
      // 更新檔案狀態為錯誤
      updateFile(fileId, { 
        status: 'error', 
        processingProgress: 0 
      });
      
      // 設置進度狀態為錯誤
      setProgress({ 
        currentStage: 'error', 
        percentage: 0, 
        details: error,
        isProcessing: false,
        error: error instanceof Error ? error.message : String(error)
      });
      
      throw error;
    }
  }, [addFile, setProgress, updateFile, setSentences]);

  return { processFile };
};
