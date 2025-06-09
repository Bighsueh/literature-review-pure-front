import React, { useEffect, useState } from 'react';
import {
  DocumentTextIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  ArrowPathIcon,
  TrashIcon,
  XMarkIcon,
  ClockIcon,
  CheckIcon
} from '@heroicons/react/24/outline';
import { useAppStore } from '../../../stores/app_store';
import { PaperInfo } from '../../../services/api_service';

interface PaperSelectionPanelProps {
  className?: string;
}

const PaperSelectionPanel: React.FC<PaperSelectionPanelProps> = ({ className = '' }) => {
  const {
    papers,
    ui,
    refreshPapers,
    deletePaper,
    clearError
  } = useAppStore();

  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  useEffect(() => {
    refreshPapers();
    const interval = setInterval(refreshPapers, 5000); // 每5秒刷新一次，更頻繁地檢查狀態
    return () => clearInterval(interval);
  }, [refreshPapers]);

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
            {papers.list.map((paper) => {
              const statusInfo = getStatusInfo(paper.processing_status);
              return (
                <li key={paper.id} className="p-3 hover:bg-gray-50 transition-colors duration-150">
                  <div className="flex items-center space-x-3">
                    <div className="flex-shrink-0 text-gray-400">
                      <DocumentTextIcon className="h-6 w-6" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate" title={paper.title}>
                        {paper.title}
                      </p>
                      <p className="text-sm text-gray-500">
                        {formatDate(paper.upload_time)}
                      </p>
                    </div>
                    <div className="flex-shrink-0 flex items-center space-x-2">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusInfo.className}`}>
                        {statusInfo.text}
                      </span>
                      {deleteConfirmId === paper.id ? (
                        <div className="flex items-center space-x-1">
                           <button onClick={(e) => confirmDelete(e, paper.id)} className="p-1 text-green-600 hover:text-green-800">
                            <CheckIcon className="h-4 w-4"/>
                          </button>
                          <button onClick={cancelDelete} className="p-1 text-red-600 hover:text-red-800">
                            <XMarkIcon className="h-4 w-4"/>
                          </button>
                        </div>
                      ) : (
                        <button onClick={(e) => handleDeleteClick(e, paper.id)} className="p-1 text-gray-400 hover:text-red-600">
                          <TrashIcon className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
};

export default PaperSelectionPanel; 