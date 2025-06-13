"""
統一查詢處理服務 (Backlog #9)
整合所有N8N API並提供統一的查詢處理介面
"""

import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

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
            
            # 步驟2: 提取選中的內容
            selected_sections = section_selection.get('selected_sections', [])
            selected_content = await self._extract_content(
                query, selected_sections
            )
            
            # 步驟3: 統一內容分析
            logger.info(f"即將進行統一內容分析，selected_content: {len(selected_content)} 項")
            analysis_result = await self._unified_content_analysis(
                query, selected_content, section_selection
            )
            logger.info(f"統一內容分析返回結果: {analysis_result}")
            
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
        papers_data: List[Dict[str, Any]],
        session: AsyncSession
    ) -> List[Dict[str, Any]]:
        """生成論文section摘要"""
        available_papers = []
        
        for paper in papers_data:
            try:
                logger.info(f"處理論文摘要: {paper['filename']}")
                
                # 獲取論文的章節資訊 - 使用正確的方法
                sections = await db_service.get_sections_for_paper(session, paper['id'])
                
                if not sections:
                    logger.warning(f"論文 {paper['filename']} 沒有章節資料")
                    continue
                
                paper_summary = {
                    'file_name': paper['filename'],
                    'paper_id': paper['id'],
                    'title': paper.get('title', ''),
                    'sections': []
                }
                
                for section in sections:
                    try:
                        # 獲取章節句子 - 使用正確的方法
                        sentences = await db_service.get_sentences_by_section_id(session, str(section.id))
                        
                        # 計算OD/CD統計
                        od_count = len([s for s in sentences if s.get('defining_type') == 'OD'])
                        cd_count = len([s for s in sentences if s.get('defining_type') == 'CD'])
                        
                        section_summary = {
                            'section_id': str(section.id),
                            'section_type': section.section_type,
                            'page_num': section.page_num or 0,
                            'word_count': len(section.content.split()) if section.content else 0,
                            'brief_content': (section.content or '')[:200] + "...",
                            'od_count': od_count,
                            'cd_count': cd_count,
                            'total_sentences': len(sentences)
                        }
                        
                        paper_summary['sections'].append(section_summary)
                        
                    except Exception as e:
                        logger.warning(f"處理章節 {section.section_type} 時出錯: {e}")
                        continue
                
                if paper_summary['sections']:  # 只有當有章節資料時才加入
                    available_papers.append(paper_summary)
                    logger.info(f"論文 {paper['filename']} 摘要生成成功，包含 {len(paper_summary['sections'])} 個章節")
                else:
                    logger.warning(f"論文 {paper['filename']} 沒有有效的章節資料")
                
            except Exception as e:
                logger.error(f"處理論文 {paper['filename']} 摘要時出錯: {e}", exc_info=True)
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
                        'paper_name': paper['file_name'],
                        'section_id': section['section_id'],
                        'section_type': section['section_type'],
                        'page_num': section['page_num'],
                        'relevance_score': section['od_count'] + section['cd_count'],
                        'focus_type': 'definitions'
                    })
        
        # 按相關性排序並取前5個
        selected_sections.sort(key=lambda x: x['relevance_score'], reverse=True)
        selected_sections = selected_sections[:5]
        
        return {
            'selected_sections': selected_sections,
            'analysis_focus': 'definitions',
            'fallback_mode': True
        }
    
    async def _extract_content(
        self, 
        query: str,
        selected_sections: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """基於 focus_type 的內容提取邏輯"""
        
        if not selected_sections:
            logger.warning("沒有選中的章節")
            return []
        
        extracted_content = []
        
        for section in selected_sections:
            section_id = section.get('section_id')
            paper_name = section.get('paper_name', section.get('file_name'))
            section_type = section.get('section_type')
            focus_type = section.get('focus_type', 'definitions')
            
            if focus_type == 'definitions':
                content = await self._process_definitions_content(query, section_id, paper_name, section_type)
                if content:
                    extracted_content.append(content)
            else:
                # 其他 focus_type 的處理框架
                logger.info(f"暫不支援 focus_type: {focus_type}，使用預設處理")
                content = await self._process_default_content(query, section_id, paper_name, section_type)
                if content:
                    extracted_content.append(content)
        
        logger.info(f"成功提取 {len(extracted_content)} 個章節的內容")
        return extracted_content
    
    async def _process_definitions_content(
        self, 
        query: str, 
        section_id: str, 
        paper_name: str, 
        section_type: str
    ) -> Optional[Dict[str, Any]]:
        """處理 definitions 類型的內容"""
        try:
            # 步驟1: 關鍵詞提取
            keywords = await n8n_service.extract_keywords(query)
            logger.info(f"提取到關鍵詞: {keywords}")
            
            # 步驟2: 從資料庫取得該章節的所有句子
            async for db in get_db():
                try:
                    all_sentences = await db_service.get_sentences_by_section_id(db, section_id)
                    
                    if not all_sentences:
                        logger.warning(f"章節 {section_id} 沒有找到句子")
                        return None
                    
                    logger.info(f"章節 {section_id} 取得 {len(all_sentences)} 個句子")
                    
                    # 步驟3: 全比對搜尋邏輯
                    matched_sentences = self._find_matching_sentences(all_sentences, keywords)
                    logger.info(f"關鍵詞匹配找到 {len(matched_sentences)} 個句子")
                    
                    # 步驟4: 篩選定義句子 (OD/CD)
                    definition_sentences = self._filter_definition_sentences(matched_sentences)
                    logger.info(f"篩選出 {len(definition_sentences)} 個定義句子")
                    
                    if not definition_sentences:
                        logger.warning(f"章節 {section_id} 沒有找到符合的定義句子")
                        return None
                    
                    # 步驟5: 構建 selected_content 格式
                    content_items = []
                    for sentence in definition_sentences:
                        content_items.append({
                            "text": sentence["text"],
                            "type": sentence["defining_type"],
                            "page_num": sentence["page_num"],
                            "id": f"{paper_name.replace('.pdf', '')}_{section_type}_{sentence['page_num']}_{sentence.get('sentence_order', 0)}",
                            "reason": f"This sentence contains a {sentence['defining_type']} definition related to the query."
                        })
                    
                    return {
                        "paper_name": paper_name,
                        "section_type": section_type,
                        "content_type": "definitions",
                        "content": content_items
                    }
                    
                except Exception as e:
                    logger.error(f"資料庫操作失敗: {e}")
                    return None
                finally:
                    break  # 退出 async generator
                    
        except Exception as e:
            logger.error(f"處理 definitions 內容失敗: {e}")
            return None
    
    async def _process_default_content(
        self, 
        query: str, 
        section_id: str, 
        paper_name: str, 
        section_type: str
    ) -> Optional[Dict[str, Any]]:
        """預設內容處理（框架）"""
        logger.info(f"使用預設處理邏輯處理章節 {section_id}")
        
        # 這裡是其他 focus_type 的處理邏輯框架
        # 目前返回簡化的內容
        return {
            "paper_name": paper_name,
            "section_type": section_type,
            "content_type": "general",
            "content": [
                {
                    "text": f"章節 {section_type} 的相關內容",
                    "type": "GENERAL",
                    "page_num": 1,
                    "id": f"{paper_name.replace('.pdf', '')}_{section_type}_general"
                }
            ]
        }
    
    def _find_matching_sentences(
        self, 
        sentences: List[Dict[str, Any]], 
        keywords: List[str]
    ) -> List[Dict[str, Any]]:
        """全比對搜尋邏輯"""
        matched_sentences = []
        
        for sentence in sentences:
            sentence_text = sentence.get("text", "").lower()
            
            # 檢查是否包含任何關鍵詞
            for keyword in keywords:
                if keyword.lower() in sentence_text:
                    matched_sentences.append(sentence)
                    break  # 找到一個匹配即可
        
        return matched_sentences
    
    def _filter_definition_sentences(
        self, 
        sentences: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """篩選定義句子 (OD/CD)"""
        definition_sentences = []
        
        for sentence in sentences:
            defining_type = sentence.get("defining_type")
            if defining_type in ["OD", "CD"]:
                definition_sentences.append(sentence)
        
        return definition_sentences
    
    async def _unified_content_analysis(
        self, 
        query: str, 
        selected_content: List[Dict[str, Any]], 
        section_selection: Dict[str, Any]
    ) -> Dict[str, Any]:
        """統一內容分析"""
        try:
            analysis_focus = section_selection.get('analysis_focus', 'definitions')
            logger.info(f"調用 N8N 統一內容分析，分析重點: {analysis_focus}")
            
            # 呼叫N8N統一內容分析API
            analysis_result = await n8n_service.unified_content_analysis(
                query=query,
                selected_content=selected_content,
                analysis_focus=analysis_focus
            )
            
            logger.info(f"N8N統一內容分析完成，結果: {analysis_result}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"統一內容分析失敗: {e}")
            logger.info("使用降級處理...")
            # 降級處理
            fallback_result = self._fallback_content_analysis(query, selected_content)
            logger.info(f"降級處理結果: {fallback_result}")
            return fallback_result
    
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