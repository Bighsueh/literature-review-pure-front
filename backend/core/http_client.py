"""
通用HTTP客戶端
支援重試機制、快取、錯誤處理和異步請求
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
from urllib.parse import urljoin

from .config import settings
from .logging import get_logger

logger = get_logger("http_client")

@dataclass
class CacheEntry:
    """快取項目"""
    data: Any
    timestamp: datetime
    expires_at: datetime
    key: str

class ResponseCache:
    """HTTP回應快取"""
    
    def __init__(self, default_ttl_seconds: int = 300):
        self._cache: Dict[str, CacheEntry] = {}
        self.default_ttl = default_ttl_seconds
        self.max_size = 1000  # 最大快取項目數
        
    def _generate_key(self, method: str, url: str, params: Dict = None, data: Dict = None) -> str:
        """生成快取鍵"""
        content = f"{method}:{url}"
        if params:
            content += f":params:{json.dumps(params, sort_keys=True)}"
        if data:
            content += f":data:{json.dumps(data, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, method: str, url: str, params: Dict = None, data: Dict = None) -> Optional[Any]:
        """從快取獲取數據"""
        key = self._generate_key(method, url, params, data)
        
        if key in self._cache:
            entry = self._cache[key]
            if datetime.now() < entry.expires_at:
                logger.debug(f"快取命中: {key[:10]}...")
                return entry.data
            else:
                # 過期項目清理
                del self._cache[key]
                logger.debug(f"快取過期清理: {key[:10]}...")
        
        return None
    
    def set(self, method: str, url: str, data: Any, ttl_seconds: int = None, 
            params: Dict = None, request_data: Dict = None):
        """設置快取數據"""
        if len(self._cache) >= self.max_size:
            self._cleanup_expired()
            
        # 如果仍然滿了，清理最舊的項目
        if len(self._cache) >= self.max_size:
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].timestamp)
            del self._cache[oldest_key]
        
        key = self._generate_key(method, url, params, request_data)
        ttl = ttl_seconds or self.default_ttl
        
        entry = CacheEntry(
            data=data,
            timestamp=datetime.now(),
            expires_at=datetime.now() + timedelta(seconds=ttl),
            key=key
        )
        
        self._cache[key] = entry
        logger.debug(f"快取設置: {key[:10]}..., TTL: {ttl}秒")
    
    def _cleanup_expired(self):
        """清理過期的快取項目"""
        now = datetime.now()
        expired_keys = [key for key, entry in self._cache.items() if now >= entry.expires_at]
        
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            logger.debug(f"清理過期快取項目: {len(expired_keys)} 個")
    
    def clear(self):
        """清空快取"""
        self._cache.clear()
        logger.info("快取已清空")
    
    def stats(self) -> Dict[str, Any]:
        """獲取快取統計"""
        now = datetime.now()
        active_count = sum(1 for entry in self._cache.values() if now < entry.expires_at)
        
        return {
            "total_entries": len(self._cache),
            "active_entries": active_count,
            "expired_entries": len(self._cache) - active_count,
            "max_size": self.max_size,
            "usage_percentage": (len(self._cache) / self.max_size) * 100
        }

class HTTPClient:
    """通用HTTP客戶端，支援重試、快取和錯誤處理"""
    
    def __init__(self, base_url: str = None, timeout: int = 30, max_retries: int = 3):
        self.base_url = base_url
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self.retry_delay = 1  # 初始重試延遲（秒）
        self.retry_backoff = 2  # 重試退避倍數
        
        # 快取設置
        self.cache = ResponseCache()
        self.cache_enabled = True
        
        # 狀態追蹤
        self.request_count = 0
        self.cache_hits = 0
        self.cache_misses = 0
        
        logger.info(f"HTTP客戶端初始化完成，基礎URL: {base_url}")
    
    def _build_url(self, endpoint: str) -> str:
        """構建完整URL"""
        if self.base_url:
            return urljoin(self.base_url, endpoint)
        return endpoint
    
    def _should_cache(self, method: str, status_code: int) -> bool:
        """判斷是否應該快取回應"""
        # 只快取GET請求和200回應
        return method.upper() == 'GET' and status_code == 200
    
    def _should_retry(self, attempt: int, status_code: int, exception: Exception = None) -> bool:
        """判斷是否應該重試"""
        if attempt >= self.max_retries:
            return False
        
        # 重試條件
        if exception:
            # 網路錯誤重試
            if isinstance(exception, (aiohttp.ClientError, asyncio.TimeoutError)):
                return True
        
        # HTTP狀態碼重試條件
        if status_code:
            # 伺服器錯誤重試
            if status_code >= 500:
                return True
            # 限流重試
            if status_code == 429:
                return True
        
        return False
    
    async def _wait_retry(self, attempt: int):
        """重試等待（指數退避）"""
        delay = self.retry_delay * (self.retry_backoff ** (attempt - 1))
        logger.debug(f"重試等待: {delay}秒 (嘗試 {attempt}/{self.max_retries})")
        await asyncio.sleep(delay)
    
    async def request(
        self,
        method: str,
        endpoint: str,
        params: Dict[str, Any] = None,
        data: Dict[str, Any] = None,
        json_data: Dict[str, Any] = None,
        headers: Dict[str, str] = None,
        timeout: int = None,
        cache_ttl: int = None,
        disable_cache: bool = False
    ) -> Dict[str, Any]:
        """
        發送HTTP請求
        
        Args:
            method: HTTP方法
            endpoint: 端點路徑
            params: URL參數
            data: 表單數據
            json_data: JSON數據
            headers: 請求頭
            timeout: 超時時間
            cache_ttl: 快取存活時間
            disable_cache: 禁用快取
            
        Returns:
            回應數據字典
            
        Raises:
            aiohttp.ClientError: 網路錯誤
            asyncio.TimeoutError: 超時錯誤
        """
        self.request_count += 1
        url = self._build_url(endpoint)
        
        # 檢查快取
        if (self.cache_enabled and not disable_cache and 
            method.upper() == 'GET' and not json_data and not data):
            cached_response = self.cache.get(method, url, params)
            if cached_response is not None:
                self.cache_hits += 1
                logger.debug(f"快取命中: {method} {url}")
                return cached_response
            else:
                self.cache_misses += 1
        
        # 準備請求參數
        request_timeout = aiohttp.ClientTimeout(total=timeout or self.timeout.total)
        request_headers = headers or {}
        
        # 重試邏輯
        last_exception = None
        last_status_code = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                async with aiohttp.ClientSession(timeout=request_timeout) as session:
                    logger.debug(f"發送請求: {method} {url} (嘗試 {attempt}/{self.max_retries})")
                    
                    async with session.request(
                        method=method,
                        url=url,
                        params=params,
                        data=data,
                        json=json_data,
                        headers=request_headers
                    ) as response:
                        last_status_code = response.status
                        response_text = await response.text()
                        
                        # 記錄回應
                        logger.debug(f"回應: {response.status} {url} ({len(response_text)} 字符)")
                        
                        if response.status >= 400:
                            # HTTP錯誤
                            if self._should_retry(attempt, response.status):
                                logger.warning(f"HTTP錯誤 {response.status}，準備重試: {url}")
                                await self._wait_retry(attempt)
                                continue
                            else:
                                # 不重試，拋出錯誤
                                error_msg = f"HTTP {response.status}: {response_text[:200]}"
                                logger.error(f"HTTP錯誤: {error_msg}")
                                raise aiohttp.ClientResponseError(
                                    request_info=response.request_info,
                                    history=response.history,
                                    status=response.status,
                                    message=error_msg
                                )
                        
                        # 解析回應
                        try:
                            response_data = json.loads(response_text) if response_text else {}
                        except json.JSONDecodeError:
                            response_data = {"text": response_text}
                        
                        # 快取成功回應
                        if (self.cache_enabled and not disable_cache and 
                            self._should_cache(method, response.status)):
                            self.cache.set(method, url, response_data, cache_ttl, params)
                        
                        return response_data
                        
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_exception = e
                logger.warning(f"請求異常: {type(e).__name__}: {str(e)}")
                
                if self._should_retry(attempt, None, e):
                    logger.info(f"網路錯誤，準備重試: {url}")
                    await self._wait_retry(attempt)
                    continue
                else:
                    # 不重試，拋出錯誤
                    logger.error(f"請求失敗，不再重試: {url}")
                    raise
        
        # 所有重試都失敗了
        if last_exception:
            raise last_exception
        else:
            raise aiohttp.ClientResponseError(
                request_info=None,
                history=(),
                status=last_status_code or 0,
                message=f"請求失敗，已重試 {self.max_retries} 次"
            )
    
    async def get(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """GET請求"""
        return await self.request("GET", endpoint, **kwargs)
    
    async def post(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """POST請求"""
        return await self.request("POST", endpoint, **kwargs)
    
    async def put(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """PUT請求"""
        return await self.request("PUT", endpoint, **kwargs)
    
    async def delete(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """DELETE請求"""
        return await self.request("DELETE", endpoint, **kwargs)
    
    def enable_cache(self, ttl_seconds: int = 300):
        """啟用快取"""
        self.cache_enabled = True
        self.cache.default_ttl = ttl_seconds
        logger.info(f"快取已啟用，預設TTL: {ttl_seconds}秒")
    
    def disable_cache(self):
        """禁用快取"""
        self.cache_enabled = False
        logger.info("快取已禁用")
    
    def clear_cache(self):
        """清空快取"""
        self.cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """獲取客戶端統計"""
        cache_stats = self.cache.stats()
        
        return {
            "requests": {
                "total": self.request_count,
                "cache_hits": self.cache_hits,
                "cache_misses": self.cache_misses,
                "cache_hit_rate": (self.cache_hits / max(self.request_count, 1)) * 100
            },
            "cache": cache_stats,
            "config": {
                "base_url": self.base_url,
                "timeout": self.timeout.total,
                "max_retries": self.max_retries,
                "cache_enabled": self.cache_enabled
            }
        }
    
    async def health_check(self, endpoint: str = "/health") -> bool:
        """健康檢查"""
        try:
            response = await self.get(endpoint, timeout=5, disable_cache=True)
            return True
        except Exception as e:
            logger.warning(f"健康檢查失敗: {e}")
            return False

def create_client(base_url: str, timeout: int = 30, max_retries: int = 3) -> HTTPClient:
    """建立專用HTTP客戶端"""
    return HTTPClient(base_url=base_url, timeout=timeout, max_retries=max_retries) 