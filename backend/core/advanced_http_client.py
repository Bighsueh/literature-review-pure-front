"""
進階HTTP客戶端
支援超高並發、自適應連接池、重試機制和性能監控
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import hashlib
from urllib.parse import urljoin
import threading
from concurrent.futures import ThreadPoolExecutor
import resource

from .config import settings
from .logging import get_logger

logger = get_logger("advanced_http_client")

@dataclass
class ConnectionPoolConfig:
    """連接池配置"""
    total_pool_size: int = 200         # 總連接池大小
    per_host_limit: int = 50           # 每主機連接限制
    keepalive_timeout: int = 60        # Keep-alive超時
    timeout_socket_connect: int = 10   # Socket連接超時
    timeout_sock_read: int = 30        # Socket讀取超時
    enable_cleanup_closed: bool = True
    ttl_dns_cache: int = 300          # DNS快取TTL

@dataclass
class PerformanceMetrics:
    """性能指標"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    concurrent_requests: int = 0
    max_concurrent_reached: int = 0
    avg_response_time: float = 0.0
    response_times: List[float] = field(default_factory=list)
    requests_per_second: float = 0.0
    last_reset: datetime = field(default_factory=datetime.now)

class AdvancedHTTPClient:
    """進階HTTP客戶端，支援超高並發和性能優化"""
    
    def __init__(
        self, 
        base_url: str = None, 
        pool_config: ConnectionPoolConfig = None,
        max_concurrent_requests: int = 50,
        enable_threading: bool = True
    ):
        self.base_url = base_url
        self.pool_config = pool_config or ConnectionPoolConfig()
        self.max_concurrent_requests = max_concurrent_requests
        self.enable_threading = enable_threading
        
        # 性能監控
        self.metrics = PerformanceMetrics()
        self._metrics_lock = threading.Lock()
        
        # 並發控制
        self._semaphore = asyncio.Semaphore(max_concurrent_requests)
        
        # 連接器和session
        self._connector = None
        self._session = None
        self._thread_pool = None
        
        # 自適應配置
        self._auto_tune_enabled = True
        self._last_tune_time = datetime.now()
        
        self._initialize_resources()
        
        logger.info(f"進階HTTP客戶端初始化完成")
        logger.info(f"  - 基礎URL: {base_url}")
        logger.info(f"  - 最大並發: {max_concurrent_requests}")
        logger.info(f"  - 每主機連接限制: {self.pool_config.per_host_limit}")
        logger.info(f"  - 總連接池: {self.pool_config.total_pool_size}")
        logger.info(f"  - 多執行緒支援: {enable_threading}")
    
    def _initialize_resources(self):
        """初始化系統資源"""
        try:
            # 增加檔案描述符限制
            soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
            if soft < 4096:
                try:
                    resource.setrlimit(resource.RLIMIT_NOFILE, (min(4096, hard), hard))
                    logger.info(f"檔案描述符限制已提升至 {min(4096, hard)}")
                except:
                    logger.warning("無法提升檔案描述符限制")
            
            # 創建執行緒池
            if self.enable_threading:
                max_workers = min(32, (self.max_concurrent_requests // 2) + 4)
                self._thread_pool = ThreadPoolExecutor(max_workers=max_workers)
                logger.info(f"執行緒池創建完成，工作執行緒: {max_workers}")
        
        except Exception as e:
            logger.warning(f"資源初始化警告: {e}")
    
    async def _get_session(self):
        """獲取或創建高性能session"""
        if self._session is None or self._session.closed:
            # 創建高性能連接器
            self._connector = aiohttp.TCPConnector(
                limit=self.pool_config.total_pool_size,
                limit_per_host=self.pool_config.per_host_limit,
                keepalive_timeout=self.pool_config.keepalive_timeout,
                enable_cleanup_closed=self.pool_config.enable_cleanup_closed,
                ttl_dns_cache=self.pool_config.ttl_dns_cache,
                use_dns_cache=True,
                # 進階TCP配置
                sock_connect=self.pool_config.timeout_socket_connect,
                sock_read=self.pool_config.timeout_sock_read
            )
            
            # 創建session
            timeout = aiohttp.ClientTimeout(
                total=None,  # 不設全局超時
                sock_connect=self.pool_config.timeout_socket_connect,
                sock_read=self.pool_config.timeout_sock_read
            )
            
            self._session = aiohttp.ClientSession(
                connector=self._connector,
                timeout=timeout,
                trust_env=True
            )
            
            logger.debug("高性能HTTP session創建完成")
        
        return self._session
    
    def _update_metrics(self, response_time: float, success: bool):
        """更新性能指標"""
        with self._metrics_lock:
            self.metrics.total_requests += 1
            if success:
                self.metrics.successful_requests += 1
            else:
                self.metrics.failed_requests += 1
            
            # 更新回應時間
            self.metrics.response_times.append(response_time)
            if len(self.metrics.response_times) > 100:  # 保持最近100個記錄
                self.metrics.response_times.pop(0)
            
            self.metrics.avg_response_time = sum(self.metrics.response_times) / len(self.metrics.response_times)
            
            # 計算RPS
            now = datetime.now()
            time_diff = (now - self.metrics.last_reset).total_seconds()
            if time_diff > 0:
                self.metrics.requests_per_second = self.metrics.total_requests / time_diff
    
    def _auto_tune_performance(self):
        """自動調校性能參數"""
        if not self._auto_tune_enabled:
            return
        
        now = datetime.now()
        if (now - self._last_tune_time).total_seconds() < 30:  # 每30秒調校一次
            return
        
        with self._metrics_lock:
            # 根據性能指標調校參數
            if self.metrics.avg_response_time > 2.0 and self.pool_config.per_host_limit > 10:
                # 回應時間過長，減少並發
                self.pool_config.per_host_limit = max(10, self.pool_config.per_host_limit - 5)
                logger.info(f"自動調校：降低並發至 {self.pool_config.per_host_limit}")
            
            elif self.metrics.avg_response_time < 0.5 and self.pool_config.per_host_limit < 100:
                # 回應快速，可增加並發
                self.pool_config.per_host_limit = min(100, self.pool_config.per_host_limit + 5)
                logger.info(f"自動調校：提升並發至 {self.pool_config.per_host_limit}")
        
        self._last_tune_time = now
    
    async def request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """發送高並發HTTP請求"""
        start_time = time.time()
        
        # 並發控制
        async with self._semaphore:
            with self._metrics_lock:
                self.metrics.concurrent_requests += 1
                if self.metrics.concurrent_requests > self.metrics.max_concurrent_reached:
                    self.metrics.max_concurrent_reached = self.metrics.concurrent_requests
            
            try:
                # 自動調校
                self._auto_tune_performance()
                
                # 構建URL
                url = urljoin(self.base_url, endpoint) if self.base_url else endpoint
                
                # 獲取session
                session = await self._get_session()
                
                # 發送請求
                async with session.request(method, url, **kwargs) as response:
                    response_text = await response.text()
                    
                    # 處理回應
                    if response.status >= 400:
                        raise aiohttp.ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status,
                            message=f"HTTP {response.status}: {response_text[:200]}"
                        )
                    
                    # 解析JSON
                    try:
                        data = json.loads(response_text) if response_text else {}
                    except json.JSONDecodeError:
                        data = {"text": response_text}
                    
                    # 更新指標
                    response_time = time.time() - start_time
                    self._update_metrics(response_time, True)
                    
                    logger.debug(f"請求成功: {method} {url} ({response_time:.3f}s)")
                    return data
            
            except Exception as e:
                response_time = time.time() - start_time
                self._update_metrics(response_time, False)
                logger.error(f"請求失敗: {method} {endpoint} - {e}")
                raise
            
            finally:
                with self._metrics_lock:
                    self.metrics.concurrent_requests -= 1
    
    async def batch_request(
        self,
        requests: List[Dict[str, Any]],
        progress_callback: Optional[Callable] = None
    ) -> List[Dict[str, Any]]:
        """批次處理多個請求"""
        tasks = []
        
        for i, req in enumerate(requests):
            method = req.pop('method', 'GET')
            endpoint = req.pop('endpoint')
            task = self.request(method, endpoint, **req)
            tasks.append((i, task))
        
        logger.info(f"開始批次處理 {len(tasks)} 個請求")
        
        # 並發執行
        results = [None] * len(requests)
        completed = 0
        
        for i, task in tasks:
            try:
                result = await task
                results[i] = {"success": True, "data": result}
            except Exception as e:
                results[i] = {"success": False, "error": str(e)}
            
            completed += 1
            if progress_callback:
                await progress_callback(completed, len(requests))
        
        return results
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """獲取性能統計"""
        with self._metrics_lock:
            return {
                "metrics": {
                    "total_requests": self.metrics.total_requests,
                    "successful_requests": self.metrics.successful_requests,
                    "failed_requests": self.metrics.failed_requests,
                    "success_rate": (self.metrics.successful_requests / max(self.metrics.total_requests, 1)) * 100,
                    "current_concurrent": self.metrics.concurrent_requests,
                    "max_concurrent_reached": self.metrics.max_concurrent_reached,
                    "avg_response_time": self.metrics.avg_response_time,
                    "requests_per_second": self.metrics.requests_per_second
                },
                "config": {
                    "max_concurrent_requests": self.max_concurrent_requests,
                    "per_host_limit": self.pool_config.per_host_limit,
                    "total_pool_size": self.pool_config.total_pool_size,
                    "auto_tune_enabled": self._auto_tune_enabled
                },
                "connection_pool": {
                    "active_connections": getattr(self._connector, '_acquired', 0) if self._connector else 0,
                    "pool_usage": f"{getattr(self._connector, '_acquired', 0)}/{self.pool_config.total_pool_size}"
                }
            }
    
    async def close(self):
        """關閉客戶端和資源"""
        if self._session and not self._session.closed:
            await self._session.close()
        
        if self._connector:
            await self._connector.close()
        
        if self._thread_pool:
            self._thread_pool.shutdown(wait=True)
        
        logger.info("進階HTTP客戶端已關閉")

def create_advanced_client(
    base_url: str,
    max_concurrent: int = 50,
    pool_config: ConnectionPoolConfig = None
) -> AdvancedHTTPClient:
    """創建進階HTTP客戶端"""
    return AdvancedHTTPClient(
        base_url=base_url,
        pool_config=pool_config,
        max_concurrent_requests=max_concurrent,
        enable_threading=True
    ) 