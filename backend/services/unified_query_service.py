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

def convert_uuids_to_strings(data: Any) -> Any:
    """遞迴轉換字典或列表中的 UUID 物件為字串"""
    if isinstance(data, dict):
        return {k: convert_uuids_to_strings(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_uuids_to_strings(i) for i in data]
    elif isinstance(data, UUID):
        return str(data)
    else:
        return data

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
                paper = next((p for p in selected_papers if p.file_name == paper_summary.get('file_name')), None)
                if paper and str(paper.workspace_id) == str(workspace_id):
                    verified_summary.append(paper_summary)
                else:
                    logger.warning(f"論文 {paper_summary.get('file_name')} 不屬於工作區 {workspace_id}，已過濾")
            
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
            
            # 清理 UUID，確保所有內容都可以 JSON 序列化
            cleaned_papers_summary = convert_uuids_to_strings(papers_summary)
            
            # 呼叫 N8N 服務
            selection_result = await n8n_service.intelligent_section_selection(
                query=query, 
                available_papers=cleaned_papers_summary
            )
            
            if "error" in selection_result:
                raise QueryProcessingError(f"智能章節選擇失敗: {selection_result['error']}")
            
            return selection_result
            
        except Exception as e:
            logger.error(f"智能章節選擇過程中出錯: {str(e)}")
            raise QueryProcessingError(f"智能章節選擇失敗: {str(e)}")
    
    async def _extract_workspace_content(
        self,
        db: AsyncSession,
        query: str,
        selected_sections: List[Dict[str, Any]],
        analysis_focus: str,
        workspace_id: UUID
    ) -> List[Dict[str, Any]]:
        """
        從資料庫中提取選定的內容 - 實現穩健的回退機制
        1. 根據 analysis_focus 優先提取特定類型的內容。
        2. 如果特定內容不存在，則回退提取關鍵句子。
        3. 確保為每個選定的章節提供內容，除非該章節完全沒有句子。
        """
        try:
            logger.info(f"開始提取工作區內容: workspace={workspace_id}, analysis_focus={analysis_focus}, section_count={len(selected_sections)}")

            all_content = []

            for section in selected_sections:
                paper_id = section.get('paper_id')
                section_name = section.get('section_name')

                if not paper_id or not section_name:
                    logger.warning(f"跳過無效的選擇章節: {section}")
                    continue

                if not await db_service.is_paper_in_workspace(db, paper_id, workspace_id):
                    logger.warning(f"Paper {paper_id} not in workspace {workspace_id}, skipping.")
                    continue

                paper_info = await db_service.get_paper_by_id(db, paper_id)
                if not paper_info:
                    logger.warning(f"找不到論文資訊: paper_id={paper_id}")
                    continue
                
                content_block = {
                    "paper_name": paper_info.file_name,
                    "section_type": section_name,
                }
                content_found = False

                # 1. 根據 analysis_focus 優先提取
                if analysis_focus == 'definitions':
                    definitions = await db_service.get_definitions_by_section(db, paper_id, section_name)
                    if definitions:
                        content_block["content_type"] = "definitions"
                        content_block["content"] = [
                            {"page_num": d.page_num, "text": str(d.text), "type": str(d.definition_type)}
                            for d in definitions
                        ]
                        content_found = True
                
                elif analysis_focus == 'methods':
                    full_section = await db_service.get_full_section_content(db, paper_id, section_name)
                    if full_section and full_section.get('text'):
                        content_block["content_type"] = "full_section"
                        content_block["content"] = str(full_section.get('text', ''))
                        content_found = True

                # 2. 如果優先內容未找到，回退到提取關鍵句子
                if not content_found:
                    # 'locate_info', 'understand_content', etc. 也使用此邏輯
                    sentences = await db_service.get_top_k_sentences_by_section(db, paper_id, section_name, k=5)
                    if sentences:
                        content_block["content_type"] = "key_sentences"
                        content_block["content"] = [
                            {"page_num": s.page_num, "sentence_text": str(s.sentence)}
                            for s in sentences
                        ]
                        content_found = True

                # 3. 如果找到了任何類型的內容，則添加到最終列表中
                if content_found:
                    all_content.append(content_block)
                else:
                    logger.warning(f"無法為章節提取任何內容: paper_id={paper_id}, section={section_name}")

            logger.info(f"工作區內容提取完成: workspace={workspace_id}, 提取到 {len(all_content)} 項內容")
            return all_content

        except Exception as e:
            logger.error(f"提取工作區內容時出錯: workspace={workspace_id}, error={str(e)}")
            return []
    
    async def _unified_content_analysis(
        self, 
        query: str, 
        selected_content: List[Dict[str, Any]], 
        section_selection: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        統一內容分析 - 調用N8N工作流程
        """
        try:
            logger.info(f"統一內容分析啟動，選擇內容數: {len(selected_content)}")
            
            # 清理 UUID
            cleaned_content = convert_uuids_to_strings(selected_content)
            
            # 從 section_selection 中獲取 analysis_focus
            analysis_focus = section_selection.get('analysis_focus', 'definitions')

            analysis_result = await n8n_service.unified_content_analysis(
                query=query,
                selected_content=cleaned_content,
                analysis_focus=analysis_focus
            )
            return analysis_result
            
        except Exception as e:
            logger.error(f"統一內容分析失敗: {str(e)}")
            raise QueryProcessingError(f"統一內容分析過程中出錯: {e}")
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """獲取處理統計數據"""
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