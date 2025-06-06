import React from 'react';
import { SourceSummary as SourceSummaryType } from '../../../types/chat';
import { DocumentTextIcon, ChartBarIcon } from '@heroicons/react/24/outline';

interface SourceSummaryProps {
  sourceSummary: SourceSummaryType;
  className?: string;
}

const SourceSummary: React.FC<SourceSummaryProps> = ({ 
  sourceSummary, 
  className = '' 
}) => {
  const getAnalysisTypeText = (type?: string) => {
    switch (type) {
      case 'definition_comparison':
        return '定義比較分析';
      case 'methods':
        return '方法論分析';
      case 'results':
        return '結果分析';
      case 'comparison':
        return '比較分析';
      default:
        return '綜合分析';
    }
  };

  const getAnalysisTypeColor = (type?: string) => {
    switch (type) {
      case 'definition_comparison':
        return 'bg-blue-50 text-blue-700 border-blue-200';
      case 'methods':
        return 'bg-green-50 text-green-700 border-green-200';
      case 'results':
        return 'bg-purple-50 text-purple-700 border-purple-200';
      case 'comparison':
        return 'bg-orange-50 text-orange-700 border-orange-200';
      default:
        return 'bg-gray-50 text-gray-700 border-gray-200';
    }
  };

  return (
    <div className={`border rounded-lg p-3 bg-gray-50 ${className}`}>
      <div className="flex items-center mb-2">
        <ChartBarIcon className="h-4 w-4 text-gray-500 mr-2" />
        <h4 className="text-sm font-medium text-gray-700">來源摘要</h4>
      </div>
      
      <div className="space-y-2">
        {/* 分析類型 */}
        {sourceSummary.analysis_type && (
          <div className="flex items-center">
            <span className="text-xs text-gray-500 mr-2">分析類型:</span>
            <span className={`text-xs px-2 py-1 rounded-full border ${getAnalysisTypeColor(sourceSummary.analysis_type)}`}>
              {getAnalysisTypeText(sourceSummary.analysis_type)}
            </span>
          </div>
        )}
        
        {/* 論文統計 */}
        <div className="flex items-center justify-between text-xs text-gray-600">
          <div className="flex items-center">
            <DocumentTextIcon className="h-3 w-3 mr-1" />
            <span>使用論文: {sourceSummary.total_papers} 篇</span>
          </div>
          
          {sourceSummary.sections_analyzed && sourceSummary.sections_analyzed.length > 0 && (
            <span>分析章節: {sourceSummary.sections_analyzed.length} 個</span>
          )}
        </div>
        
        {/* 論文清單 */}
        {sourceSummary.papers_used.length > 0 && (
          <div>
            <span className="text-xs text-gray-500 block mb-1">引用論文:</span>
            <div className="flex flex-wrap gap-1">
              {sourceSummary.papers_used.map((paper, index) => (
                <span 
                  key={index}
                  className="text-xs bg-white text-gray-600 px-2 py-1 rounded border"
                  title={paper}
                >
                  {paper.length > 20 ? `${paper.substring(0, 17)}...` : paper}
                </span>
              ))}
            </div>
          </div>
        )}
        
        {/* 分析章節 */}
        {sourceSummary.sections_analyzed && sourceSummary.sections_analyzed.length > 0 && (
          <div>
            <span className="text-xs text-gray-500 block mb-1">分析章節類型:</span>
            <div className="flex flex-wrap gap-1">
              {sourceSummary.sections_analyzed.map((section, index) => (
                <span 
                  key={index}
                  className="text-xs bg-blue-50 text-blue-700 px-2 py-1 rounded border border-blue-200"
                >
                  {section}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default SourceSummary; 