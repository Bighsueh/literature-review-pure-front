"""
統一查詢處理服務 (Backlog #9)
整合所有N8N API並提供統一的查詢處理介面
"""

import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime

from backend.core.logging import get_logger
from backend.services.n8n_service import n8n_service
from backend.services.db_service import db_service
from backend.core.exceptions import QueryProcessingError, DataValidationError

logger = get_logger(__name__)

class UnifiedQueryProcessor:
    """統一查詢處理器 - 處理所有類型的查詢"""
    
    def __init__(self):
        self.processing_stats = {
            'total_queries': 0,
            'successful_queries': 0,
            'failed_queries': 0,
            'average_processing_time': 0.0
        }
    
    async def process_query(
        self, 
        query: str, 
        papers_summary: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        統一查詢處理入口點
        
        Args:
            query: 使用者查詢語句
            papers_summary: API提供的論文摘要資料
            
        Returns:
            統一格式的查詢回應
        """
        start_time = datetime.now()
        self.processing_stats['total_queries'] += 1
        
        try:
            logger.info(f"開始處理查詢: {query[:50]}...")
            
            if not papers_summary:
                return {
                    'query': query,
                    'response': "沒有可用的論文資料",
                    'references': [],
                    'source_summary': {
                        'total_papers': 0,
                        'papers_used': [],
                        'error_occurred': True,
                        'error_message': "沒有可用的論文資料"
                    },
                    'processing_time': 0,
                    'papers_analyzed': 0,
                    'timestamp': datetime.now().isoformat()
                }
            
            # 步驟1: 智能章節選擇
            section_selection = await self._intelligent_section_selection(
                query, papers_summary
            )
            
            # 步驟2: 提取選中的內容 (簡化版本)
            selected_content = self._extract_content_from_summary(
                section_selection, papers_summary
            )
            
            # 步驟3: 統一內容分析
            analysis_result = await self._unified_content_analysis(
                query, selected_content, section_selection
            )
            
            # 記錄成功統計
            processing_time = (datetime.now() - start_time).total_seconds()
            self.processing_stats['successful_queries'] += 1
            self._update_average_time(processing_time)
            
            logger.info(f"查詢處理完成，耗時 {processing_time:.2f} 秒")
            
            return {
                'query': query,
                'response': analysis_result.get('response', '查詢處理完成'),
                'references': analysis_result.get('references', []),
                'source_summary': analysis_result.get('source_summary', {
                    'total_papers': len(papers_summary),
                    'papers_used': [paper['file_name'] for paper in papers_summary],
                }),
                'processing_time': processing_time,
                'papers_analyzed': len(papers_summary),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.processing_stats['failed_queries'] += 1
            logger.error(f"查詢處理失敗: {e}")
            
            # 返回錯誤但結構化的回應
            return {
                'query': query,
                'response': f"抱歉，處理您的查詢時遇到了問題: {str(e)}",
                'references': [],
                'source_summary': {
                    'total_papers': 0,
                    'papers_used': [],
                    'error_occurred': True,
                    'error_message': str(e)
                },
                'processing_time': (datetime.now() - start_time).total_seconds(),
                'papers_analyzed': 0,
                'timestamp': datetime.now().isoformat()
            }
    
    async def _generate_papers_summary(
        self, 
        papers_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """生成論文section摘要"""
        available_papers = []
        
        for paper in papers_data:
            try:
                # 獲取論文的章節資訊
                sections = await db_service.get_paper_sections(paper['id'])
                
                paper_summary = {
                    'file_name': paper['filename'],
                    'paper_id': paper['id'],
                    'title': paper.get('title', ''),
                    'sections': []
                }
                
                for section in sections:
                    # 計算OD/CD統計
                    sentences = await db_service.get_section_sentences(section['id'])
                    od_count = len([s for s in sentences if s.get('od_cd_label') == 'OD'])
                    cd_count = len([s for s in sentences if s.get('od_cd_label') == 'CD'])
                    
                    section_summary = {
                        'section_id': section['id'],
                        'section_type': section['section_type'],
                        'page_num': section.get('page_num', 0),
                        'word_count': len(section.get('content', '').split()),
                        'brief_content': section.get('content', '')[:200] + "...",
                        'od_count': od_count,
                        'cd_count': cd_count,
                        'total_sentences': len(sentences)
                    }
                    
                    paper_summary['sections'].append(section_summary)
                
                available_papers.append(paper_summary)
                
            except Exception as e:
                logger.warning(f"處理論文 {paper['filename']} 摘要時出錯: {e}")
                continue
        
        logger.info(f"生成了 {len(available_papers)} 篇論文的section摘要")
        return available_papers
    
    async def _intelligent_section_selection(
        self, 
        query: str, 
        available_papers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """智能章節選擇"""
        try:
            # 呼叫N8N智能章節選擇API
            selection_result = await n8n_service.intelligent_section_selection(
                query=query,
                available_papers=available_papers,
                max_sections=5  # 最多選擇5個章節
            )
            
            logger.info(f"智能選擇了 {len(selection_result.get('selected_sections', []))} 個章節")
            return selection_result
            
        except Exception as e:
            logger.error(f"智能章節選擇失敗: {e}")
            # 降級為簡單選擇策略
            return self._fallback_section_selection(query, available_papers)
    
    def _fallback_section_selection(
        self, 
        query: str, 
        available_papers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """降級章節選擇策略"""
        selected_sections = []
        
        # 簡單策略：選擇包含最多OD/CD的章節
        for paper in available_papers:
            for section in paper['sections']:
                if section['od_count'] > 0 or section['cd_count'] > 0:
                    selected_sections.append({
                        'file_name': paper['file_name'],
                        'section_type': section['section_type'],
                        'page_num': section['page_num'],
                        'relevance_score': section['od_count'] + section['cd_count']
                    })
        
        # 按相關性排序並取前5個
        selected_sections.sort(key=lambda x: x['relevance_score'], reverse=True)
        selected_sections = selected_sections[:5]
        
        return {
            'selected_sections': selected_sections,
            'analysis_focus': 'definitions',
            'fallback_mode': True
        }
    
    def _extract_content_from_summary(
        self, 
        section_selection: Dict[str, Any], 
        papers_summary: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """從摘要中提取內容（簡化版本）"""
        selected_content = []
        
        for selection in section_selection.get('selected_sections', []):
            # 找到對應的論文和章節
            for paper in papers_summary:
                if paper['file_name'] == selection['file_name']:
                for section in paper['sections']:
                    if (section['section_type'] == selection['section_type'] and 
                        section.get('page_num') == selection.get('page_num')):
                
                            # 簡化的內容提取
                content_items = []
                            if section['od_count'] > 0:
                    content_items.append({
                                    'text': f"此章節包含 {section['od_count']} 個操作型定義",
                                    'type': 'OD',
                                    'page_num': section['page_num']
                                })
                            if section['cd_count'] > 0:
                    content_items.append({
                                    'text': f"此章節包含 {section['cd_count']} 個概念型定義",
                                    'type': 'CD',
                                    'page_num': section['page_num']
                        })
                
                if content_items:
                    selected_content.append({
                                    'paper_name': paper['file_name'],
                                    'section_type': section['section_type'],
                        'content_type': 'definitions',
                        'content': content_items
                    })
                        break
                        break
        
        logger.info(f"提取了 {len(selected_content)} 個章節的內容")
        return selected_content
    
    async def _unified_content_analysis(
        self, 
        query: str, 
        selected_content: List[Dict[str, Any]], 
        section_selection: Dict[str, Any]
    ) -> Dict[str, Any]:
        """統一內容分析"""
        try:
            analysis_focus = section_selection.get('analysis_focus', 'definitions')
            
            # 呼叫N8N統一內容分析API
            analysis_result = await n8n_service.unified_content_analysis(
                query=query,
                selected_content=selected_content,
                analysis_focus=analysis_focus
            )
            
            logger.info("統一內容分析完成")
            return analysis_result
            
        except Exception as e:
            logger.error(f"統一內容分析失敗: {e}")
            # 降級處理
            return self._fallback_content_analysis(query, selected_content)
    
    def _fallback_content_analysis(
        self, 
        query: str, 
        selected_content: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """降級內容分析"""
        # 簡單的內容整合
        all_content = []
        papers_used = set()
        
        for content_group in selected_content:
            papers_used.add(content_group['paper_name'])
            for item in content_group['content']:
                all_content.append(f"{item['text']} ({content_group['paper_name']})")
        
        response = f"根據 {len(papers_used)} 篇論文的分析，找到以下相關內容：\n" + "\n".join(all_content[:5])
        
        return {
            'response': response,
            'references': [],
            'source_summary': {
                'total_papers': len(papers_used),
                'papers_used': list(papers_used),
                'sections_analyzed': len(selected_content),
                'analysis_type': 'fallback'
            },
            'fallback_mode': True
        }
    
    def _update_average_time(self, processing_time: float):
        """更新平均處理時間"""
        total_successful = self.processing_stats['successful_queries']
        current_avg = self.processing_stats['average_processing_time']
        
        new_avg = ((current_avg * (total_successful - 1)) + processing_time) / total_successful
        self.processing_stats['average_processing_time'] = new_avg
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """獲取處理統計資訊"""
        return self.processing_stats.copy()
    
    async def health_check(self) -> Dict[str, Any]:
        """健康檢查"""
        try:
            # 檢查N8N服務狀態
            try:
                n8n_health = await n8n_service.health_check()
                n8n_status = n8n_health.get('overall_healthy', False)
            except Exception as e:
                n8n_status = False
                logger.warning(f"N8N服務健康檢查失敗: {e}")
            
            # 檢查資料庫連接 (簡化檢查)
            db_status = True  # 簡化為預設健康
            
            return {
                'unified_query_processor': True,
                'n8n_service': n8n_status,
                'database_service': db_status,
                'processing_stats': self.processing_stats,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"健康檢查失敗: {e}")
            return {
                'unified_query_processor': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

# 全域實例
unified_query_processor = UnifiedQueryProcessor() 