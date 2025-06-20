/**
 * 工作區檔案列表組件 - FE-04 檔案管理系統重構
 * 支援工作區隔離的檔案管理和批量操作
 */

import React, { useEffect, useState, useCallback, useMemo } from 'react';
import {
  DocumentTextIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  ArrowPathIcon,
  TrashIcon,
  XMarkIcon,
  ClockIcon,
  CheckIcon,
  MinusIcon,
  FunnelIcon,
  MagnifyingGlassIcon,
  ArrowsUpDownIcon
} from '@heroicons/react/24/outline';
import { CheckIcon as CheckIconSolid } from '@heroicons/react/24/solid';
import { useWorkspaceFileStore } from '../../stores/workspace/workspaceFileStore';
import { useWorkspaceContext } from '../../contexts/WorkspaceContext';
import { Paper } from '../../types/api';
import LoadingSpinner from '../common/LoadingSpinner';

interface WorkspaceFileListProps {
  className?: string;
  onFileSelect?: (paperId: string) => void;
  showSelection?: boolean;
  enableBatchOperations?: boolean;
  compact?: boolean;
}

// 排序和篩選選項
type SortOption = 'name' | 'date' | 'size' | 'status';
type SortDirection = 'asc' | 'desc';
type StatusFilter = 'all' | 'pending' | 'processing' | 'completed' | 'failed';

// 檔案列表標題組件
const FileListHeader: React.FC<{
  totalCount: number;
  selectedCount: number;
  isAllSelected: boolean;
  isPartialSelected: boolean;
  onSelectAll: () => void;
  onDeselectAll: () => void;
  onBatchDelete: () => void;
  isLoading: boolean;
  showSelection: boolean;
  enableBatchOperations: boolean;
}> = ({ 
  totalCount, 
  selectedCount, 
  isAllSelected, 
  isPartialSelected, 
  onSelectAll, 
  onDeselectAll,
  onBatchDelete,
  isLoading,
  showSelection,
  enableBatchOperations
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
          {showSelection && (
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
          )}
          <div>
            <h3 className="text-sm font-medium text-gray-900">工作區檔案</h3>
            <p className="text-xs text-gray-500">
              {showSelection ? `已選取 ${selectedCount} / ${totalCount}` : `共 ${totalCount}`} 個檔案
            </p>
          </div>
        </div>
        
        {/* 批量操作按鈕 */}
        {enableBatchOperations && selectedCount > 0 && (
          <div className="flex items-center space-x-2">
            <span className="text-xs text-blue-600 font-medium">
              {selectedCount} 個已選取
            </span>
            <button
              onClick={onBatchDelete}
              className="p-1.5 text-red-600 hover:bg-red-100 rounded-md transition-colors"
              title="刪除選取的檔案"
            >
              <TrashIcon className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

// 搜尋和篩選控制組件
const FileListControls: React.FC<{
  searchQuery: string;
  onSearchChange: (query: string) => void;
  sortOption: SortOption;
  sortDirection: SortDirection;
  onSortChange: (option: SortOption, direction: SortDirection) => void;
  statusFilter: StatusFilter;
  onStatusFilterChange: (filter: StatusFilter) => void;
  compact: boolean;
}> = ({
  searchQuery,
  onSearchChange,
  sortOption,
  sortDirection,
  onSortChange,
  statusFilter,
  onStatusFilterChange,
  compact
}) => {
  const [showFilters, setShowFilters] = useState(false);

  const sortOptions = [
    { value: 'name', label: '名稱' },
    { value: 'date', label: '日期' },
    { value: 'size', label: '大小' },
    { value: 'status', label: '狀態' }
  ] as const;

  const statusOptions = [
    { value: 'all', label: '全部' },
    { value: 'pending', label: '等待中' },
    { value: 'processing', label: '處理中' },
    { value: 'completed', label: '已完成' },
    { value: 'failed', label: '失敗' }
  ] as const;

  if (compact) {
    return (
      <div className="p-2 border-b border-gray-200 bg-white">
        <div className="flex items-center space-x-2">
          {/* 緊湊型搜尋 */}
          <div className="flex-1 relative">
            <MagnifyingGlassIcon className="absolute left-2 top-2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="搜尋檔案..."
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          
          {/* 篩選按鈕 */}
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="p-1.5 text-gray-600 hover:bg-gray-100 rounded-md"
          >
            <FunnelIcon className="w-4 h-4" />
          </button>
        </div>
        
        {/* 展開的篩選選項 */}
        {showFilters && (
          <div className="mt-2 p-2 bg-gray-50 rounded-md space-y-2">
            <select
              value={statusFilter}
              onChange={(e) => onStatusFilterChange(e.target.value as StatusFilter)}
              className="w-full text-xs border border-gray-300 rounded px-2 py-1"
            >
              {statusOptions.map(option => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="p-3 border-b border-gray-200 bg-white space-y-3">
      {/* 搜尋欄 */}
      <div className="relative">
        <MagnifyingGlassIcon className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
        <input
          type="text"
          placeholder="搜尋檔案名稱..."
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
      </div>
      
      {/* 排序和篩選控制 */}
      <div className="flex items-center space-x-3">
        {/* 排序控制 */}
        <div className="flex items-center space-x-2">
          <ArrowsUpDownIcon className="w-4 h-4 text-gray-400" />
          <select
            value={sortOption}
            onChange={(e) => onSortChange(e.target.value as SortOption, sortDirection)}
            className="text-sm border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            {sortOptions.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          
          <button
            onClick={() => onSortChange(sortOption, sortDirection === 'asc' ? 'desc' : 'asc')}
            className="p-1 text-gray-600 hover:bg-gray-100 rounded"
          >
            {sortDirection === 'asc' ? '↑' : '↓'}
          </button>
        </div>
        
        {/* 狀態篩選 */}
        <div className="flex items-center space-x-2">
          <FunnelIcon className="w-4 h-4 text-gray-400" />
          <select
            value={statusFilter}
            onChange={(e) => onStatusFilterChange(e.target.value as StatusFilter)}
            className="text-sm border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            {statusOptions.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
};

// 單個檔案項目組件
const FileItem: React.FC<{
  paper: Paper;
  isSelected: boolean;
  onToggleSelection: (paperId: string) => void;
  onDelete: (paperId: string) => void;
  onFileSelect?: (paperId: string) => void;
  deleteConfirmId: string | null;
  setDeleteConfirmId: (id: string | null) => void;
  showSelection: boolean;
  compact: boolean;
}> = ({ 
  paper, 
  isSelected, 
  onToggleSelection, 
  onDelete, 
  onFileSelect,
  deleteConfirmId, 
  setDeleteConfirmId,
  showSelection,
  compact
}) => {
  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    if (compact) {
      return date.toLocaleDateString('zh-TW', { month: '2-digit', day: '2-digit' });
    }
    return date.toLocaleString('zh-TW', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getStatusInfo = (status: Paper['processing_status']) => {
    switch (status) {
      case 'completed':
        return { 
          icon: <CheckCircleIcon className={`${compact ? 'h-4 w-4' : 'h-5 w-5'} text-green-500`} />, 
          text: '已完成',
          className: 'bg-green-100 text-green-800'
        };
      case 'failed':
        return { 
          icon: <ExclamationTriangleIcon className={`${compact ? 'h-4 w-4' : 'h-5 w-5'} text-red-500`} />, 
          text: '失敗',
          className: 'bg-red-100 text-red-800'
        };
      case 'processing':
        return { 
          icon: <ArrowPathIcon className={`${compact ? 'h-4 w-4' : 'h-5 w-5'} text-blue-500 animate-spin`} />, 
          text: '處理中',
          className: 'bg-blue-100 text-blue-800'
        };
      case 'pending':
      default:
        return { 
          icon: <ClockIcon className={`${compact ? 'h-4 w-4' : 'h-5 w-5'} text-gray-500`} />, 
          text: '等待',
          className: 'bg-gray-100 text-gray-800'
        };
    }
  };

  const handleItemClick = useCallback(() => {
    if (onFileSelect) {
      onFileSelect(paper.id);
    }
  }, [paper.id, onFileSelect]);

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

  const handleToggleClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    onToggleSelection(paper.id);
  }, [paper.id, onToggleSelection]);

  const statusInfo = getStatusInfo(paper.processing_status);

  return (
    <li 
      className={`${compact ? 'p-2' : 'p-3'} hover:bg-gray-50 transition-colors duration-150 cursor-pointer`}
      onClick={handleItemClick}
    >
      <div className={`flex items-center ${compact ? 'space-x-2' : 'space-x-3'}`}>
        {/* 選取 Checkbox */}
        {showSelection && (
          <button
            onClick={handleToggleClick}
            className={`flex items-center justify-center ${compact ? 'w-4 h-4' : 'w-5 h-5'} border-2 rounded transition-colors duration-150 hover:border-blue-400`}
            style={{
              borderColor: isSelected ? '#3B82F6' : '#D1D5DB',
              backgroundColor: isSelected ? '#3B82F6' : 'transparent'
            }}
          >
            {isSelected && (
              <CheckIconSolid className={`${compact ? 'w-2.5 h-2.5' : 'w-3 h-3'} text-white`} />
            )}
          </button>
        )}

        {/* 文件圖標 */}
        <div className="flex-shrink-0 text-gray-400">
          <DocumentTextIcon className={`${compact ? 'h-5 w-5' : 'h-6 w-6'}`} />
        </div>

        {/* 檔案資訊 */}
        <div className="flex-1 min-w-0">
          <p className={`${compact ? 'text-xs' : 'text-sm'} font-medium text-gray-900 truncate`} title={paper.title}>
            {paper.title}
          </p>
          <div className={`${compact ? 'text-xs' : 'text-sm'} text-gray-500 space-y-0.5`}>
            <p>{formatDate(paper.upload_time)}</p>
            {!compact && paper.file_size && (
              <p>{formatFileSize(paper.file_size)}</p>
            )}
          </div>
        </div>

        {/* 狀態和操作 */}
        <div className="flex-shrink-0 flex items-center space-x-2">
          {/* 狀態標籤 */}
          <span className={`inline-flex items-center ${compact ? 'px-1.5 py-0.5 text-xs' : 'px-2.5 py-0.5 text-xs'} rounded-full font-medium ${statusInfo.className}`}>
            {compact ? statusInfo.icon : statusInfo.text}
          </span>

          {/* 刪除按鈕 */}
          {deleteConfirmId === paper.id ? (
            <div className="flex items-center space-x-1" onClick={(e) => e.stopPropagation()}>
              <button
                onClick={confirmDelete}
                className="p-1 text-red-600 hover:bg-red-100 rounded transition-colors"
                title="確認刪除"
              >
                <CheckIcon className="w-4 h-4" />
              </button>
              <button
                onClick={cancelDelete}
                className="p-1 text-gray-600 hover:bg-gray-100 rounded transition-colors"
                title="取消刪除"
              >
                <XMarkIcon className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <button
              onClick={handleDeleteClick}
              className="p-1 text-gray-400 hover:text-red-600 hover:bg-red-100 rounded transition-colors"
              title="刪除檔案"
            >
              <TrashIcon className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </li>
  );
};

// 主要的工作區檔案列表組件
const WorkspaceFileList: React.FC<WorkspaceFileListProps> = ({
  className = '',
  onFileSelect,
  showSelection = true,
  enableBatchOperations = true,
  compact = false
}) => {
  const { currentWorkspace } = useWorkspaceContext();
  const { 
    papers, 
    selectedPaperIds, 
    isLoading, 
    error,
    refreshPapers,
    togglePaperSelection,
    setBatchSelection,
    clearSelection,
    selectAll,
    deletePaper
  } = useWorkspaceFileStore(currentWorkspace?.id || '');

  // 本地狀態
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortOption, setSortOption] = useState<SortOption>('date');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');

  // 初始化時載入檔案
  useEffect(() => {
    if (currentWorkspace?.id) {
      refreshPapers();
    }
  }, [currentWorkspace?.id, refreshPapers]);

  // 篩選和排序邏輯
  const filteredAndSortedPapers = useMemo(() => {
    let filtered = papers;

    // 搜尋篩選
    if (searchQuery) {
      filtered = filtered.filter(paper =>
        paper.title.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }

    // 狀態篩選
    if (statusFilter !== 'all') {
      filtered = filtered.filter(paper => paper.processing_status === statusFilter);
    }

    // 排序
    filtered.sort((a, b) => {
      let comparison = 0;
      
      switch (sortOption) {
        case 'name':
          comparison = a.title.localeCompare(b.title);
          break;
        case 'date':
          comparison = new Date(a.upload_time).getTime() - new Date(b.upload_time).getTime();
          break;
        case 'size':
          comparison = (a.file_size || 0) - (b.file_size || 0);
          break;
        case 'status':
          const statusOrder = { pending: 0, processing: 1, completed: 2, failed: 3 };
          comparison = statusOrder[a.processing_status] - statusOrder[b.processing_status];
          break;
      }
      
      return sortDirection === 'asc' ? comparison : -comparison;
    });

    return filtered;
  }, [papers, searchQuery, statusFilter, sortOption, sortDirection]);

  // 選擇狀態計算
  const selectedCount = selectedPaperIds.size;
  const totalCount = filteredAndSortedPapers.length;
  const isAllSelected = totalCount > 0 && selectedCount === totalCount;
  const isPartialSelected = selectedCount > 0 && selectedCount < totalCount;

  // 事件處理器
  const handleSelectAll = useCallback(() => {
    const allIds = filteredAndSortedPapers.map(p => p.id);
    setBatchSelection(allIds, true);
  }, [filteredAndSortedPapers, setBatchSelection]);

  const handleDeselectAll = useCallback(() => {
    clearSelection();
  }, [clearSelection]);

  const handleBatchDelete = useCallback(async () => {
    if (selectedCount === 0) return;
    
    const confirmed = window.confirm(`確定要刪除 ${selectedCount} 個檔案嗎？`);
    if (!confirmed) return;

    const selectedIds = Array.from(selectedPaperIds);
    
    for (const paperId of selectedIds) {
      try {
        await deletePaper(paperId);
      } catch (error) {
        console.error(`Failed to delete paper ${paperId}:`, error);
      }
    }
    
    clearSelection();
  }, [selectedCount, selectedPaperIds, deletePaper, clearSelection]);

  const handleSortChange = useCallback((option: SortOption, direction: SortDirection) => {
    setSortOption(option);
    setSortDirection(direction);
  }, []);

  if (!currentWorkspace) {
    return (
      <div className="flex items-center justify-center h-32 text-gray-500">
        請選擇工作區
      </div>
    );
  }

  if (isLoading && papers.length === 0) {
    return (
      <div className="flex items-center justify-center h-32">
        <LoadingSpinner />
        <span className="ml-2 text-gray-600">載入檔案中...</span>
      </div>
    );
  }

  return (
    <div className={`h-full flex flex-col bg-white ${className}`}>
      {/* 標題區 */}
      <FileListHeader
        totalCount={totalCount}
        selectedCount={selectedCount}
        isAllSelected={isAllSelected}
        isPartialSelected={isPartialSelected}
        onSelectAll={handleSelectAll}
        onDeselectAll={handleDeselectAll}
        onBatchDelete={handleBatchDelete}
        isLoading={isLoading}
        showSelection={showSelection}
        enableBatchOperations={enableBatchOperations}
      />

      {/* 搜尋和篩選控制 */}
      <FileListControls
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        sortOption={sortOption}
        sortDirection={sortDirection}
        onSortChange={handleSortChange}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        compact={compact}
      />

      {/* 錯誤提示 */}
      {error && (
        <div className="p-3 bg-red-50 border-l-4 border-red-400">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* 檔案列表 */}
      <div className="flex-1 overflow-y-auto">
        {filteredAndSortedPapers.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-32 text-gray-500">
            <DocumentTextIcon className="w-12 h-12 mb-2" />
            <p>{searchQuery || statusFilter !== 'all' ? '沒有符合條件的檔案' : '尚無檔案'}</p>
          </div>
        ) : (
          <ul className="divide-y divide-gray-200">
            {filteredAndSortedPapers.map((paper) => (
              <FileItem
                key={paper.id}
                paper={paper}
                isSelected={selectedPaperIds.has(paper.id)}
                onToggleSelection={togglePaperSelection}
                onDelete={deletePaper}
                onFileSelect={onFileSelect}
                deleteConfirmId={deleteConfirmId}
                setDeleteConfirmId={setDeleteConfirmId}
                showSelection={showSelection}
                compact={compact}
              />
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};

export default WorkspaceFileList;