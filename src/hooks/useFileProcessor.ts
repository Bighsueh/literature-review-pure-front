// hooks/useFileProcessor.ts
import { useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { useAppStore } from '../stores/appStore';
import { useFileStore } from '../stores/fileStore';
import { splitSentencesAPI } from '../services/splitSentencesAPI';
import { n8nAPI } from '../services/n8nAPI';
import { localStorageService } from '../services/localStorageService';
import { FileData, ProcessedSentence } from '../types/file';
// SentenceWithPage 用於處理來自 splitSentencesAPI 的回傳值
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
      
      const sentencesWithPage = await splitSentencesAPI.processFile(file);
      
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
      
      for (let i = 0; i < sentencesWithPage.length; i++) {
        const sentenceObj = sentencesWithPage[i];
        const progress = 20 + (i / sentencesWithPage.length) * 70;
        
        // 取得句子文本
        const sentenceText = sentenceObj.sentence;

        setProgress({ 
          currentStage: 'analyzing', 
          percentage: progress, 
          details: {
            message: `分析第 ${i+1}/${sentencesWithPage.length} 個句子`,
            currentSentence: sentenceText,
            processed: i + 1,
            total: sentencesWithPage.length
          },
          isProcessing: true
        });
        
        updateFile(fileId, { processingProgress: progress });
        
        // 呼叫 n8n API 檢查句子類型，添加重試機制
        let result;
        let retryCount = 0;
        let success = false;
        
        while (retryCount < 3 && !success) {
          try {
            // 只傳遞句子文本到 n8n API
            result = await n8nAPI.checkOdCd(sentenceText);
            
            // 檢查 defining_type 是否存在
            if (result && result.defining_type) {
              success = true;
            } else {
              // 如果 defining_type 不存在，視為需要重試的錯誤
              console.warn(`Retry ${retryCount + 1}: defining_type is undefined`, result);
              retryCount++;
              // 短暫延遲後重試
              await new Promise(resolve => setTimeout(resolve, 1000));
            }
          } catch (error) {
            console.warn(`Retry ${retryCount + 1} failed:`, error);
            retryCount++;
            // 短暫延遲後重試
            await new Promise(resolve => setTimeout(resolve, 1000));
          }
        }
        
        // 如果三次重試後仍然失敗，則跳過這筆資料
        if (!success) {
          console.error(`Skipping sentence after 3 retries: ${sentenceText.substring(0, 50) + '...'}`);
          
          // 使用預設值創建一個記錄，標記為 'OTHER'
          const processedSentence: ProcessedSentence = {
            id: uuidv4(),
            content: sentenceText,
            type: 'OTHER', // 預設為 OTHER
            reason: '自動跳過：處理此句時發生錯誤',
            fileId,
            pageNumber: sentenceObj.page,
            fileName: sentenceObj.fileName,
            skipped: true // 添加標記表示此句被跳過
          };
          
          processedSentences.push(processedSentence);
          continue; // 跳到下一個句子
        }
        
        // 正常處理句子
        try {
          // 確保 result 不是 undefined
          if (!result) {
            throw new Error('Result is undefined after successful check');
          }
          
          const processedSentence: ProcessedSentence = {
            id: uuidv4(),
            content: sentenceText,
            type: result.defining_type.toUpperCase() as 'OD' | 'CD' | 'OTHER',
            reason: result.reason || '',
            fileId,
            pageNumber: sentenceObj.page,
            fileName: sentenceObj.fileName
          };
          
          processedSentences.push(processedSentence);
        } catch (error) {
          // 如果在處理過程中出現錯誤，使用預設值
          console.error('Error processing sentence result:', error);
          const processedSentence: ProcessedSentence = {
            id: uuidv4(),
            content: sentenceText,
            type: 'OTHER', // 預設為 OTHER
            reason: '處理此句時發生錯誤',
            fileId,
            pageNumber: sentenceObj.page,
            fileName: sentenceObj.fileName,
            skipped: true
          };
          
          processedSentences.push(processedSentence);
        }
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
