"""
N8N API整合服務
支援OD/CD檢測、關鍵詞提取、批次呼叫和智能快取
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from datetime import datetime
import json

from ..core.config import settings
from ..core.logging import get_logger
from ..core.http_client import create_client, HTTPClient

logger = get_logger("n8n_service")

@dataclass
class BatchRequest:
    """批次請求項目"""
    id: str
    endpoint: str
    data: Dict[str, Any]
    priority: int = 1  # 1=高優先序, 2=中, 3=低
    retry_count: int = 0
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class BatchResponse:
    """批次回應項目"""
    request_id: str
    success: bool
    data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    processing_time: float = 0.0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class N8NService:
    """N8N API整合服務"""
    
    def __init__(self):
        self.base_url = settings.n8n_base_url
        self.client = create_client(
            base_url=self.base_url,
            timeout=60,  # N8N工作流程可能需要較長時間
            max_retries=3
        )
        
        # API端點配置 (根據 n8n_api_document.md)
        self.endpoints = {
            'od_cd_detection': '/webhook/check-od-cd',
            'keyword_extraction': '/webhook/421337df-0d97-47b4-a96b-a70a6c35d416',
            'intelligent_section_selection': '/webhook/intelligent-section-selection',
            'unified_content_analysis': '/webhook/unified-content-analysis',
            'enhanced_organization': '/webhook/enhanced-organize-response'
        }
        
        # 批次處理配置
        self.batch_queue: List[BatchRequest] = []
        self.max_batch_size = 10
        self.batch_timeout = 30  # 秒
        self.max_concurrent_requests = 5
        
        # 快取配置
        self.client.enable_cache(ttl_seconds=600)  # 10分鐘快取
        
        # 統計追蹤
        self.request_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'cached_requests': 0,
            'batch_requests': 0
        }
        
        logger.info(f"N8N服務初始化完成，基礎URL: {self.base_url}")
    
    # ===== 基礎API呼叫方法 =====
    
    async def _call_n8n_webhook(
        self,
        endpoint_key: str,
        data: Dict[str, Any],
        timeout: int = None,
        disable_cache: bool = False
    ) -> Dict[str, Any]:
        """呼叫N8N webhook"""
        if endpoint_key not in self.endpoints:
            raise ValueError(f"未知的端點: {endpoint_key}")
        
        endpoint = self.endpoints[endpoint_key]
        self.request_stats['total_requests'] += 1
        
        try:
            start_time = time.time()
            
            response = await self.client.post(
                endpoint=endpoint,
                json_data=data,
                timeout=timeout,
                disable_cache=disable_cache
            )
            
            processing_time = time.time() - start_time
            
            if response:
                self.request_stats['successful_requests'] += 1
                logger.debug(f"N8N API成功: {endpoint_key} ({processing_time:.2f}秒)")
                return response
            else:
                self.request_stats['failed_requests'] += 1
                logger.warning(f"N8N API返回空回應: {endpoint_key}")
                return {"error": "空回應"}
                
        except Exception as e:
            self.request_stats['failed_requests'] += 1
            logger.error(f"N8N API呼叫失敗: {endpoint_key}, 錯誤: {e}")
            raise
    
    # ===== 現有API方法 =====
    
    async def detect_od_cd(
        self,
        sentence: str,
        cache_key: str = None
    ) -> Dict[str, Any]:
        """
        OD/CD檢測API (根據 n8n_api_document.md 規格)
        
        Args:
            sentence: 單一句子
            cache_key: 自定義快取鍵
            
        Returns:
            OD/CD檢測結果
        """
        # 根據API文件，使用 application/x-www-form-urlencoded 格式
        request_data = {
            "sentence": sentence
        }
        
        logger.info(f"執行OD/CD檢測: {sentence[:50]}...")
        
        try:
            result = await self.client.post(
                endpoint=self.endpoints['od_cd_detection'],
                data=request_data,  # 使用 data 而非 json_data
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=30,
                disable_cache=(cache_key is None)
            )
            
            # 驗證回應格式 {"defining_type": "string", "reason": "string"}
            if 'defining_type' in result and 'reason' in result:
                logger.info(f"OD/CD檢測完成: {result['defining_type']}")
                return result
            else:
                logger.warning(f"OD/CD檢測回應格式異常: {result}")
                return {"error": "回應格式異常", "raw_response": result}
                
        except Exception as e:
            logger.error(f"OD/CD檢測失敗: {e}")
            return {
                "error": str(e),
                "sentence": sentence,
                "failed_at": datetime.now().isoformat()
            }
    
    async def extract_keywords(
        self,
        query: str
    ) -> Dict[str, Any]:
        """
        關鍵詞提取API (根據 n8n_api_document.md 規格)
        
        Args:
            query: 需要萃取關鍵字的查詢語句
            
        Returns:
            關鍵詞提取結果
        """
        # 根據API文件，使用 application/x-www-form-urlencoded 格式
        request_data = {
            "query": query
        }
        
        logger.info(f"執行關鍵詞提取: {query[:50]}...")
        
        try:
            result = await self.client.post(
                endpoint=self.endpoints['keyword_extraction'],
                data=request_data,  # 使用 data 而非 json_data
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=30
            )
            
            # 驗證回應格式 [{"output": {"keywords": ["string", ...]}}]
            if isinstance(result, list) and len(result) > 0 and 'output' in result[0]:
                keywords = result[0]['output'].get('keywords', [])
                logger.info(f"關鍵詞提取完成，提取到 {len(keywords)} 個關鍵詞")
                return {
                    'keywords': keywords,
                    'total_keywords': len(keywords)
                }
            else:
                logger.warning(f"關鍵詞提取回應格式異常: {result}")
                return {"error": "回應格式異常", "raw_response": result}
                
        except Exception as e:
            logger.error(f"關鍵詞提取失敗: {e}")
            return {
                "error": str(e),
                "query": query,
                "failed_at": datetime.now().isoformat()
            }
    
    # ===== 新API方法 (Backlog #8功能) =====
    
    async def intelligent_section_selection(
        self,
        query: str,
        available_papers: List[Dict[str, Any]],
        max_sections: int = 3
    ) -> Dict[str, Any]:
        """
        智能章節選擇API (根據 n8n_api_document.md 規格)
        
        Args:
            query: 使用者查詢語句
            available_papers: 可用論文及其section摘要列表
            max_sections: 最大選擇章節數
            
        Returns:
            選擇的章節列表及分析策略
        """
        request_data = {
            "query": query,
            "available_papers": available_papers,
            "max_sections": max_sections,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"執行智能章節選擇，查詢: {query[:50]}..., 論文數量: {len(available_papers)}")
        
        try:
            result = await self._call_n8n_webhook(
                'intelligent_section_selection', 
                request_data,
                timeout=120  # 智能選擇可能需要更長時間
            )
            
            # 驗證回應格式符合API文檔
            expected_fields = ['selected_sections', 'analysis_focus', 'suggested_approach']
            if all(field in result for field in expected_fields):
                selected_count = len(result['selected_sections'])
                analysis_focus = result['analysis_focus']
                logger.info(f"智能章節選擇完成，選擇了 {selected_count} 個章節，分析重點: {analysis_focus}")
                return result
            else:
                logger.warning("智能章節選擇回應格式異常")
                return {"error": "回應格式異常", "raw_response": result}
                
        except Exception as e:
            logger.error(f"智能章節選擇失敗: {e}")
            return {
                "error": str(e),
                "query": query,
                "available_papers_count": len(available_papers),
                "failed_at": datetime.now().isoformat()
            }
    
    async def unified_content_analysis(
        self,
        query: str,
        selected_content: List[Dict[str, Any]],
        analysis_focus: str = "definitions"
    ) -> Dict[str, Any]:
        """
        統一內容分析API (根據 n8n_api_document.md 規格)
        
        Args:
            query: 原始查詢語句
            selected_content: LLM選中的section內容
            analysis_focus: 分析重點類型 (definitions, methods, comparison)
            
        Returns:
            統一分析結果包含回應、引用和來源摘要
        """
        request_data = {
            "query": query,
            "selected_content": selected_content,
            "analysis_focus": analysis_focus,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"執行統一內容分析，查詢: {query[:50]}..., 分析重點: {analysis_focus}")
        
        try:
            result = await self._call_n8n_webhook(
                'unified_content_analysis', 
                request_data,
                timeout=180  # 多論文內容分析需要更長時間
            )
            
            # 驗證回應格式符合API文檔
            expected_fields = ['response', 'references', 'source_summary']
            if all(field in result for field in expected_fields):
                reference_count = len(result['references'])
                papers_analyzed = result['source_summary'].get('total_papers', 0)
                logger.info(f"統一內容分析完成，生成 {reference_count} 個引用，分析 {papers_analyzed} 篇論文")
                return result
            else:
                logger.warning("統一內容分析回應格式異常")
                return {"error": "回應格式異常", "raw_response": result}
                
        except Exception as e:
            logger.error(f"統一內容分析失敗: {e}")
            return {
                "error": str(e),
                "query": query,
                "content_count": len(selected_content),
                "analysis_focus": analysis_focus,
                "failed_at": datetime.now().isoformat()
            }
    
    async def enhanced_organization(
        self,
        query: str,
        papers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        增強型組織回應API (根據 n8n_api_document.md 規格 - 向後相容)
        
        Args:
            query: 使用者的查詢語句
            papers: 論文列表，包含操作型和概念型定義
            
        Returns:
            組織後的回應，包含引用和來源摘要
        """
        request_data = {
            "query": query,
            "papers": papers,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"執行增強型組織回應，查詢: {query[:50]}..., 論文數量: {len(papers)}")
        
        try:
            result = await self._call_n8n_webhook(
                'enhanced_organization', 
                request_data,
                timeout=240  # 多檔案處理需要更長時間
            )
            
            # 驗證回應格式符合API文檔
            expected_fields = ['response', 'references', 'source_summary']
            if all(field in result for field in expected_fields):
                reference_count = len(result['references'])
                papers_used = len(result['source_summary'].get('papers_used', []))
                logger.info(f"增強型組織回應完成，生成 {reference_count} 個引用，使用 {papers_used} 篇論文")
                return result
            else:
                logger.warning("增強型組織回應格式異常")
                return {"error": "回應格式異常", "raw_response": result}
                
        except Exception as e:
            logger.error(f"增強型組織回應失敗: {e}")
            return {
                "error": str(e),
                "query": query,
                "papers_count": len(papers),
                "failed_at": datetime.now().isoformat()
            }
    
    # ===== 批次處理功能 =====
    
    async def add_to_batch(
        self,
        request_id: str,
        endpoint_key: str,
        data: Dict[str, Any],
        priority: int = 2
    ) -> bool:
        """添加請求到批次佇列"""
        if len(self.batch_queue) >= self.max_batch_size * 2:  # 限制佇列大小
            logger.warning("批次佇列已滿，丟棄請求")
            return False
        
        batch_request = BatchRequest(
            id=request_id,
            endpoint=endpoint_key,
            data=data,
            priority=priority
        )
        
        self.batch_queue.append(batch_request)
        logger.debug(f"請求已添加到批次佇列: {request_id}")
        return True
    
    async def process_batch(self) -> List[BatchResponse]:
        """處理批次佇列中的請求"""
        if not self.batch_queue:
            return []
        
        # 按優先序排序
        self.batch_queue.sort(key=lambda x: (x.priority, x.created_at))
        
        # 取出要處理的批次
        batch_size = min(len(self.batch_queue), self.max_batch_size)
        current_batch = self.batch_queue[:batch_size]
        self.batch_queue = self.batch_queue[batch_size:]
        
        logger.info(f"開始處理批次，項目數: {batch_size}")
        
        # 創建任務列表
        tasks = []
        for request in current_batch:
            task = self._process_single_batch_request(request)
            tasks.append(task)
        
        # 並發執行，限制併發數
        semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        
        async def bounded_task(task):
            async with semaphore:
                return await task
        
        bounded_tasks = [bounded_task(task) for task in tasks]
        responses = await asyncio.gather(*bounded_tasks, return_exceptions=True)
        
        # 處理結果
        batch_responses = []
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                batch_response = BatchResponse(
                    request_id=current_batch[i].id,
                    success=False,
                    error_message=str(response)
                )
            else:
                batch_response = response
            
            batch_responses.append(batch_response)
        
        self.request_stats['batch_requests'] += len(batch_responses)
        success_count = sum(1 for r in batch_responses if r.success)
        
        logger.info(f"批次處理完成，成功: {success_count}/{len(batch_responses)}")
        return batch_responses
    
    async def _process_single_batch_request(self, request: BatchRequest) -> BatchResponse:
        """處理單個批次請求"""
        start_time = time.time()
        
        try:
            result = await self._call_n8n_webhook(
                request.endpoint,
                request.data,
                disable_cache=False  # 批次請求使用快取
            )
            
            processing_time = time.time() - start_time
            
            return BatchResponse(
                request_id=request.id,
                success=True,
                data=result,
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            
            return BatchResponse(
                request_id=request.id,
                success=False,
                error_message=str(e),
                processing_time=processing_time
            )
    
    # ===== 高級功能 =====
    
    async def batch_od_cd_detection(
        self,
        paper_sentences_list: List[Dict[str, Any]],
        progress_callback: callable = None
    ) -> List[Dict[str, Any]]:
        """
        批次OD/CD檢測
        
        Args:
            paper_sentences_list: 包含paper_id和sentences的列表
            progress_callback: 進度回調函數
            
        Returns:
            批次檢測結果
        """
        logger.info(f"開始批次OD/CD檢測，論文數量: {len(paper_sentences_list)}")
        
        results = []
        total_papers = len(paper_sentences_list)
        
        for i, paper_data in enumerate(paper_sentences_list):
            try:
                paper_id = paper_data.get('paper_id')
                sentences = paper_data.get('sentences', [])
                paper_title = paper_data.get('title', '')
                paper_authors = paper_data.get('authors', [])
                
                # 執行檢測
                detection_result = await self.detect_od_cd(
                    sentences=sentences,
                    paper_title=paper_title,
                    paper_authors=paper_authors,
                    cache_key=f"od_cd_{paper_id}"
                )
                
                results.append({
                    'paper_id': paper_id,
                    'detection_result': detection_result,
                    'success': 'error' not in detection_result
                })
                
                # 進度回調
                if progress_callback:
                    progress = (i + 1) / total_papers
                    await progress_callback(progress, paper_id)
                
                # 避免API限流
                if i < total_papers - 1:
                    await asyncio.sleep(0.5)
                    
            except Exception as e:
                logger.error(f"批次檢測失敗，論文ID: {paper_data.get('paper_id')}, 錯誤: {e}")
                results.append({
                    'paper_id': paper_data.get('paper_id'),
                    'detection_result': {"error": str(e)},
                    'success': False
                })
        
        success_count = sum(1 for r in results if r['success'])
        logger.info(f"批次OD/CD檢測完成，成功: {success_count}/{total_papers}")
        
        return results
    
    async def health_check(self) -> Dict[str, bool]:
        """檢查N8N服務健康狀態"""
        logger.info("執行N8N服務健康檢查")
        
        health_status = {}
        
        for endpoint_name, endpoint_path in self.endpoints.items():
            try:
                # 簡單的健康檢查請求
                test_data = {"health_check": True, "timestamp": datetime.now().isoformat()}
                
                response = await self.client.post(
                    endpoint=endpoint_path,
                    json_data=test_data,
                    timeout=10,
                    disable_cache=True
                )
                
                health_status[endpoint_name] = True
                logger.debug(f"N8N端點健康: {endpoint_name}")
                
            except Exception as e:
                health_status[endpoint_name] = False
                logger.warning(f"N8N端點不健康: {endpoint_name}, 錯誤: {e}")
        
        overall_health = all(health_status.values())
        logger.info(f"N8N服務健康檢查完成，整體狀態: {'健康' if overall_health else '不健康'}")
        
        return {
            **health_status,
            'overall_healthy': overall_health,
            'checked_at': datetime.now().isoformat()
        }
    
    # ===== 管理和統計功能 =====
    
    def get_stats(self) -> Dict[str, Any]:
        """獲取服務統計"""
        client_stats = self.client.get_stats()
        
        return {
            "n8n_stats": self.request_stats,
            "http_stats": client_stats,
            "batch_queue_size": len(self.batch_queue),
            "endpoints": list(self.endpoints.keys()),
            "cache_enabled": self.client.cache_enabled,
            "base_url": self.base_url
        }
    
    def clear_cache(self):
        """清空快取"""
        self.client.clear_cache()
        logger.info("N8N服務快取已清空")
    
    def reset_stats(self):
        """重置統計"""
        self.request_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'cached_requests': 0,
            'batch_requests': 0
        }
        logger.info("N8N服務統計已重置")
    
    # ===== 相容性別名方法 =====
    
    async def batch_detect_od_cd(self, sentences: List[str]) -> Dict[str, Any]:
        """批次檢測OD/CD - 相容性別名"""
        # 轉換格式以符合 batch_od_cd_detection 的期望
        paper_sentences_list = [{
            "paper_id": "validation_test",
            "sentences": sentences,
            "title": "Validation Test",
            "authors": []
        }]
        
        results = await self.batch_od_cd_detection(paper_sentences_list)
        
        if results and len(results) > 0:
            return results[0]['detection_result']
        else:
            return {"error": "批次檢測失敗", "success": False}

"""
N8N API整合服務
支援OD/CD檢測、關鍵詞提取、批次呼叫和智能快取
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from datetime import datetime
import json

from ..core.config import settings
from ..core.logging import get_logger
from ..core.http_client import create_client, HTTPClient

logger = get_logger("n8n_service")

@dataclass
class BatchRequest:
    """批次請求項目"""
    id: str
    endpoint: str
    data: Dict[str, Any]
    priority: int = 1  # 1=高優先序, 2=中, 3=低
    retry_count: int = 0
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class BatchResponse:
    """批次回應項目"""
    request_id: str
    success: bool
    data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    processing_time: float = 0.0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class N8NService:
    """N8N API整合服務"""
    
    def __init__(self):
        self.base_url = settings.n8n_base_url
        self.client = create_client(
            base_url=self.base_url,
            timeout=60,  # N8N工作流程可能需要較長時間
            max_retries=3
        )
        
        # API端點配置 (根據 n8n_api_document.md)
        self.endpoints = {
            'od_cd_detection': '/webhook/check-od-cd',
            'keyword_extraction': '/webhook/421337df-0d97-47b4-a96b-a70a6c35d416',
            'intelligent_section_selection': '/webhook/intelligent-section-selection',
            'unified_content_analysis': '/webhook/unified-content-analysis',
            'enhanced_organization': '/webhook/enhanced-organize-response'
        }
        
        # 批次處理配置
        self.batch_queue: List[BatchRequest] = []
        self.max_batch_size = 10
        self.batch_timeout = 30  # 秒
        self.max_concurrent_requests = 5
        
        # 快取配置
        self.client.enable_cache(ttl_seconds=600)  # 10分鐘快取
        
        # 統計追蹤
        self.request_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'cached_requests': 0,
            'batch_requests': 0
        }
        
        logger.info(f"N8N服務初始化完成，基礎URL: {self.base_url}")
    
    # ===== 基礎API呼叫方法 =====
    
    async def _call_n8n_webhook(
        self,
        endpoint_key: str,
        data: Dict[str, Any],
        timeout: int = None,
        disable_cache: bool = False
    ) -> Dict[str, Any]:
        """呼叫N8N webhook"""
        if endpoint_key not in self.endpoints:
            raise ValueError(f"未知的端點: {endpoint_key}")
        
        endpoint = self.endpoints[endpoint_key]
        self.request_stats['total_requests'] += 1
        
        try:
            start_time = time.time()
            
            response = await self.client.post(
                endpoint=endpoint,
                json_data=data,
                timeout=timeout,
                disable_cache=disable_cache
            )
            
            processing_time = time.time() - start_time
            
            if response:
                self.request_stats['successful_requests'] += 1
                logger.debug(f"N8N API成功: {endpoint_key} ({processing_time:.2f}秒)")
                return response
            else:
                self.request_stats['failed_requests'] += 1
                logger.warning(f"N8N API返回空回應: {endpoint_key}")
                return {"error": "空回應"}
                
        except Exception as e:
            self.request_stats['failed_requests'] += 1
            logger.error(f"N8N API呼叫失敗: {endpoint_key}, 錯誤: {e}")
            raise
    
    # ===== 現有API方法 =====
    
    async def detect_od_cd(
        self,
        sentence: str,
        cache_key: str = None
    ) -> Dict[str, Any]:
        """
        OD/CD檢測API (根據 n8n_api_document.md 規格)
        
        Args:
            sentence: 單一句子
            cache_key: 自定義快取鍵
            
        Returns:
            OD/CD檢測結果
        """
        # 根據API文件，使用 application/x-www-form-urlencoded 格式
        request_data = {
            "sentence": sentence
        }
        
        logger.info(f"執行OD/CD檢測: {sentence[:50]}...")
        
        try:
            result = await self.client.post(
                endpoint=self.endpoints['od_cd_detection'],
                data=request_data,  # 使用 data 而非 json_data
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=30,
                disable_cache=(cache_key is None)
            )
            
            # 驗證回應格式 {"defining_type": "string", "reason": "string"}
            if 'defining_type' in result and 'reason' in result:
                logger.info(f"OD/CD檢測完成: {result['defining_type']}")
                return result
            else:
                logger.warning(f"OD/CD檢測回應格式異常: {result}")
                return {"error": "回應格式異常", "raw_response": result}
                
        except Exception as e:
            logger.error(f"OD/CD檢測失敗: {e}")
            return {
                "error": str(e),
                "sentence": sentence,
                "failed_at": datetime.now().isoformat()
            }
    
    async def extract_keywords(
        self,
        query: str
    ) -> Dict[str, Any]:
        """
        關鍵詞提取API (根據 n8n_api_document.md 規格)
        
        Args:
            query: 需要萃取關鍵字的查詢語句
            
        Returns:
            關鍵詞提取結果
        """
        # 根據API文件，使用 application/x-www-form-urlencoded 格式
        request_data = {
            "query": query
        }
        
        logger.info(f"執行關鍵詞提取: {query[:50]}...")
        
        try:
            result = await self.client.post(
                endpoint=self.endpoints['keyword_extraction'],
                data=request_data,  # 使用 data 而非 json_data
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=30
            )
            
            # 驗證回應格式 [{"output": {"keywords": ["string", ...]}}]
            if isinstance(result, list) and len(result) > 0 and 'output' in result[0]:
                keywords = result[0]['output'].get('keywords', [])
                logger.info(f"關鍵詞提取完成，提取到 {len(keywords)} 個關鍵詞")
                return {
                    'keywords': keywords,
                    'total_keywords': len(keywords)
                }
            else:
                logger.warning(f"關鍵詞提取回應格式異常: {result}")
                return {"error": "回應格式異常", "raw_response": result}
                
        except Exception as e:
            logger.error(f"關鍵詞提取失敗: {e}")
            return {
                "error": str(e),
                "query": query,
                "failed_at": datetime.now().isoformat()
            }
    
    # ===== 新API方法 (Backlog #8功能) =====
    
    async def intelligent_section_selection(
        self,
        query: str,
        available_papers: List[Dict[str, Any]],
        max_sections: int = 3
    ) -> Dict[str, Any]:
        """
        智能章節選擇API (根據 n8n_api_document.md 規格)
        
        Args:
            query: 使用者查詢語句
            available_papers: 可用論文及其section摘要列表
            max_sections: 最大選擇章節數
            
        Returns:
            選擇的章節列表及分析策略
        """
        request_data = {
            "query": query,
            "available_papers": available_papers,
            "max_sections": max_sections,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"執行智能章節選擇，查詢: {query[:50]}..., 論文數量: {len(available_papers)}")
        
        try:
            result = await self._call_n8n_webhook(
                'intelligent_section_selection', 
                request_data,
                timeout=120  # 智能選擇可能需要更長時間
            )
            
            # 驗證回應格式符合API文檔
            expected_fields = ['selected_sections', 'analysis_focus', 'suggested_approach']
            if all(field in result for field in expected_fields):
                selected_count = len(result['selected_sections'])
                analysis_focus = result['analysis_focus']
                logger.info(f"智能章節選擇完成，選擇了 {selected_count} 個章節，分析重點: {analysis_focus}")
                return result
            else:
                logger.warning("智能章節選擇回應格式異常")
                return {"error": "回應格式異常", "raw_response": result}
                
        except Exception as e:
            logger.error(f"智能章節選擇失敗: {e}")
            return {
                "error": str(e),
                "query": query,
                "available_papers_count": len(available_papers),
                "failed_at": datetime.now().isoformat()
            }
    
    async def unified_content_analysis(
        self,
        query: str,
        selected_content: List[Dict[str, Any]],
        analysis_focus: str = "definitions"
    ) -> Dict[str, Any]:
        """
        統一內容分析API (根據 n8n_api_document.md 規格)
        
        Args:
            query: 原始查詢語句
            selected_content: LLM選中的section內容
            analysis_focus: 分析重點類型 (definitions, methods, comparison)
            
        Returns:
            統一分析結果包含回應、引用和來源摘要
        """
        request_data = {
            "query": query,
            "selected_content": selected_content,
            "analysis_focus": analysis_focus,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"執行統一內容分析，查詢: {query[:50]}..., 分析重點: {analysis_focus}")
        
        try:
            result = await self._call_n8n_webhook(
                'unified_content_analysis', 
                request_data,
                timeout=180  # 多論文內容分析需要更長時間
            )
            
            # 驗證回應格式符合API文檔
            expected_fields = ['response', 'references', 'source_summary']
            if all(field in result for field in expected_fields):
                reference_count = len(result['references'])
                papers_analyzed = result['source_summary'].get('total_papers', 0)
                logger.info(f"統一內容分析完成，生成 {reference_count} 個引用，分析 {papers_analyzed} 篇論文")
                return result
            else:
                logger.warning("統一內容分析回應格式異常")
                return {"error": "回應格式異常", "raw_response": result}
                
        except Exception as e:
            logger.error(f"統一內容分析失敗: {e}")
            return {
                "error": str(e),
                "query": query,
                "content_count": len(selected_content),
                "analysis_focus": analysis_focus,
                "failed_at": datetime.now().isoformat()
            }
    
    async def enhanced_organization(
        self,
        query: str,
        papers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        增強型組織回應API (根據 n8n_api_document.md 規格 - 向後相容)
        
        Args:
            query: 使用者的查詢語句
            papers: 論文列表，包含操作型和概念型定義
            
        Returns:
            組織後的回應，包含引用和來源摘要
        """
        request_data = {
            "query": query,
            "papers": papers,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"執行增強型組織回應，查詢: {query[:50]}..., 論文數量: {len(papers)}")
        
        try:
            result = await self._call_n8n_webhook(
                'enhanced_organization', 
                request_data,
                timeout=240  # 多檔案處理需要更長時間
            )
            
            # 驗證回應格式符合API文檔
            expected_fields = ['response', 'references', 'source_summary']
            if all(field in result for field in expected_fields):
                reference_count = len(result['references'])
                papers_used = len(result['source_summary'].get('papers_used', []))
                logger.info(f"增強型組織回應完成，生成 {reference_count} 個引用，使用 {papers_used} 篇論文")
                return result
            else:
                logger.warning("增強型組織回應格式異常")
                return {"error": "回應格式異常", "raw_response": result}
                
        except Exception as e:
            logger.error(f"增強型組織回應失敗: {e}")
            return {
                "error": str(e),
                "query": query,
                "papers_count": len(papers),
                "failed_at": datetime.now().isoformat()
            }
    
    # ===== 批次處理功能 =====
    
    async def add_to_batch(
        self,
        request_id: str,
        endpoint_key: str,
        data: Dict[str, Any],
        priority: int = 2
    ) -> bool:
        """添加請求到批次佇列"""
        if len(self.batch_queue) >= self.max_batch_size * 2:  # 限制佇列大小
            logger.warning("批次佇列已滿，丟棄請求")
            return False
        
        batch_request = BatchRequest(
            id=request_id,
            endpoint=endpoint_key,
            data=data,
            priority=priority
        )
        
        self.batch_queue.append(batch_request)
        logger.debug(f"請求已添加到批次佇列: {request_id}")
        return True
    
    async def process_batch(self) -> List[BatchResponse]:
        """處理批次佇列中的請求"""
        if not self.batch_queue:
            return []
        
        # 按優先序排序
        self.batch_queue.sort(key=lambda x: (x.priority, x.created_at))
        
        # 取出要處理的批次
        batch_size = min(len(self.batch_queue), self.max_batch_size)
        current_batch = self.batch_queue[:batch_size]
        self.batch_queue = self.batch_queue[batch_size:]
        
        logger.info(f"開始處理批次，項目數: {batch_size}")
        
        # 創建任務列表
        tasks = []
        for request in current_batch:
            task = self._process_single_batch_request(request)
            tasks.append(task)
        
        # 並發執行，限制併發數
        semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        
        async def bounded_task(task):
            async with semaphore:
                return await task
        
        bounded_tasks = [bounded_task(task) for task in tasks]
        responses = await asyncio.gather(*bounded_tasks, return_exceptions=True)
        
        # 處理結果
        batch_responses = []
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                batch_response = BatchResponse(
                    request_id=current_batch[i].id,
                    success=False,
                    error_message=str(response)
                )
            else:
                batch_response = response
            
            batch_responses.append(batch_response)
        
        self.request_stats['batch_requests'] += len(batch_responses)
        success_count = sum(1 for r in batch_responses if r.success)
        
        logger.info(f"批次處理完成，成功: {success_count}/{len(batch_responses)}")
        return batch_responses
    
    async def _process_single_batch_request(self, request: BatchRequest) -> BatchResponse:
        """處理單個批次請求"""
        start_time = time.time()
        
        try:
            result = await self._call_n8n_webhook(
                request.endpoint,
                request.data,
                disable_cache=False  # 批次請求使用快取
            )
            
            processing_time = time.time() - start_time
            
            return BatchResponse(
                request_id=request.id,
                success=True,
                data=result,
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            
            return BatchResponse(
                request_id=request.id,
                success=False,
                error_message=str(e),
                processing_time=processing_time
            )
    
    # ===== 高級功能 =====
    
    async def batch_od_cd_detection(
        self,
        paper_sentences_list: List[Dict[str, Any]],
        progress_callback: callable = None
    ) -> List[Dict[str, Any]]:
        """
        批次OD/CD檢測
        
        Args:
            paper_sentences_list: 包含paper_id和sentences的列表
            progress_callback: 進度回調函數
            
        Returns:
            批次檢測結果
        """
        logger.info(f"開始批次OD/CD檢測，論文數量: {len(paper_sentences_list)}")
        
        results = []
        total_papers = len(paper_sentences_list)
        
        for i, paper_data in enumerate(paper_sentences_list):
            try:
                paper_id = paper_data.get('paper_id')
                sentences = paper_data.get('sentences', [])
                paper_title = paper_data.get('title', '')
                paper_authors = paper_data.get('authors', [])
                
                # 執行檢測
                detection_result = await self.detect_od_cd(
                    sentences=sentences,
                    paper_title=paper_title,
                    paper_authors=paper_authors,
                    cache_key=f"od_cd_{paper_id}"
                )
                
                results.append({
                    'paper_id': paper_id,
                    'detection_result': detection_result,
                    'success': 'error' not in detection_result
                })
                
                # 進度回調
                if progress_callback:
                    progress = (i + 1) / total_papers
                    await progress_callback(progress, paper_id)
                
                # 避免API限流
                if i < total_papers - 1:
                    await asyncio.sleep(0.5)
                    
            except Exception as e:
                logger.error(f"批次檢測失敗，論文ID: {paper_data.get('paper_id')}, 錯誤: {e}")
                results.append({
                    'paper_id': paper_data.get('paper_id'),
                    'detection_result': {"error": str(e)},
                    'success': False
                })
        
        success_count = sum(1 for r in results if r['success'])
        logger.info(f"批次OD/CD檢測完成，成功: {success_count}/{total_papers}")
        
        return results
    
    async def health_check(self) -> Dict[str, bool]:
        """檢查N8N服務健康狀態"""
        logger.info("執行N8N服務健康檢查")
        
        health_status = {}
        
        for endpoint_name, endpoint_path in self.endpoints.items():
            try:
                # 簡單的健康檢查請求
                test_data = {"health_check": True, "timestamp": datetime.now().isoformat()}
                
                response = await self.client.post(
                    endpoint=endpoint_path,
                    json_data=test_data,
                    timeout=10,
                    disable_cache=True
                )
                
                health_status[endpoint_name] = True
                logger.debug(f"N8N端點健康: {endpoint_name}")
                
            except Exception as e:
                health_status[endpoint_name] = False
                logger.warning(f"N8N端點不健康: {endpoint_name}, 錯誤: {e}")
        
        overall_health = all(health_status.values())
        logger.info(f"N8N服務健康檢查完成，整體狀態: {'健康' if overall_health else '不健康'}")
        
        return {
            **health_status,
            'overall_healthy': overall_health,
            'checked_at': datetime.now().isoformat()
        }
    
    # ===== 管理和統計功能 =====
    
    def get_stats(self) -> Dict[str, Any]:
        """獲取服務統計"""
        client_stats = self.client.get_stats()
        
        return {
            "n8n_stats": self.request_stats,
            "http_stats": client_stats,
            "batch_queue_size": len(self.batch_queue),
            "endpoints": list(self.endpoints.keys()),
            "cache_enabled": self.client.cache_enabled,
            "base_url": self.base_url
        }
    
    def clear_cache(self):
        """清空快取"""
        self.client.clear_cache()
        logger.info("N8N服務快取已清空")
    
    def reset_stats(self):
        """重置統計"""
        self.request_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'cached_requests': 0,
            'batch_requests': 0
        }
        logger.info("N8N服務統計已重置")
    
    # ===== 相容性別名方法 =====
    
    async def batch_detect_od_cd(self, sentences: List[str]) -> Dict[str, Any]:
        """批次檢測OD/CD - 相容性別名"""
        # 轉換格式以符合 batch_od_cd_detection 的期望
        paper_sentences_list = [{
            "paper_id": "validation_test",
            "sentences": sentences,
            "title": "Validation Test",
            "authors": []
        }]
        
        results = await self.batch_od_cd_detection(paper_sentences_list)
        
        if results and len(results) > 0:
            return results[0]['detection_result']
        else:
            return {"error": "批次檢測失敗", "success": False}

# 建立服務實例
n8n_service = N8NService() 