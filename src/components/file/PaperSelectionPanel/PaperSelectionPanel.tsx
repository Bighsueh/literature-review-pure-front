import React, { useEffect, useState } from 'react';
import {
  DocumentTextIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  ArrowPathIcon,
  TrashIcon,
  PlayIcon,
  StopIcon,
  CheckIcon,
  XMarkIcon
} from '@heroicons/react/24/outline';
import { useAppStore } from '../../../stores/app_store';
import { PaperInfo } from '../../../services/api_service';

interface PaperSelectionPanelProps {
  className?: string;
}

const PaperSelectionPanel: React.FC<PaperSelectionPanelProps> = ({ className = '' }) => {
  const {
    papers,
    progress,
    ui,
    refreshPapers,
    togglePaperSelection,
    deletePaper,
    startProcessing,
    stopProcessing,
    clearError
  } = useAppStore();

  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);

  // 初始化時載入論文列表
  useEffect(() => {
    const initialize = async () => {
      if (!isInitialized) {
        await refreshPapers();
        setIsInitialized(true);
      }
    };
    initialize();
  }, [isInitialized, refreshPapers]);

  // 自動刷新論文列表
  useEffect(() => {
    const interval = setInterval(() => {
      if (!ui.isLoading) {
        refreshPapers();
      }
    }, 10000); // 每10秒刷新一次

    return () => clearInterval(interval);
  }, [refreshPapers, ui.isLoading]);

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleString('zh-TW', {
      year: 'numeric',
      month: 'numeric',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getStatusIcon = (status: PaperInfo['processing_status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />;
      case 'failed':
        return <ExclamationTriangleIcon className="h-5 w-5 text-red-500" />;
      case 'processing':
        return <ArrowPathIcon className="h-5 w-5 text-blue-500 animate-spin" />;
      case 'pending':
      default:
        return <DocumentTextIcon className="h-5 w-5 text-gray-400" />;
    }
  };

  const getStatusText = (status: PaperInfo['processing_status']) => {
    switch (status) {
      case 'completed':
        return '已完成';
      case 'failed':
        return '處理失敗';
      case 'processing':
        return '處理中';
      case 'pending':
      default:
        return '等待中';
    }
  };

  const handleSelectAll = () => {
    // 選擇所有已完成的論文
    const completedPapers = (papers.list || []).filter(paper => paper.processing_status === 'completed');
    completedPapers.forEach(paper => {
      if (!paper.selected) {
        togglePaperSelection(paper.id);
      }
    });
  };

  const handleDeselectAll = () => {
    // 取消選擇所有論文
    (papers.selectedIds || []).forEach(paperId => {
      togglePaperSelection(paperId);
    });
  };

  const handleDeleteClick = (e: React.MouseEvent, paperId: string) => {
    e.stopPropagation();
    setDeleteConfirmId(paperId);
  };

  const confirmDelete = async (e: React.MouseEvent, paperId: string) => {
    e.stopPropagation();
    await deletePaper(paperId);
    setDeleteConfirmId(null);
  };

  const cancelDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    setDeleteConfirmId(null);
  };

  const handleStartProcessing = async () => {
    if (papers.selectedIds.length === 0) {
      return;
    }
    await startProcessing();
  };

  const handleStopProcessing = async () => {
    await stopProcessing();
  };

  const selectedCount = papers.selectedIds?.length || 0;
  const completedCount = (papers.list || []).filter(p => p.processing_status === 'completed').length;
  const processingCount = (papers.list || []).filter(p => p.processing_status === 'processing').length;

  return (
    <div className={`flex flex-col h-full ${className}`}>
      {/* 標題列 */}
      <div className="flex-shrink-0 p-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-medium text-gray-900">論文管理</h3>
          <button
            onClick={refreshPapers}
            disabled={ui.isLoading}
            className="text-gray-400 hover:text-gray-600 disabled:opacity-50"
          >
            <ArrowPathIcon className={`h-5 w-5 ${ui.isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
        
        {/* 統計信息 */}
        <div className="mt-2 text-sm text-gray-500">
          總計 {papers.list?.length || 0} 篇 | 已完成 {completedCount} 篇 | 處理中 {processingCount} 篇
        </div>
      </div>

      {/* 操作按鈕 */}
      <div className="flex-shrink-0 p-4 border-b border-gray-200 space-y-2">
        {/* 選擇操作 */}
        <div className="flex items-center space-x-2">
          <button
            onClick={handleSelectAll}
            disabled={completedCount === 0 || ui.isLoading}
            className="flex-1 px-3 py-2 text-sm bg-blue-50 text-blue-700 rounded-md hover:bg-blue-100 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            全選已完成
          </button>
          <button
            onClick={handleDeselectAll}
            disabled={selectedCount === 0 || ui.isLoading}
            className="flex-1 px-3 py-2 text-sm bg-gray-50 text-gray-700 rounded-md hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            取消全選
          </button>
        </div>

        {/* 處理操作 */}
        <div className="flex items-center space-x-2">
          {progress.isProcessing ? (
            <button
              onClick={handleStopProcessing}
              className="flex-1 flex items-center justify-center px-3 py-2 text-sm bg-red-50 text-red-700 rounded-md hover:bg-red-100"
            >
              <StopIcon className="h-4 w-4 mr-1" />
              停止處理
            </button>
          ) : (
            <button
              onClick={handleStartProcessing}
              disabled={selectedCount === 0 || ui.isLoading}
              className="flex-1 flex items-center justify-center px-3 py-2 text-sm bg-green-50 text-green-700 rounded-md hover:bg-green-100 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <PlayIcon className="h-4 w-4 mr-1" />
              開始處理 ({selectedCount})
            </button>
          )}
        </div>

        {/* 選擇狀態顯示 */}
        {selectedCount > 0 && (
          <div className="text-sm text-blue-600 bg-blue-50 px-3 py-2 rounded-md">
            已選擇 {selectedCount} 篇論文
          </div>
        )}
      </div>

      {/* 錯誤提示 */}
      {ui.errorMessage && (
        <div className="flex-shrink-0 mx-4 mt-2 p-3 bg-red-50 border border-red-200 rounded-md">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <ExclamationTriangleIcon className="h-5 w-5 text-red-400 mr-2" />
              <span className="text-sm text-red-700">{ui.errorMessage}</span>
            </div>
            <button
              onClick={clearError}
              className="text-red-400 hover:text-red-600"
            >
              <XMarkIcon className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* 論文列表 */}
      <div className="flex-1 overflow-y-auto">
        {ui.isLoading && (papers.list?.length || 0) === 0 ? (
          <div className="flex items-center justify-center h-32">
            <ArrowPathIcon className="h-6 w-6 text-gray-400 animate-spin mr-2" />
            <span className="text-gray-500">載入中...</span>
          </div>
        ) : (papers.list?.length || 0) === 0 ? (
          <div className="flex items-center justify-center h-32 text-gray-500">
            尚未上傳任何論文
          </div>
        ) : (
          <ul className="divide-y divide-gray-200">
            {(papers.list || []).map((paper) => (
              <li key={paper.id} className="p-4 hover:bg-gray-50">
                <div className="flex items-start space-x-3">
                  {/* 選擇框 */}
                  <div className="flex-shrink-0 mt-1">
                    <button
                      onClick={() => togglePaperSelection(paper.id)}
                      disabled={paper.processing_status !== 'completed' || ui.isLoading}
                      className={`
                        w-5 h-5 rounded border-2 flex items-center justify-center
                        ${paper.selected 
                          ? 'bg-blue-500 border-blue-500 text-white' 
                          : 'border-gray-300 hover:border-blue-500'
                        }
                        ${paper.processing_status !== 'completed' 
                          ? 'opacity-50 cursor-not-allowed' 
                          : 'cursor-pointer'
                        }
                      `}
                    >
                      {paper.selected && <CheckIcon className="h-3 w-3" />}
                    </button>
                  </div>

                  {/* 狀態圖標 */}
                  <div className="flex-shrink-0 mt-1">
                    {getStatusIcon(paper.processing_status)}
                  </div>

                  {/* 論文信息 */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {paper.title}
                        </p>
                        {Array.isArray(paper.authors) && paper.authors.length > 0 && (
                          <p className="text-xs text-gray-500 truncate">
                            {paper.authors.join(', ')}
                          </p>
                        )}
                        <div className="flex items-center space-x-2 text-xs text-gray-500 mt-1">
                          <span>{formatDate(paper.upload_time)}</span>
                          <span>•</span>
                          <span>{getStatusText(paper.processing_status)}</span>
                          {paper.section_count > 0 && (
                            <>
                              <span>•</span>
                              <span>{paper.section_count} 章節</span>
                            </>
                          )}
                          {paper.sentence_count > 0 && (
                            <>
                              <span>•</span>
                              <span>{paper.sentence_count} 句子</span>
                            </>
                          )}
                        </div>
                      </div>

                      {/* 刪除按鈕 */}
                      <div className="flex-shrink-0 ml-2">
                        {deleteConfirmId === paper.id ? (
                          <div className="flex items-center space-x-1">
                            <button
                              onClick={(e) => confirmDelete(e, paper.id)}
                              className="text-red-500 hover:text-red-700 text-xs px-2 py-1"
                            >
                              確認
                            </button>
                            <button
                              onClick={cancelDelete}
                              className="text-gray-500 hover:text-gray-700 text-xs px-2 py-1"
                            >
                              取消
                            </button>
                          </div>
                        ) : (
                          <button
                            onClick={(e) => handleDeleteClick(e, paper.id)}
                            disabled={ui.isLoading}
                            className="text-gray-400 hover:text-red-500 p-1 disabled:opacity-50"
                          >
                            <TrashIcon className="h-4 w-4" />
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* 底部狀態 */}
      {progress.isProcessing && (
        <div className="flex-shrink-0 p-4 border-t border-gray-200 bg-blue-50">
          <div className="flex items-center space-x-2">
            <ArrowPathIcon className="h-4 w-4 text-blue-500 animate-spin" />
            <span className="text-sm text-blue-700">
              正在處理論文... ({progress.percentage.toFixed(1)}%)
            </span>
          </div>
          {typeof progress.details === 'object' && progress.details && 'message' in progress.details && (
            <p className="text-xs text-blue-600 mt-1">
              {progress.details.message as string}
            </p>
          )}
        </div>
      )}
    </div>
  );
};

export default PaperSelectionPanel; 