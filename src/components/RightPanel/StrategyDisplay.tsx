import React, { useState } from 'react';
import { Message, Reference } from '../../types/chat';
import { 
  InformationCircleIcon,
  ChevronDownIcon,
  ChevronUpIcon
} from '@heroicons/react/24/outline';

interface StrategyDisplayProps {
  selectedMessage: Message | null;
  visible: boolean;
}

// 策略類型對應的中文描述和圖標


const StrategyDisplay: React.FC<StrategyDisplayProps> = ({ selectedMessage, visible }) => {
  const [showReferences, setShowReferences] = useState(true);

  if (!visible || !selectedMessage || selectedMessage.type !== 'system') {
    return (
      <div className="p-6 text-center text-gray-500">
        <InformationCircleIcon className="h-12 w-12 mx-auto mb-3 text-gray-300" />
        <h3 className="text-lg font-medium text-gray-700 mb-2">等待選擇回答</h3>
        <p className="text-sm">點擊左側系統回答以查看AI策略和引用詳情</p>
      </div>
    );
  }

  const { references, source_summary } = selectedMessage;

  if ((!references || references.length === 0) && !source_summary) {
    return (
      <div className="p-6 text-center text-gray-500">
        <InformationCircleIcon className="h-12 w-12 mx-auto mb-3 text-gray-300" />
        <h3 className="text-lg font-medium text-gray-700 mb-2">無引用或摘要資訊</h3>
        <p className="text-sm">此回答沒有可顯示的引用或來源摘要。</p>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">

      {/* 引用句子詳情 */}
      {references && references.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg shadow-sm">
          <div className="p-4 border-b border-gray-100">
            <button
              onClick={() => setShowReferences(!showReferences)}
              className="flex items-center justify-between w-full text-left"
            >
              <h3 className="text-lg font-semibold text-gray-900">
                引用句子 ({references.length})
              </h3>
              {showReferences ? (
                <ChevronUpIcon className="h-5 w-5 text-gray-500" />
              ) : (
                <ChevronDownIcon className="h-5 w-5 text-gray-500" />
              )}
            </button>
          </div>
          
          {showReferences && (
            <div className="divide-y divide-gray-100">
              {references.map((ref, index) => (
                <ReferenceCard key={ref.id} reference={ref} index={index} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* 來源摘要 */}
      {source_summary && (
        <div className="bg-white border border-gray-200 rounded-lg shadow-sm">
          <div className="p-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">來源摘要</h3>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-600">分析論文數：</span>
                <span className="font-medium ml-1">{source_summary.total_papers}</span>
              </div>
              <div>
                <span className="text-gray-600">使用檔案：</span>
                <span className="font-medium ml-1">{source_summary.papers_used.length}</span>
              </div>
            </div>
            {source_summary.papers_used.length > 0 && (
              <div className="mt-3">
                <p className="text-xs text-gray-600 mb-2">使用的論文檔案：</p>
                <div className="flex flex-wrap gap-1">
                  {source_summary.papers_used.map((paper, index) => (
                    <span 
                      key={index}
                      className="inline-block px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded"
                    >
                      {paper}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

// 引用卡片組件
const ReferenceCard: React.FC<{
  reference: Reference;
  index: number;
}> = ({ reference, index }) => {
  const fileName = reference.paper_name || reference.file_name || '未知檔案';
  const section = reference.section_type || reference.section || '未知章節';
  const content = reference.content_snippet || reference.sentence || '無內容預覽';

  return (
    <div className="p-4">
      <div className="flex items-start space-x-3">
        <div className="flex-shrink-0">
          <div className="w-6 h-6 bg-blue-100 text-blue-800 rounded-full flex items-center justify-center text-xs font-medium">
            {index + 1}
          </div>
        </div>
        
        <div className="flex-1 min-w-0">
          <div className="flex items-center space-x-2 mb-1">
            <h4 className="text-sm font-medium text-gray-900 truncate">{fileName}</h4>
            {reference.type && (
              <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium ${
                reference.type === 'OD' 
                  ? 'bg-blue-100 text-blue-800' 
                  : reference.type === 'CD'
                  ? 'bg-purple-100 text-purple-800'
                  : 'bg-gray-100 text-gray-800'
              }`}>
                {reference.type}
              </span>
            )}
          </div>
          
          <div className="text-xs text-gray-600 mb-2">
            {section} • 第 {reference.page_num} 頁
          </div>
          
          <div className="text-sm text-gray-700 bg-gray-50 p-2 rounded">
            {content.length > 150 ? `${content.substring(0, 150)}...` : content}
          </div>
        </div>
      </div>
    </div>
  );
};

export default StrategyDisplay; 