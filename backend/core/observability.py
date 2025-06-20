import time
import functools
import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from collections import defaultdict, deque
import threading
from uuid import uuid4
import psutil
import logging

from .logging import get_logger
from .config import settings

logger = get_logger("observability")

class MetricsCollector:
    """指標收集器"""
    
    def __init__(self):
        self.metrics = defaultdict(list)
        self.counters = defaultdict(int)
        self.gauges = defaultdict(float)
        self.histograms = defaultdict(lambda: deque(maxlen=1000))
        self.lock = threading.Lock()
        
    def increment_counter(self, metric_name: str, value: int = 1, tags: Optional[Dict[str, str]] = None):
        """增加計數器"""
        with self.lock:
            key = self._build_key(metric_name, tags)
            self.counters[key] += value
            
    def set_gauge(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """設置儀表值"""
        with self.lock:
            key = self._build_key(metric_name, tags)
            self.gauges[key] = value
            
    def record_histogram(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """記錄直方圖值"""
        with self.lock:
            key = self._build_key(metric_name, tags)
            self.histograms[key].append({
                'value': value,
                'timestamp': datetime.now()
            })
            
    def _build_key(self, metric_name: str, tags: Optional[Dict[str, str]] = None) -> str:
        """構建指標鍵"""
        if not tags:
            return metric_name
        tag_str = ",".join([f"{k}={v}" for k, v in sorted(tags.items())])
        return f"{metric_name}[{tag_str}]"
        
    def get_metrics(self) -> Dict[str, Any]:
        """取得所有指標"""
        with self.lock:
            return {
                'counters': dict(self.counters),
                'gauges': dict(self.gauges),
                'histograms': {k: list(v) for k, v in self.histograms.items()},
                'timestamp': datetime.now().isoformat()
            }
            
    def reset_metrics(self):
        """重設指標"""
        with self.lock:
            self.counters.clear()
            self.gauges.clear()
            self.histograms.clear()

class PerformanceMonitor:
    """效能監控器"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self.active_requests = {}
        self.lock = threading.Lock()
        
    def start_request(self, request_id: str, endpoint: str, method: str) -> str:
        """開始請求追蹤"""
        if not request_id:
            request_id = str(uuid4())
            
        with self.lock:
            self.active_requests[request_id] = {
                'endpoint': endpoint,
                'method': method,
                'start_time': time.time(),
                'start_datetime': datetime.now()
            }
            
        self.metrics.increment_counter(
            'http_requests_total',
            tags={'endpoint': endpoint, 'method': method}
        )
        
        return request_id
        
    def end_request(self, request_id: str, status_code: int, error: Optional[str] = None):
        """結束請求追蹤"""
        with self.lock:
            if request_id not in self.active_requests:
                return
                
            request_info = self.active_requests.pop(request_id)
            
        duration = time.time() - request_info['start_time']
        
        # 記錄響應時間
        self.metrics.record_histogram(
            'http_request_duration_seconds',
            duration,
            tags={
                'endpoint': request_info['endpoint'],
                'method': request_info['method'],
                'status': str(status_code)
            }
        )
        
        # 記錄錯誤
        if error:
            self.metrics.increment_counter(
                'http_errors_total',
                tags={
                    'endpoint': request_info['endpoint'],
                    'method': request_info['method'],
                    'error_type': error
                }
            )
            
    def get_active_requests(self) -> Dict[str, Any]:
        """取得活躍請求"""
        with self.lock:
            return dict(self.active_requests)

class HealthChecker:
    """健康檢查器"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self.checks = {}
        
    def register_check(self, name: str, check_func: Callable[[], bool], critical: bool = False):
        """註冊健康檢查"""
        self.checks[name] = {
            'func': check_func,
            'critical': critical,
            'last_result': None,
            'last_check': None
        }
        
    async def run_health_checks(self) -> Dict[str, Any]:
        """執行所有健康檢查"""
        results = {}
        overall_status = "healthy"
        
        for name, check_info in self.checks.items():
            try:
                start_time = time.time()
                
                if asyncio.iscoroutinefunction(check_info['func']):
                    result = await check_info['func']()
                else:
                    result = check_info['func']()
                    
                duration = time.time() - start_time
                
                check_info['last_result'] = result
                check_info['last_check'] = datetime.now()
                
                results[name] = {
                    'status': 'pass' if result else 'fail',
                    'duration_ms': round(duration * 1000, 2),
                    'critical': check_info['critical'],
                    'last_check': check_info['last_check'].isoformat()
                }
                
                # 記錄健康檢查指標
                self.metrics.set_gauge(
                    f'health_check_{name}',
                    1.0 if result else 0.0
                )
                
                self.metrics.record_histogram(
                    'health_check_duration_seconds',
                    duration,
                    tags={'check': name}
                )
                
                # 如果是關鍵檢查且失敗，標記整體狀態為不健康
                if check_info['critical'] and not result:
                    overall_status = "unhealthy"
                elif not result and overall_status == "healthy":
                    overall_status = "degraded"
                    
            except Exception as e:
                logger.error(f"健康檢查失敗 {name}: {str(e)}")
                results[name] = {
                    'status': 'error',
                    'error': str(e),
                    'critical': check_info['critical'],
                    'last_check': datetime.now().isoformat()
                }
                
                if check_info['critical']:
                    overall_status = "unhealthy"
                elif overall_status == "healthy":
                    overall_status = "degraded"
                    
        return {
            'status': overall_status,
            'checks': results,
            'timestamp': datetime.now().isoformat()
        }

class SystemMonitor:
    """系統監控器"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        
    def collect_system_metrics(self):
        """收集系統指標"""
        try:
            # CPU 使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            self.metrics.set_gauge('system_cpu_percent', cpu_percent)
            
            # 記憶體使用率
            memory = psutil.virtual_memory()
            self.metrics.set_gauge('system_memory_percent', memory.percent)
            self.metrics.set_gauge('system_memory_available_bytes', memory.available)
            self.metrics.set_gauge('system_memory_used_bytes', memory.used)
            
            # 磁碟使用率
            disk = psutil.disk_usage('/')
            self.metrics.set_gauge('system_disk_percent', disk.percent)
            self.metrics.set_gauge('system_disk_free_bytes', disk.free)
            self.metrics.set_gauge('system_disk_used_bytes', disk.used)
            
            # 網路統計
            network = psutil.net_io_counters()
            self.metrics.set_gauge('system_network_bytes_sent', network.bytes_sent)
            self.metrics.set_gauge('system_network_bytes_recv', network.bytes_recv)
            
            # 程序統計
            process = psutil.Process()
            self.metrics.set_gauge('process_memory_rss_bytes', process.memory_info().rss)
            self.metrics.set_gauge('process_memory_vms_bytes', process.memory_info().vms)
            self.metrics.set_gauge('process_cpu_percent', process.cpu_percent())
            
            # 檔案描述符
            self.metrics.set_gauge('process_open_fds', process.num_fds())
            
        except Exception as e:
            logger.error(f"收集系統指標失敗: {str(e)}")

class ObservabilityManager:
    """可觀測性管理器"""
    
    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.performance_monitor = PerformanceMonitor(self.metrics_collector)
        self.health_checker = HealthChecker(self.metrics_collector)
        self.system_monitor = SystemMonitor(self.metrics_collector)
        
        # 註冊基本健康檢查
        self._register_basic_health_checks()
        
    def _register_basic_health_checks(self):
        """註冊基本健康檢查"""
        
        def check_memory():
            """檢查記憶體使用率"""
            memory = psutil.virtual_memory()
            return memory.percent < 90  # 記憶體使用率小於90%
            
        def check_disk():
            """檢查磁碟空間"""
            disk = psutil.disk_usage('/')
            return disk.percent < 95  # 磁碟使用率小於95%
            
        def check_cpu():
            """檢查CPU使用率"""
            cpu_percent = psutil.cpu_percent(interval=1)
            return cpu_percent < 95  # CPU使用率小於95%
            
        self.health_checker.register_check('memory', check_memory, critical=True)
        self.health_checker.register_check('disk', check_disk, critical=True)
        self.health_checker.register_check('cpu', check_cpu, critical=False)
        
    async def get_observability_data(self) -> Dict[str, Any]:
        """取得完整的可觀測性資料"""
        # 收集系統指標
        self.system_monitor.collect_system_metrics()
        
        # 執行健康檢查
        health_data = await self.health_checker.run_health_checks()
        
        # 取得指標
        metrics_data = self.metrics_collector.get_metrics()
        
        # 取得活躍請求
        active_requests = self.performance_monitor.get_active_requests()
        
        return {
            'health': health_data,
            'metrics': metrics_data,
            'active_requests': active_requests,
            'system_info': {
                'python_version': psutil.PYTHON,
                'boot_time': datetime.fromtimestamp(psutil.boot_time()).isoformat(),
                'cpu_count': psutil.cpu_count(),
            },
            'timestamp': datetime.now().isoformat()
        }

# 全域可觀測性管理器實例
observability = ObservabilityManager()

# 裝飾器用於自動追蹤函數效能
def monitor_performance(metric_name: Optional[str] = None):
    """效能監控裝飾器"""
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            name = metric_name or f"{func.__module__}.{func.__name__}"
            start_time = time.time()
            
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                    
                duration = time.time() - start_time
                observability.metrics_collector.record_histogram(
                    f'function_duration_seconds',
                    duration,
                    tags={'function': name}
                )
                
                observability.metrics_collector.increment_counter(
                    f'function_calls_total',
                    tags={'function': name, 'status': 'success'}
                )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                observability.metrics_collector.record_histogram(
                    f'function_duration_seconds',
                    duration,
                    tags={'function': name}
                )
                
                observability.metrics_collector.increment_counter(
                    f'function_calls_total',
                    tags={'function': name, 'status': 'error'}
                )
                
                raise
                
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            name = metric_name or f"{func.__module__}.{func.__name__}"
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                observability.metrics_collector.record_histogram(
                    f'function_duration_seconds',
                    duration,
                    tags={'function': name}
                )
                
                observability.metrics_collector.increment_counter(
                    f'function_calls_total',
                    tags={'function': name, 'status': 'success'}
                )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                observability.metrics_collector.record_histogram(
                    f'function_duration_seconds',
                    duration,
                    tags={'function': name}
                )
                
                observability.metrics_collector.increment_counter(
                    f'function_calls_total',
                    tags={'function': name, 'status': 'error'}
                )
                
                raise
                
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
            
    return decorator