"""
高性能N8N API服務
專為大量並發請求優化，支援動態負載平衡和請求池管理
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import json
import random

from ..core.config import settings
from ..core.logging import get_logger
from ..core.advanced_http_client import create_advanced_client, ConnectionPoolConfig

logger = get_logger("high_performance_n8n")

@dataclass
class RequestBatch:
    """請求批次"""
    requests: List[Dict[str, Any]]
    batch_id: str
    created_at: datetime
    priority: int = 1
    
    def __post_init__(self):
        if not hasattr(self, 'created_at'):
            self.created_at = datetime.now()

@dataclass
class LoadBalancerConfig:
    """負載平衡配置"""
    max_requests_per_second: int = 100
    burst_limit: int = 200
    circuit_breaker_threshold: int = 10  # 連續失敗次數
    health_check_interval: int = 30      # 健康檢查間隔（秒）
    adaptive_scaling: bool = True        # 自適應擴展

class HighPerformanceN8N:
    """高性能N8N API服務"""
    
    def __init__(self):
        self.base_url = getattr(settings, 'N8N_BASE_URL', 'http://localhost:5678')
        
        # 高性能HTTP客戶端配置
        pool_config = ConnectionPoolConfig(
            total_pool_size=500,    # 增加總連接池
            per_host_limit=100,     # 大幅增加每主機限制
            keepalive_timeout=120,  # 延長keep-alive
            timeout_socket_connect=5,
            timeout_sock_read=60
        )
        
        # 創建多個客戶端實例以分散負載
        self.client_pool = []
        for i in range(3):  # 創建3個客戶端實例
            client = create_advanced_client(
                base_url=self.base_url,
                max_concurrent=100,  # 每個客戶端100並發
                pool_config=pool_config
            )
            self.client_pool.append(client)
        
        # 負載平衡配置
        self.lb_config = LoadBalancerConfig()
        self._current_client_index = 0
        self._client_health = [True] * len(self.client_pool)
        self._circuit_breaker_counts = [0] * len(self.client_pool)
        
        # 批次處理配置
        self.max_batch_size = 50
        self.batch_queue = []
        self.batch_processing = False
        
        # 性能監控
        self.request_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'avg_response_time': 0.0,
            'peak_rps': 0.0,
            'current_rps': 0.0
        }
        
        # API端點配置
        self.endpoints = {
            'od_cd_detection': '/webhook/check-od-cd',
            'keyword_extraction': '/webhook/extract-keywords',
            'intelligent_section_selection': '/webhook/intelligent-section-selection',
            'unified_content_analysis': '/webhook/unified-content-analysis',
            'enhanced_organization': '/webhook/enhanced-organization'
        }
        
        # 啟動健康檢查
        asyncio.create_task(self._health_check_loop())
        
        logger.info("高性能N8N服務初始化完成")
        logger.info(f"  - 客戶端實例: {len(self.client_pool)}")
        logger.info(f"  - 總並發能力: {len(self.client_pool) * 100}")
        logger.info(f"  - 總連接池: {pool_config.total_pool_size}")
        logger.info(f"  - 每主機限制: {pool_config.per_host_limit}")
    
    def _get_next_client(self):
        """負載平衡選擇客戶端"""
        # 輪詢選擇健康的客戶端
        for _ in range(len(self.client_pool)):
            client_index = self._current_client_index % len(self.client_pool)
            self._current_client_index += 1
            
            if self._client_health[client_index]:
                return self.client_pool[client_index], client_index
        
        # 如果沒有健康的客戶端，選擇第一個
        logger.warning("沒有健康的客戶端，使用第一個")
        return self.client_pool[0], 0
    
    async def _health_check_loop(self):
        """健康檢查循環"""
        while True:
            try:
                await asyncio.sleep(self.lb_config.health_check_interval)
                
                # 檢查每個客戶端的健康狀態
                for i, client in enumerate(self.client_pool):
                    try:
                        # 簡單的健康檢查請求
                        start_time = time.time()
                        await client.request(
                            'POST',
                            self.endpoints['od_cd_detection'],
                            data={'sentence': 'health check'},
                            timeout=10
                        )
                        response_time = time.time() - start_time
                        
                        # 重置熔斷器
                        if self._circuit_breaker_counts[i] > 0:
                            self._circuit_breaker_counts[i] = max(0, self._circuit_breaker_counts[i] - 1)
                        
                        self._client_health[i] = True
                        logger.debug(f"客戶端 {i} 健康檢查通過 ({response_time:.3f}s)")
                        
                    except Exception as e:
                        self._circuit_breaker_counts[i] += 1
                        if self._circuit_breaker_counts[i] >= self.lb_config.circuit_breaker_threshold:
                            self._client_health[i] = False
                            logger.warning(f"客戶端 {i} 健康檢查失敗，標記為不健康: {e}")
                        else:
                            logger.debug(f"客戶端 {i} 健康檢查失敗: {e}")
                
                healthy_count = sum(self._client_health)
                logger.info(f"健康檢查完成，健康客戶端: {healthy_count}/{len(self.client_pool)}")
                
            except Exception as e:
                logger.error(f"健康檢查循環異常: {e}")
    
    async def detect_od_cd_batch(
        self, 
        sentences: List[str], 
        progress_callback: Optional[Callable] = None
    ) -> List[Dict[str, Any]]:
        """高並發批次OD/CD檢測"""
        if not sentences:
            return []
        
        logger.info(f"開始高並發OD/CD檢測，句子數量: {len(sentences)}")
        start_time = time.time()
        
        # 創建檢測任務
        tasks = []
        for i, sentence in enumerate(sentences):
            task = self._detect_single_od_cd(sentence, f"batch_{i}")
            tasks.append((i, task))
        
        # 分批並發處理
        batch_size = self.max_batch_size
        all_results = [None] * len(sentences)
        processed_count = 0
        
        for i in range(0, len(tasks), batch_size):
            batch_tasks = tasks[i:i + batch_size]
            logger.debug(f"處理批次 {i//batch_size + 1}, 任務數: {len(batch_tasks)}")
            
            # 並發執行當前批次
            batch_results = await asyncio.gather(
                *[task for _, task in batch_tasks], 
                return_exceptions=True
            )
            
            # 處理結果
            for j, result in enumerate(batch_results):
                task_index, _ = batch_tasks[j]
                
                if isinstance(result, Exception):
                    all_results[task_index] = {
                        "sentence": sentences[task_index],
                        "result": {"error": str(result), "defining_type": "UNKNOWN", "reason": "檢測失敗"}
                    }
                else:
                    all_results[task_index] = {
                        "sentence": sentences[task_index],
                        "result": result
                    }
                
                processed_count += 1
                
                # 進度回調
                if progress_callback:
                    await progress_callback(processed_count, len(sentences))
        
        # 更新統計
        total_time = time.time() - start_time
        rps = len(sentences) / total_time if total_time > 0 else 0
        self.request_stats['total_requests'] += len(sentences)
        self.request_stats['current_rps'] = rps
        if rps > self.request_stats['peak_rps']:
            self.request_stats['peak_rps'] = rps
        
        successful_count = sum(1 for r in all_results if "error" not in r["result"])
        self.request_stats['successful_requests'] += successful_count
        self.request_stats['failed_requests'] += len(sentences) - successful_count
        
        logger.info(f"高並發OD/CD檢測完成")
        logger.info(f"  - 處理時間: {total_time:.2f}秒")
        logger.info(f"  - 處理速度: {rps:.1f} RPS")
        logger.info(f"  - 成功率: {successful_count/len(sentences)*100:.1f}%")
        
        return all_results
    
    async def _detect_single_od_cd(self, sentence: str, request_id: str) -> Dict[str, Any]:
        """單句OD/CD檢測"""
        client, client_index = self._get_next_client()
        
        try:
            result = await client.request(
                'POST',
                self.endpoints['od_cd_detection'],
                data={'sentence': sentence},
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            
            # 驗證回應格式
            if 'defining_type' in result and 'reason' in result:
                return result
            else:
                return {"error": "回應格式異常", "defining_type": "UNKNOWN", "reason": "格式錯誤"}
        
        except Exception as e:
            # 記錄客戶端錯誤
            self._circuit_breaker_counts[client_index] += 1
            logger.error(f"OD/CD檢測失敗 (客戶端 {client_index}): {e}")
            return {"error": str(e), "defining_type": "UNKNOWN", "reason": "檢測異常"}
    
    async def extract_keywords_batch(
        self, 
        queries: List[str], 
        progress_callback: Optional[Callable] = None
    ) -> List[Dict[str, Any]]:
        """批次關鍵詞提取"""
        if not queries:
            return []
        
        logger.info(f"開始批次關鍵詞提取，查詢數量: {len(queries)}")
        
        # 創建任務
        tasks = []
        for i, query in enumerate(queries):
            task = self._extract_single_keywords(query, f"keywords_{i}")
            tasks.append((i, task))
        
        # 並發執行
        results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
        
        # 處理結果
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append({
                    "query": queries[i],
                    "keywords": [],
                    "error": str(result)
                })
            else:
                final_results.append({
                    "query": queries[i],
                    **result
                })
            
            # 進度回調
            if progress_callback:
                await progress_callback(i + 1, len(queries))
        
        return final_results
    
    async def _extract_single_keywords(self, query: str, request_id: str) -> Dict[str, Any]:
        """單個關鍵詞提取"""
        client, client_index = self._get_next_client()
        
        try:
            result = await client.request(
                'POST',
                self.endpoints['keyword_extraction'],
                data={'query': query},
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            
            # 處理回應格式
            if isinstance(result, list) and len(result) > 0 and 'output' in result[0]:
                keywords = result[0]['output'].get('keywords', [])
                return {
                    'keywords': keywords,
                    'total_keywords': len(keywords)
                }
            else:
                return {"keywords": [], "error": "回應格式異常"}
        
        except Exception as e:
            self._circuit_breaker_counts[client_index] += 1
            logger.error(f"關鍵詞提取失敗 (客戶端 {client_index}): {e}")
            return {"keywords": [], "error": str(e)}
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """獲取性能統計"""
        # 收集所有客戶端的統計
        client_stats = []
        total_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_response_time": 0.0
        }
        
        for i, client in enumerate(self.client_pool):
            stats = client.get_performance_stats()
            client_stats.append({
                "client_id": i,
                "healthy": self._client_health[i],
                "circuit_breaker_count": self._circuit_breaker_counts[i],
                **stats
            })
            
            # 累計統計
            metrics = stats.get("metrics", {})
            total_stats["total_requests"] += metrics.get("total_requests", 0)
            total_stats["successful_requests"] += metrics.get("successful_requests", 0)
            total_stats["failed_requests"] += metrics.get("failed_requests", 0)
        
        # 計算平均回應時間
        total_requests = max(total_stats["total_requests"], 1)
        avg_response_times = [
            stats.get("metrics", {}).get("avg_response_time", 0) 
            for stats in client_stats
        ]
        total_stats["avg_response_time"] = sum(avg_response_times) / len(avg_response_times)
        
        return {
            "high_performance_stats": self.request_stats,
            "total_stats": total_stats,
            "client_pool_stats": client_stats,
            "load_balancer": {
                "healthy_clients": sum(self._client_health),
                "total_clients": len(self.client_pool),
                "circuit_breaker_active": sum(1 for count in self._circuit_breaker_counts if count >= self.lb_config.circuit_breaker_threshold)
            },
            "configuration": {
                "max_concurrent_per_client": 100,
                "total_concurrent_capacity": len(self.client_pool) * 100,
                "batch_size": self.max_batch_size
            }
        }
    
    async def close(self):
        """關閉所有資源"""
        for client in self.client_pool:
            await client.close()
        logger.info("高性能N8N服務已關閉")

# 建立全局高性能N8N服務實例
high_performance_n8n = HighPerformanceN8N() 