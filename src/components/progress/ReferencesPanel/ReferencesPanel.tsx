import React from 'react';
import { useAppStore } from '../../../stores/appStore';

interface ReferencesPanelProps {
  onViewInPDF?: (sentenceId: string) => void;
}

const ReferencesPanel: React.FC<ReferencesPanelProps> = ({ onViewInPDF }) => {
  const { selectedReferences } = useAppStore();
  
  const getTypeLabel = (type: string) => {
    switch (type) {
      case 'OD': return '操作型定義';
      case 'CD': return '概念型定義';
      default: return '其他';
    }
  };
  
  const getTypeColor = (type: string) => {
    switch (type) {
      case 'OD': return 'bg-blue-100 text-blue-800';
      case 'CD': return 'bg-purple-100 text-purple-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };
  
  if (selectedReferences.length === 0) {
    return (
      <div className="p-4 text-center text-gray-500">
        <p>尚未選擇任何引用句子</p>
        <p className="text-sm mt-2">點擊回答中的引用來查看詳情</p>
      </div>
    );
  }

  return (
    <div className="overflow-y-auto">
      <div className="p-4">
        <h3 className="text-lg font-medium text-gray-900 mb-4">引用原文</h3>
        
        {selectedReferences.map((reference) => (
          <div 
            key={reference.id} 
            className="mb-4 p-3 bg-white rounded-lg shadow-sm border border-gray-200"
          >
            <div className="flex justify-between items-start mb-2">
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${getTypeColor(reference.type)}`}>
                {getTypeLabel(reference.type)}
              </span>
              
              <button
                className="text-xs text-blue-600 hover:text-blue-800"
                onClick={() => onViewInPDF?.(reference.id)}
              >
                在 PDF 中查看
              </button>
            </div>
            
            <p className="text-sm text-gray-800 mb-2">{reference.content}</p>
            
            {reference.reason && (
              <div className="text-xs text-gray-600 border-t pt-2 mt-2">
                <p className="font-medium">分類原因:</p>
                <p className="mt-1 italic">{reference.reason}</p>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default ReferencesPanel;
