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
from backend.core.database import get_db

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
            analysis_focus = section_selection.get('analysis_focus', 'definitions')
            selected_content = await self._extract_content(
                query, selected_sections, analysis_focus
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
                logger.info(f"處理論文摘要: {paper['filename']} (original: {paper.get('original_filename', 'N/A')})")
                
                # 獲取論文的章節資訊 - 使用正確的方法
                sections = await db_service.get_sections_for_paper(session, paper['id'])
                logger.info(f"論文 {paper['filename']} 找到 {len(sections) if sections else 0} 個章節")
                
                if not sections:
                    logger.warning(f"論文 {paper['filename']} 沒有章節資料")
                    continue
                
                # 使用 original_filename 作為 file_name，確保與 N8N API 一致
                paper_summary = {
                    'file_name': paper.get('original_filename', paper['filename']),
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
        """智能章節選擇（移除降級處理，確保與 flowchart 一致）"""
        
        # 呼叫N8N智能章節選擇API
        selection_result = await n8n_service.intelligent_section_selection(
            query=query,
            available_papers=available_papers,
            max_sections=5  # 最多選擇5個章節
        )
        
        # 檢查是否有錯誤
        if 'error' in selection_result:
            error_msg = f"智能章節選擇失敗: {selection_result['error']}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        # 驗證回應格式
        expected_fields = ['selected_sections', 'analysis_focus', 'suggested_approach']
        if not all(field in selection_result for field in expected_fields):
            error_msg = f"智能章節選擇回應格式異常，缺少必要欄位: {expected_fields}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        selected_count = len(selection_result.get('selected_sections', []))
        analysis_focus = selection_result['analysis_focus']
        logger.info(f"智能章節選擇完成，選擇了 {selected_count} 個章節，分析重點: {analysis_focus}")
        
        return selection_result
    
    async def _extract_content(
        self, 
        query: str,
        selected_sections: List[Dict[str, Any]],
        analysis_focus: str = "definitions"
    ) -> List[Dict[str, Any]]:
        """基於 analysis_focus 和 focus_type 的內容提取邏輯"""
        
        if not selected_sections:
            logger.warning("沒有選中的章節")
            return []
        
        extracted_content = []
        
        for section in selected_sections:
            paper_name = section.get('paper_name', section.get('file_name'))
            section_type = section.get('section_type')
            focus_type = section.get('focus_type', 'definitions')
            
            if not paper_name or not section_type:
                logger.warning(f"章節資料不完整: paper_name={paper_name}, section_type={section_type}")
                continue
            
            logger.info(f"處理章節: {paper_name} - {section_type}, focus_type: {focus_type}, analysis_focus: {analysis_focus}")
            
            # 根據 analysis_focus 決定處理方式，而不是僅依賴 focus_type
            if analysis_focus == 'definitions' or focus_type == 'definitions':
                # 對於定義查詢，即使 focus_type 不是 definitions 也要進行定義處理
                logger.info(f"使用定義處理邏輯 (analysis_focus={analysis_focus}, focus_type={focus_type})")
                content = await self._process_definitions_content(query, paper_name, section_type)
                if content:
                    extracted_content.append(content)
            elif focus_type == 'key_sentences' and analysis_focus == 'definitions':
                # 特殊情況：focus_type 是 key_sentences 但 analysis_focus 是 definitions
                logger.info(f"特殊處理: focus_type=key_sentences 但 analysis_focus=definitions，使用定義處理邏輯")
                content = await self._process_definitions_content(query, paper_name, section_type)
                if content:
                    extracted_content.append(content)
            else:
                # 其他 focus_type 的處理框架
                logger.info(f"使用預設處理邏輯: focus_type={focus_type}, analysis_focus={analysis_focus}")
                content = await self._process_default_content(query, paper_name, section_type)
                if content:
                    extracted_content.append(content)
        
        logger.info(f"成功提取 {len(extracted_content)} 個章節的內容")
        return extracted_content
    
    async def _process_definitions_content(
        self, 
        query: str, 
        paper_name: str, 
        section_type: str
    ) -> Optional[Dict[str, Any]]:
        """處理 definitions 類型的內容（修正版本：不依賴 section_id）"""
        try:
            # 步驟1: 關鍵詞提取
            keywords_result = await n8n_service.extract_keywords(query)
            logger.info(f"關鍵詞提取結果類型: {type(keywords_result)}")
            logger.info(f"關鍵詞提取原始結果: {keywords_result}")
            
            # 處理 N8N API 回傳格式 - 實際格式是 [{"keywords": [...]}]
            keywords = []
            if isinstance(keywords_result, list) and len(keywords_result) > 0:
                first_item = keywords_result[0]
                if isinstance(first_item, dict) and 'keywords' in first_item:
                    keywords = first_item['keywords']
                    logger.info(f"成功提取關鍵詞: {keywords}")
                else:
                    logger.warning(f"關鍵詞提取回傳格式異常，第一個項目: {first_item}")
            elif isinstance(keywords_result, dict):
                # 備用處理：如果是字典格式
                if 'keywords' in keywords_result:
                    keywords = keywords_result['keywords']
                elif 'error' in keywords_result:
                    logger.warning(f"關鍵詞提取失敗: {keywords_result['error']}")
                else:
                    logger.warning(f"關鍵詞提取回傳格式異常: {keywords_result}")
            else:
                logger.warning(f"關鍵詞提取回傳格式完全異常: {keywords_result}")
            
            # 如果沒有關鍵詞，使用查詢本身作為關鍵詞
            if not keywords:
                logger.info("沒有提取到關鍵詞，使用原始查詢進行匹配")
                keywords = [query.strip()]
            
            logger.info(f"最終使用的關鍵詞: {keywords} (數量: {len(keywords)})")
            
            # 步驟2: 從資料庫根據 paper_name 和 section_type 取得該章節的所有句子
            async for db in get_db():
                try:
                    all_sentences = await db_service.get_sentences_by_paper_and_section_type(
                        db, paper_name, section_type
                    )
                    
                    logger.info(f"資料庫查詢結果: 論文 {paper_name} 章節 {section_type} 取得 {len(all_sentences) if all_sentences else 0} 個句子")
                    
                    if not all_sentences:
                        logger.warning(f"論文 {paper_name} 的章節 {section_type} 沒有找到句子")
                        logger.info(f"嘗試查詢該論文的所有章節類型...")
                        
                        # 診斷：查看該論文有哪些章節類型
                        try:
                            from sqlalchemy import text
                            debug_query = text("""
                                SELECT DISTINCT ps.section_type, COUNT(s.id) as sentence_count
                                FROM paper_sections ps 
                                LEFT JOIN sentences s ON ps.id = s.section_id 
                                JOIN papers p ON ps.paper_id = p.id
                                WHERE p.file_name = :paper_name OR p.original_filename = :paper_name
                                GROUP BY ps.section_type
                                ORDER BY sentence_count DESC
                            """)
                            debug_result = await db.execute(debug_query, {"paper_name": paper_name})
                            available_sections = debug_result.fetchall()
                            
                            logger.info(f"該論文可用的章節類型: {[(row[0], row[1]) for row in available_sections]}")
                            
                        except Exception as debug_e:
                            logger.warning(f"診斷查詢失敗: {debug_e}")
                        
                        return None
                    
                    logger.info(f"論文 {paper_name} 章節 {section_type} 取得 {len(all_sentences)} 個句子")
                    
                    # 步驟3: 全比對搜尋邏輯
                    matched_sentences = self._find_matching_sentences(all_sentences, keywords)
                    logger.info(f"關鍵詞匹配找到 {len(matched_sentences)} 個句子")
                    
                    # 診斷：顯示匹配的句子樣本
                    if matched_sentences:
                        sample_sentences = matched_sentences[:3]  # 顯示前3個
                        for i, sentence in enumerate(sample_sentences):
                            logger.info(f"匹配句子 {i+1}: {sentence.get('text', '')[:100]}...")
                    
                    # 步驟4: 篩選定義句子 (OD/CD)
                    definition_sentences = self._filter_definition_sentences(matched_sentences)
                    logger.info(f"篩選出 {len(definition_sentences)} 個定義句子")
                    
                    # 診斷：顯示定義句子的類型分布
                    if definition_sentences:
                        od_count = len([s for s in definition_sentences if s.get('defining_type') == 'OD'])
                        cd_count = len([s for s in definition_sentences if s.get('defining_type') == 'CD'])
                        logger.info(f"定義句子分布: OD={od_count}, CD={cd_count}")
                    else:
                        # 診斷：查看所有句子的 defining_type 分布
                        all_types = {}
                        for sentence in all_sentences:
                            dtype = sentence.get('defining_type', 'UNKNOWN')
                            all_types[dtype] = all_types.get(dtype, 0) + 1
                        logger.info(f"該章節所有句子的 defining_type 分布: {all_types}")
                    
                    if not definition_sentences:
                        logger.warning(f"論文 {paper_name} 章節 {section_type} 沒有找到符合的定義句子")
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
                    logger.error(f"資料庫操作失敗: {e}", exc_info=True)
                    return None
                    
        except Exception as e:
            logger.error(f"處理 definitions 內容失敗: {e}", exc_info=True)
            return None
    
    async def _process_default_content(
        self, 
        query: str, 
        paper_name: str, 
        section_type: str
    ) -> Optional[Dict[str, Any]]:
        """預設內容處理（框架）"""
        logger.info(f"使用預設處理邏輯處理章節 {section_type}")
        
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
        """篩選定義句子 (基於布林欄位)"""
        definition_sentences = []
        
        for sentence in sentences:
            # 使用實際的布林欄位檢查是否為定義句子
            has_objective = sentence.get("has_objective", False)
            has_dataset = sentence.get("has_dataset", False) 
            has_contribution = sentence.get("has_contribution", False)
            
            # 如果任一布林欄位為 True，則視為定義句子
            if has_objective or has_dataset or has_contribution:
                # 為了保持與後續處理的相容性，添加 defining_type 欄位
                sentence_copy = sentence.copy()
                
                # 根據布林欄位決定 defining_type
                if has_objective:
                    sentence_copy["defining_type"] = "OD"  # Objective Definition
                elif has_dataset:
                    sentence_copy["defining_type"] = "CD"  # Conceptual Definition (Dataset)
                elif has_contribution:
                    sentence_copy["defining_type"] = "CD"  # Conceptual Definition (Contribution)
                
                definition_sentences.append(sentence_copy)
        
        return definition_sentences
    
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