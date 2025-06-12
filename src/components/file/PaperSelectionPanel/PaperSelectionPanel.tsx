import React, { useEffect, useState, useCallback } from 'react';
import {
  DocumentTextIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  ArrowPathIcon,
  TrashIcon,
  XMarkIcon,
  ClockIcon,
  CheckIcon,
  MinusIcon
} from '@heroicons/react/24/outline';
import { CheckIcon as CheckIconSolid } from '@heroicons/react/24/solid';
import { useAppStore } from '../../../stores/app_store';
import { PaperInfo } from '../../../services/api_service';

interface PaperSelectionPanelProps {
  className?: string;
}

// 論文選取標題組件
const PaperSelectionHeader: React.FC<{
  totalCount: number;
  selectedCount: number;
  isAllSelected: boolean;
  isPartialSelected: boolean;
  onSelectAll: () => void;
  onDeselectAll: () => void;
  isLoading: boolean;
}> = ({ 
  totalCount, 
  selectedCount, 
  isAllSelected, 
  isPartialSelected, 
  onSelectAll, 
  onDeselectAll,
  isLoading 
}) => {
  const handleToggleAll = useCallback(() => {
    if (isAllSelected) {
      onDeselectAll();
    } else {
      onSelectAll();
    }
  }, [isAllSelected, onSelectAll, onDeselectAll]);

  return (
    <div className="flex-shrink-0 p-3 bg-gray-50 border-b border-gray-200">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <button
            onClick={handleToggleAll}
            disabled={isLoading || totalCount === 0}
            className="flex items-center justify-center w-5 h-5 border-2 rounded transition-colors duration-150 disabled:opacity-50"
            style={{
              borderColor: isAllSelected || isPartialSelected ? '#3B82F6' : '#D1D5DB',
              backgroundColor: isAllSelected ? '#3B82F6' : 'transparent'
            }}
          >
            {isAllSelected && (
              <CheckIconSolid className="w-3 h-3 text-white" />
            )}
            {isPartialSelected && !isAllSelected && (
              <MinusIcon className="w-3 h-3 text-blue-600" />
            )}
          </button>
          <div>
            <h3 className="text-sm font-medium text-gray-900">論文選取</h3>
            <p className="text-xs text-gray-500">
              已選取 {selectedCount} / {totalCount} 篇論文
            </p>
          </div>
        </div>
        
        {selectedCount > 0 && (
          <div className="text-xs text-blue-600 font-medium">
            {selectedCount} 篇已選取
          </div>
        )}
      </div>
    </div>
  );
};

// 單個論文項目組件
const PaperSelectionItem: React.FC<{
  paper: PaperInfo;
  isSelected: boolean;
  onToggleSelection: (paperId: string) => void;
  onDelete: (paperId: string) => void;
  deleteConfirmId: string | null;
  setDeleteConfirmId: (id: string | null) => void;
}> = ({ 
  paper, 
  isSelected, 
  onToggleSelection, 
  onDelete, 
  deleteConfirmId, 
  setDeleteConfirmId 
}) => {
  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleString('zh-TW', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    });
  };

  const getStatusInfo = (status: PaperInfo['processing_status']) => {
    switch (status) {
      case 'completed':
        return { 
          icon: <CheckCircleIcon className="h-5 w-5 text-green-500" />, 
          text: '已完成',
          className: 'bg-green-100 text-green-800'
        };
      case 'failed':
        return { 
          icon: <ExclamationTriangleIcon className="h-5 w-5 text-red-500" />, 
          text: '處理失敗',
          className: 'bg-red-100 text-red-800'
        };
      case 'processing':
        return { 
          icon: <ArrowPathIcon className="h-5 w-5 text-blue-500 animate-spin" />, 
          text: '處理中',
          className: 'bg-blue-100 text-blue-800'
        };
      case 'pending':
      default:
        return { 
          icon: <ClockIcon className="h-5 w-5 text-gray-500" />, 
          text: '等待中',
          className: 'bg-gray-100 text-gray-800'
        };
    }
  };

  const handleDeleteClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setDeleteConfirmId(paper.id);
  };

  const confirmDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDelete(paper.id);
    setDeleteConfirmId(null);
  };

  const cancelDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    setDeleteConfirmId(null);
  };

  const handleToggleClick = useCallback(() => {
    onToggleSelection(paper.id);
  }, [paper.id, onToggleSelection]);

  const statusInfo = getStatusInfo(paper.processing_status);

  return (
    <li className="p-3 hover:bg-gray-50 transition-colors duration-150">
      <div className="flex items-center space-x-3">
        {/* 選取 Checkbox */}
        <button
          onClick={handleToggleClick}
          className="flex items-center justify-center w-5 h-5 border-2 rounded transition-colors duration-150 hover:border-blue-400"
          style={{
            borderColor: isSelected ? '#3B82F6' : '#D1D5DB',
            backgroundColor: isSelected ? '#3B82F6' : 'transparent'
          }}
        >
          {isSelected && (
            <CheckIconSolid className="w-3 h-3 text-white" />
          )}
        </button>

        {/* 文件圖標 */}
        <div className="flex-shrink-0 text-gray-400">
          <DocumentTextIcon className="h-6 w-6" />
        </div>

        {/* 論文資訊 */}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-900 truncate" title={paper.title}>
            {paper.title}
          </p>
          <p className="text-sm text-gray-500">
            {formatDate(paper.upload_time)}
          </p>
        </div>

        {/* 狀態標籤 */}
        <div className="flex-shrink-0 flex items-center space-x-2">
          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusInfo.className}`}>
            {statusInfo.text}
          </span>

          {/* 刪除按鈕 */}
          {deleteConfirmId === paper.id ? (
            <div className="flex items-center space-x-1">
              <button 
                onClick={confirmDelete} 
                className="p-1 text-green-600 hover:text-green-800"
                title="確認刪除"
              >
                <CheckIcon className="h-4 w-4"/>
              </button>
              <button 
                onClick={cancelDelete} 
                className="p-1 text-red-600 hover:text-red-800"
                title="取消刪除"
              >
                <XMarkIcon className="h-4 w-4"/>
              </button>
            </div>
          ) : (
            <button 
              onClick={handleDeleteClick} 
              className="p-1 text-gray-400 hover:text-red-600"
              title="刪除論文"
            >
              <TrashIcon className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>
    </li>
  );
};

// 主組件
const PaperSelectionPanel: React.FC<PaperSelectionPanelProps> = ({ className = '' }) => {
  const {
    papers,
    ui,
    refreshPapers,
    deletePaper,
    togglePaperSelection,
    selectAllPapers,
    deselectAllPapers,
    clearError
  } = useAppStore();

  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  // 計算派生狀態
  const selectedCount = papers.selectedIds.length;
  const totalCount = papers.list.length;
  const isAllSelected = totalCount > 0 && selectedCount === totalCount;
  const isPartialSelected = selectedCount > 0 && selectedCount < totalCount;

  useEffect(() => {
    refreshPapers();
    const interval = setInterval(refreshPapers, 5000); // 每5秒刷新一次
    return () => clearInterval(interval);
  }, [refreshPapers]);

  // 事件處理函數
  const handleToggleSelection = useCallback(async (paperId: string) => {
    await togglePaperSelection(paperId);
  }, [togglePaperSelection]);

  const handleSelectAll = useCallback(async () => {
    await selectAllPapers();
  }, [selectAllPapers]);

  const handleDeselectAll = useCallback(async () => {
    await deselectAllPapers();
  }, [deselectAllPapers]);

  const handleDelete = useCallback(async (paperId: string) => {
    await deletePaper(paperId);
  }, [deletePaper]);

  return (
    <div className={`flex flex-col h-full bg-white ${className}`}>
      {/* 錯誤提示 */}
      {ui.errorMessage && (
        <div className="flex-shrink-0 m-2 p-2 bg-red-50 border border-red-200 rounded-md">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <ExclamationTriangleIcon className="h-4 w-4 text-red-400 mr-2" />
              <span className="text-sm text-red-700">{ui.errorMessage}</span>
            </div>
            <button onClick={clearError} className="text-red-400 hover:text-red-600">
              <XMarkIcon className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* 選取標題 */}
      <PaperSelectionHeader
        totalCount={totalCount}
        selectedCount={selectedCount}
        isAllSelected={isAllSelected}
        isPartialSelected={isPartialSelected}
        onSelectAll={handleSelectAll}
        onDeselectAll={handleDeselectAll}
        isLoading={ui.isLoading}
      />

      {/* 論文列表 */}
      <div className="flex-1 overflow-y-auto">
        {ui.isLoading && !papers.list.length ? (
          <div className="flex items-center justify-center h-full">
            <ArrowPathIcon className="h-6 w-6 text-gray-400 animate-spin mr-2" />
            <span className="text-gray-500">載入中...</span>
          </div>
        ) : !papers.list.length ? (
          <div className="text-center py-10 px-4">
            <DocumentTextIcon className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">無上傳檔案</h3>
            <p className="mt-1 text-sm text-gray-500">請從上方拖曳或點擊以上傳您的第一份文件。</p>
          </div>
        ) : (
          <ul className="divide-y divide-gray-200">
            {papers.list.map((paper) => (
              <PaperSelectionItem
                key={paper.id}
                paper={paper}
                isSelected={papers.selectedIds.includes(paper.id)}
                onToggleSelection={handleToggleSelection}
                onDelete={handleDelete}
                deleteConfirmId={deleteConfirmId}
                setDeleteConfirmId={setDeleteConfirmId}
              />
            ))}
          </ul>
        )}
      </div>

      {/* 選取狀態提示 */}
      {selectedCount > 0 && (
        <div className="flex-shrink-0 p-3 bg-blue-50 border-t border-blue-200">
          <div className="flex items-center justify-between">
            <span className="text-sm text-blue-700">
              已選取 {selectedCount} 篇論文，可開始進行查詢分析
            </span>
            <button
              onClick={handleDeselectAll}
              className="text-sm text-blue-600 hover:text-blue-800 underline"
            >
              清除選取
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default PaperSelectionPanel; 