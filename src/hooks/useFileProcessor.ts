// hooks/useFileProcessor.ts
import { useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { useAppStore } from '../stores/appStore';
import { useFileStore } from '../stores/fileStore';
import { splitSentencesAPI } from '../services/splitSentencesAPI';
import { n8nAPI } from '../services/n8nAPI';
import { localStorageService } from '../services/localStorageService';
import { FileData, ProcessedSentence } from '../types/file';

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
      
      // 階段 2: 批次分析 OD/CD
      setProgress({ 
        currentStage: 'analyzing', 
        percentage: 20, 
        details: '開始分析句子類型...',
        isProcessing: true
      });
      
      // 準備處理的句子
      const processedSentences: ProcessedSentence[] = [];
      const sentenceTexts: string[] = sentencesWithPage.map(obj => obj.sentence);

      // 使用我們的批次處理方法
      try {
        // 定義進度回調函數
        const onProgressUpdate = (processed: number, total: number, currentSentence?: string) => {
          // 計算進度百分比 (20% 開始，70% 範圍內完成分析階段)
          const progress = 20 + (processed / total) * 70;
          
          setProgress({ 
            currentStage: 'analyzing', 
            percentage: progress, 
            details: {
              message: `批次分析中: ${processed}/${total} 個句子`,
              currentSentence,
              processed,
              total
            },
            isProcessing: true
          });
          
          updateFile(fileId, { processingProgress: progress });
        };

        // 調用批次處理 API
        const batchResults = await n8nAPI.checkOdCdBatch(sentenceTexts, onProgressUpdate);
        
        // 處理結果
        batchResults.forEach((result, index) => {
          const sentenceObj = sentencesWithPage[index];
          const sentenceText = sentenceObj.sentence;
          
          try {
            // 檢查是否有錯誤
            if ((result.result as any).error) {
              console.error(`Error processing sentence: ${sentenceText.substring(0, 50)}...`, result.result);
              
              // 處理錯誤情況
              const processedSentence: ProcessedSentence = {
                id: uuidv4(),
                content: sentenceText,
                type: 'OTHER', // 預設為 OTHER
                reason: '處理此句時發生錯誤: ' + (result.result.reason || '未知錯誤'),
                fileId,
                pageNumber: sentenceObj.page,
                fileName: sentenceObj.fileName,
                skipped: true
              };
              
              processedSentences.push(processedSentence);
              return; // 跳過此次迭代
            }
            
            // 正常處理句子
            const processedSentence: ProcessedSentence = {
              id: uuidv4(),
              content: sentenceText,
              type: result.result.defining_type?.toUpperCase() as 'OD' | 'CD' | 'OTHER',
              reason: result.result.reason || '',
              fileId,
              pageNumber: sentenceObj.page,
              fileName: sentenceObj.fileName
            };
            
            processedSentences.push(processedSentence);
          } catch (error) {
            // 如果在處理過程中出現錯誤，使用預設值
            console.error('Error processing batch result:', error);
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
        });
      } catch (error) {
        console.error('Batch processing error:', error);
        
        // 如果批量處理失敗，為所有句子創建默認處理結果
        sentencesWithPage.forEach(sentenceObj => {
          const processedSentence: ProcessedSentence = {
            id: uuidv4(),
            content: sentenceObj.sentence,
            type: 'OTHER',
            reason: '批量處理失敗：' + (error instanceof Error ? error.message : '未知錯誤'),
            fileId,
            pageNumber: sentenceObj.page,
            fileName: sentenceObj.fileName,
            skipped: true
          };
          
          processedSentences.push(processedSentence);
        });
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
