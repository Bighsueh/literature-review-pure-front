import React, { useState } from 'react';
import { Message, SelectedSection, Reference } from '../../types/chat';
import { 
  DocumentTextIcon, 
  InformationCircleIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  SparklesIcon,
  BookOpenIcon,
  ListBulletIcon,
  FolderIcon
} from '@heroicons/react/24/outline';

interface StrategyDisplayProps {
  selectedMessage: Message | null;
  visible: boolean;
}

// 策略類型對應的中文描述和圖標
const STRATEGY_CONFIG = {
  'locate_info': {
    name: '資訊定位與檢索',
    description: '找到原文句子、段落、章節或頁碼',
    icon: ListBulletIcon,
    color: 'blue'
  },
  'understand_content': {
    name: '內容理解與深度閱讀', 
    description: '深入解析單篇論文的定義、量測方法、研究動機',
    icon: BookOpenIcon,
    color: 'purple'
  },
  'cross_paper': {
    name: '跨文獻比較與整合',
    description: '生成跨篇比較表、整合研究空缺',
    icon: FolderIcon,
    color: 'green'
  },
  'definitions': {
    name: '概念/操作定義分析',
    description: '著重概念型與操作型定義的差異與演進',
    icon: SparklesIcon,
    color: 'indigo'
  },
  'methods': {
    name: '方法論比較',
    description: '著重方法論、量測工具的比較',
    icon: DocumentTextIcon,
    color: 'orange'
  },
  'results': {
    name: '研究結果對比',
    description: '著重主要發現、統計結果的差異',
    icon: DocumentTextIcon,
    color: 'red'
  },
  'comparison': {
    name: '理論框架對照',
    description: '著重理論框架或研究觀點的對照',
    icon: DocumentTextIcon,
    color: 'pink'
  }
} as const;

// Focus Type 的中文對應
const FOCUS_TYPE_CONFIG = {
  'definitions': { name: '定義句子', color: 'purple' },
  'key_sentences': { name: '關鍵句子', color: 'blue' },
  'deep_summary': { name: '深度摘要', color: 'green' },
  'cross_table': { name: '跨篇比較表', color: 'orange' },
  'full_section': { name: '完整章節', color: 'gray' }
} as const;

const StrategyDisplay: React.FC<StrategyDisplayProps> = ({ selectedMessage, visible }) => {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());
  const [showReferences, setShowReferences] = useState(true);

  const toggleSectionExpansion = (sectionKey: string) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(sectionKey)) {
      newExpanded.delete(sectionKey);
    } else {
      newExpanded.add(sectionKey);
    }
    setExpandedSections(newExpanded);
  };

  if (!visible || !selectedMessage || selectedMessage.type !== 'system') {
    return (
      <div className="p-6 text-center text-gray-500">
        <InformationCircleIcon className="h-12 w-12 mx-auto mb-3 text-gray-300" />
        <h3 className="text-lg font-medium text-gray-700 mb-2">等待選擇回答</h3>
        <p className="text-sm">點擊左側系統回答以查看AI策略和引用詳情</p>
      </div>
    );
  }

  const { strategy_info, references, source_summary } = selectedMessage;

  // 如果沒有策略資訊，顯示基本資訊
  if (!strategy_info) {
    return (
      <div className="p-6">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex items-center">
            <InformationCircleIcon className="h-5 w-5 text-yellow-600 mr-2" />
            <p className="text-sm text-yellow-800">此回答暫無策略資訊</p>
          </div>
        </div>
        
        {references && references.length > 0 && (
          <div className="mt-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">引用來源</h3>
            <div className="space-y-3">
              {references.map((ref, index) => (
                <ReferenceCard key={ref.id} reference={ref} index={index} />
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  const strategyConfig = STRATEGY_CONFIG[strategy_info.analysis_focus as keyof typeof STRATEGY_CONFIG] || {
    name: strategy_info.analysis_focus,
    description: strategy_info.suggested_approach,
    icon: DocumentTextIcon,
    color: 'gray'
  };

  const StrategyIcon = strategyConfig.icon;

  return (
    <div className="p-6 space-y-6">
      {/* 策略資訊卡片 */}
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm">
        <div className="p-4 border-b border-gray-100">
          <div className="flex items-start">
            <div className={`p-2 rounded-lg bg-${strategyConfig.color}-100 mr-4`}>
              <StrategyIcon className={`h-6 w-6 text-${strategyConfig.color}-600`} />
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-gray-900">
                {strategyConfig.name}
              </h3>
              <p className="text-sm text-gray-600 mt-1">
                {strategyConfig.description}
              </p>
              {strategy_info.fallback_mode && (
                <div className="mt-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-800">
                  降級模式
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="p-4">
          <h4 className="text-sm font-medium text-gray-700 mb-2">AI 分析方法</h4>
          <p className="text-sm text-gray-600 bg-gray-50 p-3 rounded-md">
            {strategy_info.suggested_approach}
          </p>
        </div>
      </div>

      {/* 選中章節資訊 */}
      {strategy_info.selected_sections && strategy_info.selected_sections.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg shadow-sm">
          <div className="p-4 border-b border-gray-100">
            <h3 className="text-lg font-semibold text-gray-900">
              選中章節 ({strategy_info.selected_sections.length})
            </h3>
          </div>
          
          <div className="divide-y divide-gray-100">
            {strategy_info.selected_sections.map((section, index) => (
              <SectionCard 
                key={`${section.paper_name}-${section.section_type}-${index}`}
                section={section}
                isExpanded={expandedSections.has(`section-${index}`)}
                onToggle={() => toggleSectionExpansion(`section-${index}`)}
              />
            ))}
          </div>
        </div>
      )}

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

// 章節卡片組件
const SectionCard: React.FC<{
  section: SelectedSection;
  isExpanded: boolean;
  onToggle: () => void;
}> = ({ section, isExpanded, onToggle }) => {
  const focusConfig = FOCUS_TYPE_CONFIG[section.focus_type as keyof typeof FOCUS_TYPE_CONFIG] || {
    name: section.focus_type,
    color: 'gray'
  };

  return (
    <div className="p-4">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center space-x-2 mb-2">
            <h4 className="font-medium text-gray-900">{section.paper_name}</h4>
            <span className="text-xs text-gray-500">•</span>
            <span className="text-sm text-gray-600">{section.section_type}</span>
            {section.page_num && (
              <>
                <span className="text-xs text-gray-500">•</span>
                <span className="text-sm text-gray-600">第 {section.page_num} 頁</span>
              </>
            )}
          </div>
          
          <div className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-${focusConfig.color}-100 text-${focusConfig.color}-800`}>
            {focusConfig.name}
          </div>
        </div>
        
        <button
          onClick={onToggle}
          className="ml-2 p-1 text-gray-400 hover:text-gray-600"
        >
          {isExpanded ? (
            <ChevronUpIcon className="h-4 w-4" />
          ) : (
            <ChevronDownIcon className="h-4 w-4" />
          )}
        </button>
      </div>

      {isExpanded && (
        <div className="mt-3 space-y-3">
          <div>
            <p className="text-xs font-medium text-gray-700 mb-1">選擇原因：</p>
            <p className="text-sm text-gray-600 bg-gray-50 p-2 rounded">
              {section.selection_reason}
            </p>
          </div>
          
          {section.keywords && section.keywords.length > 0 && (
            <div>
              <p className="text-xs font-medium text-gray-700 mb-2">關鍵詞：</p>
              <div className="flex flex-wrap gap-1">
                {section.keywords.map((keyword, index) => (
                  <span 
                    key={index}
                    className="inline-block px-2 py-1 text-xs bg-yellow-100 text-yellow-800 rounded"
                  >
                    {keyword}
                  </span>
                ))}
              </div>
            </div>
          )}
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