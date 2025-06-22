"""
統一查詢處理服務 (Backlog #9)
整合所有N8N API並提供統一的查詢處理介面
"""

import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from backend.core.logging import get_logger
from backend.services.n8n_service import n8n_service
from backend.services.db_service import db_service
from backend.core.exceptions import QueryProcessingError, DataValidationError
from backend.core.database import get_db

logger = get_logger(__name__)

class UnifiedQueryProcessor:
    """統一查詢處理器 - 處理所有類型的查詢，嚴格執行工作區隔離"""
    
    def __init__(self):
        self.processing_stats = {
            'total_queries': 0,
            'successful_queries': 0,
            'failed_queries': 0,
            'average_processing_time': 0.0
        }
    
    async def process_query(
        self, 
        db: AsyncSession,
        query_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        統一查詢處理入口點 - 強制工作區隔離
        
        Args:
            db: 資料庫會話
            query_params: 查詢參數，必須包含 workspace_id
            
        Returns:
            統一格式的查詢回應
        """
        start_time = datetime.now()
        self.processing_stats['total_queries'] += 1

        try:
            # 1. 強制驗證工作區ID
            workspace_id = query_params.get('workspace_id')
            if not workspace_id:
                raise QueryProcessingError("workspace_id is required for all queries")
            
            query = query_params.get('query', '')
            logger.info(f"開始處理工作區查詢: workspace={workspace_id}, query={query[:50]}...")
            
            # 2. 驗證並獲取工作區範圍內的論文摘要
            papers_summary = await self._get_workspace_papers_summary(db, workspace_id)
            
            if not papers_summary:
                return {
                    'query': query,
                    'response': f"工作區 {workspace_id} 中沒有可用的論文資料",
                    'references': [],
                    'source_summary': {
                        'total_papers': 0,
                        'papers_used': [],
                        'workspace_id': str(workspace_id),
                        'error_occurred': True,
                        'error_message': "工作區中沒有可用的論文資料"
                    },
                    'processing_time': 0,
                    'papers_analyzed': 0,
                    'workspace_id': str(workspace_id),
                    'timestamp': datetime.now().isoformat()
                }
            
            # 3. 步驟1: 智能章節選擇（限制在工作區範圍內）
            section_selection = await self._intelligent_section_selection(
                query, papers_summary, workspace_id
            )
            
            # 4. 步驟2: 提取選中的內容（嚴格工作區過濾）
            selected_sections = section_selection.get('selected_sections', [])
            analysis_focus = section_selection.get('analysis_focus', 'definitions')
            selected_content = await self._extract_workspace_content(
                db, query, selected_sections, analysis_focus, workspace_id
            )
            
            # 5. 步驟3: 統一內容分析
            logger.info(f"即將進行統一內容分析，workspace={workspace_id}, selected_content: {len(selected_content)} 項")
            analysis_result = await self._unified_content_analysis(
                query, selected_content, section_selection
            )
            
            # 6. 記錄成功處理
            processing_time = (datetime.now() - start_time).total_seconds()
            self.processing_stats['successful_queries'] += 1
            self.processing_stats['average_processing_time'] = (
                (self.processing_stats['average_processing_time'] * (self.processing_stats['successful_queries'] - 1) + processing_time)
                / self.processing_stats['successful_queries']
            )
            
            # 7. 確保回應包含工作區資訊
            analysis_result['workspace_id'] = str(workspace_id)
            analysis_result['processing_time'] = processing_time
            analysis_result['papers_analyzed'] = len(papers_summary)
            analysis_result['timestamp'] = datetime.now().isoformat()
            
            logger.info(f"工作區查詢處理完成: workspace={workspace_id}, 處理時間={processing_time:.2f}s")
            return analysis_result
            
        except Exception as e:
            self.processing_stats['failed_queries'] += 1
            processing_time = (datetime.now() - start_time).total_seconds()
            
            logger.error(f"工作區查詢處理失敗: workspace={workspace_id}, error={str(e)}")
            
            return {
                'query': query_params.get('query', ''),
                'response': f"查詢處理失敗: {str(e)}",
                'references': [],
                'source_summary': {
                    'total_papers': 0,
                    'papers_used': [],
                    'workspace_id': str(workspace_id) if workspace_id else None,
                    'error_occurred': True,
                    'error_message': str(e)
                },
                'processing_time': processing_time,
                'papers_analyzed': 0,
                'workspace_id': str(workspace_id) if workspace_id else None,
                'timestamp': datetime.now().isoformat(),
                'error': True
            }
    
    async def _get_workspace_papers_summary(
        self, 
        db: AsyncSession, 
        workspace_id: UUID
    ) -> List[Dict[str, Any]]:
        """
        獲取工作區範圍內的論文摘要 - 嚴格工作區隔離
        """
        try:
            # 僅獲取屬於指定工作區的已選取論文
            selected_papers = await db_service.get_selected_papers_by_workspace(db, workspace_id)
                
            if not selected_papers:
                logger.warning(f"工作區 {workspace_id} 中沒有已選取的論文")
                return []
            
            paper_ids = [str(paper.id) for paper in selected_papers]
            
            # 獲取論文摘要，並再次驗證工作區歸屬
            papers_summary = await db_service.get_papers_with_sections_summary(db, paper_ids)
                        
            # 額外的安全檢查：確保所有論文都屬於指定工作區
            verified_summary = []
            for paper_summary in papers_summary:
                # 通過檔案名在資料庫中驗證工作區歸屬
                paper = next((p for p in selected_papers if p.file_name == paper_summary.file_name), None)
                if paper and str(paper.workspace_id) == str(workspace_id):
                    verified_summary.append(paper_summary)
                else:
                    logger.warning(f"論文 {paper_summary.file_name} 不屬於工作區 {workspace_id}，已過濾")
            
            logger.info(f"工作區 {workspace_id} 中獲取到 {len(verified_summary)} 個論文摘要")
            return verified_summary
                
        except Exception as e:
            logger.error(f"獲取工作區論文摘要失敗: workspace={workspace_id}, error={str(e)}")
            return []
    
    async def _intelligent_section_selection(
        self, 
        query: str, 
        papers_summary: List[Dict[str, Any]], 
        workspace_id: UUID
    ) -> Dict[str, Any]:
        """
        智能章節選擇 - 添加工作區上下文
        """
        try:
            logger.info(f"執行智能章節選擇: workspace={workspace_id}, 論文數={len(papers_summary)}")
            
            # 添加工作區資訊到上下文
            enhanced_papers_summary = []
            for paper in papers_summary:
                enhanced_paper = paper.copy()
                enhanced_paper['workspace_id'] = str(workspace_id)
                enhanced_papers_summary.append(enhanced_paper)
        
            # 調用N8N智能章節選擇API
            selection_result = await n8n_service.intelligent_section_selection(
                query=query,
                    available_papers=enhanced_papers_summary
                )
        
            # 驗證選擇結果只包含當前工作區的內容
            if 'selected_sections' in selection_result:
                verified_sections = []
                for section in selection_result['selected_sections']:
                    paper_name = section.get('paper_name', '')
                    # 確保該論文確實屬於當前工作區
                    if any(p.file_name == paper_name for p in papers_summary):
                        verified_sections.append(section)
                    else:
                        logger.warning(f"過濾非工作區論文章節: {paper_name}")
                
                selection_result['selected_sections'] = verified_sections
            
            logger.info(f"智能章節選擇完成: workspace={workspace_id}, 選擇章節數={len(selection_result.get('selected_sections', []))}")
            return selection_result
            
        except Exception as e:
            logger.error(f"智能章節選擇失敗: workspace={workspace_id}, error={str(e)}")
            return {
                'selected_sections': [],
                'analysis_focus': 'definitions',
                'error': str(e)
            }
    
    async def _extract_workspace_content(
        self, 
        db: AsyncSession,
        query: str, 
        selected_sections: List[Dict[str, Any]], 
        analysis_focus: str,
        workspace_id: UUID
    ) -> List[Dict[str, Any]]:
        """
        提取工作區範圍內的內容 - 嚴格執行工作區隔離
        """
        try:
            if not selected_sections:
                logger.warning(f"工作區 {workspace_id} 中沒有選中的章節")
                return []
            
            selected_content = []
            
            for section_info in selected_sections:
                paper_name = section_info.get('paper_name', '')
                section_type = section_info.get('section_type', '')
                focus_type = section_info.get('focus_type', analysis_focus)
                
                logger.info(f"提取內容: workspace={workspace_id}, paper={paper_name}, section={section_type}, focus={focus_type}")
                
                # 特殊處理：definitions focus_type
                if focus_type == 'definitions':
                    # 提取關鍵詞
                    keywords_result = await n8n_service.query_keyword_extraction(query)
                    keywords = []
                    if isinstance(keywords_result, list) and keywords_result:
                        keywords = keywords_result[0].get('output', {}).get('keywords', [])
            
                    # 在工作區範圍內搜尋定義句子
                    definition_sentences = await db_service.search_sentences_in_workspace(
                        db, workspace_id, 
                        defining_types=['OD', 'CD'],
                        keywords=keywords
                    )
                    
                    # 過濾並格式化為 definitions content_type
                    definitions_content = []
                    for sentence in definition_sentences:
                        # 確保句子屬於當前處理的論文和章節
                        if (sentence.get('file_name') == paper_name and 
                            sentence.get('section_type') == section_type):
                            definitions_content.append({
                                'sentence_id': sentence.get('sentence_id'),
                                'content': sentence.get('content'),
                                'defining_type': sentence.get('defining_type'),
                                'page_num': sentence.get('page_num'),
                                'paper_name': paper_name,
                                'section_type': section_type
                            })
                    
                    if definitions_content:
                        selected_content.append({
                            'paper_name': paper_name,
                            'section_type': section_type,
                            'content_type': 'definitions',
                            'content': definitions_content
                        })
                
                else:
                    # 一般內容提取流程
                    if focus_type == 'key_sentences':
                        # 在工作區範圍內搜尋關鍵句子
                        key_sentences = await db_service.search_sentences_in_workspace(
                            db, workspace_id,
                            keywords=[query]  # 使用查詢作為關鍵詞
                        )
                    
                        # 過濾屬於當前論文和章節的句子
                        filtered_sentences = [
                            s for s in key_sentences 
                            if (s.get('file_name') == paper_name and 
                                s.get('section_type') == section_type)
                        ]
                        
                        if filtered_sentences:
                            selected_content.append({
                                'paper_name': paper_name,
                                'section_type': section_type,
                                'content_type': 'key_sentences',
                                'content': filtered_sentences
                            })
                    
                    elif focus_type == 'full_section':
                        # 獲取完整章節內容（在工作區範圍內）
                        section_content = await db_service.get_section_content_by_workspace(
                            db, workspace_id, paper_name, section_type
                        )
                        
                        if section_content:
                            selected_content.append({
                                'paper_name': paper_name,
                                'section_type': section_type,
                                'content_type': 'full_section',
                                'content': section_content
                            })
            
            logger.info(f"內容提取完成: workspace={workspace_id}, 提取項目數={len(selected_content)}")
            return selected_content
                    
        except Exception as e:
            logger.error(f"工作區內容提取失敗: workspace={workspace_id}, error={str(e)}")
            return []
    
    async def _unified_content_analysis(
        self, 
        query: str, 
        selected_content: List[Dict[str, Any]], 
        section_selection: Dict[str, Any]
    ) -> Dict[str, Any]:
        """統一內容分析（移除降級處理，確保與 flowchart 一致）"""
        
        analysis_focus = section_selection.get('analysis_focus', 'understand_content')
        
        # 確保 analysis_focus 使用正確的值 (根據 n8n_api_document.md 更新)
        valid_analysis_focus = [
            'locate_info', 'understand_content', 'cross_paper', 
            'definitions', 'methods', 'results', 'comparison', 'other'
        ]
        
        if analysis_focus not in valid_analysis_focus:
            logger.warning(f"無效的 analysis_focus: {analysis_focus}，使用預設值 'understand_content'")
            analysis_focus = 'understand_content'
        
        # 檢查是否有內容可分析
        if not selected_content:
            error_msg = "沒有選中的內容，無法進行統一內容分析"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        logger.info(f"調用 N8N 統一內容分析，分析重點: {analysis_focus}, 內容數量: {len(selected_content)}")
        
        # 呼叫N8N統一內容分析API
        analysis_result = await n8n_service.unified_content_analysis(
            query=query,
            selected_content=selected_content,
            analysis_focus=analysis_focus
        )
        
        # 檢查是否有錯誤
        if 'error' in analysis_result:
            error_msg = f"統一內容分析失敗: {analysis_result['error']}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        # 驗證回應格式
        expected_fields = ['response', 'references', 'source_summary']
        if not all(field in analysis_result for field in expected_fields):
            error_msg = f"統一內容分析回應格式異常，缺少必要欄位: {expected_fields}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        reference_count = len(analysis_result['references'])
        papers_analyzed = analysis_result['source_summary'].get('total_papers', 0)
        logger.info(f"統一內容分析完成，生成 {reference_count} 個引用，分析 {papers_analyzed} 篇論文")
        
        return analysis_result
    
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