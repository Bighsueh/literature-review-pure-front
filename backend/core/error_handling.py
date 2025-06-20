"""
統一的API錯誤處理和重試機制
實現RFC 7807標準的錯誤響應格式
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from functools import wraps
import structlog
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import traceback

from .logging import get_logger

logger = get_logger(__name__)

# 錯誤代碼常量
class ErrorCodes:
    # 認證和授權錯誤
    AUTHENTICATION_FAILED = "AUTH_001"
    INVALID_TOKEN = "AUTH_002"
    TOKEN_EXPIRED = "AUTH_003"
    AUTHORIZATION_FAILED = "AUTH_004"
    
    # 資源錯誤
    RESOURCE_NOT_FOUND = "RESOURCE_001"
    RESOURCE_CONFLICT = "RESOURCE_002"
    RESOURCE_ALREADY_EXISTS = "RESOURCE_003"
    
    # 檔案處理錯誤
    FILE_TOO_LARGE = "FILE_001"
    FILE_INVALID_FORMAT = "FILE_002"
    FILE_UPLOAD_FAILED = "FILE_003"
    FILE_PROCESSING_FAILED = "FILE_004"
    
    # 工作區錯誤
    WORKSPACE_NOT_FOUND = "WORKSPACE_001"
    WORKSPACE_ACCESS_DENIED = "WORKSPACE_002"
    WORKSPACE_NAME_CONFLICT = "WORKSPACE_003"
    
    # 系統錯誤
    DATABASE_ERROR = "SYSTEM_001"
    EXTERNAL_SERVICE_ERROR = "SYSTEM_002"
    INTERNAL_SERVER_ERROR = "SYSTEM_003"
    RATE_LIMIT_EXCEEDED = "SYSTEM_004"
    
    # 驗證錯誤
    VALIDATION_ERROR = "VALIDATION_001"
    MISSING_REQUIRED_FIELD = "VALIDATION_002"
    INVALID_INPUT_FORMAT = "VALIDATION_003"

class ErrorResponse(BaseModel):
    """統一的錯誤響應格式"""
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime
    request_id: Optional[str] = None
    suggestions: Optional[List[str]] = None

class APIError(Exception):
    """自定義API錯誤基類"""
    
    def __init__(
        self, 
        error_code: str, 
        message: str, 
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[str]] = None
    ):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        self.suggestions = suggestions or []
        super().__init__(message)

class AuthenticationError(APIError):
    """認證錯誤"""
    def __init__(self, message: str = "Authentication failed", details: Optional[Dict] = None):
        super().__init__(
            error_code=ErrorCodes.AUTHENTICATION_FAILED,
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
            suggestions=["請重新登入", "檢查您的憑證是否有效"]
        )

class AuthorizationError(APIError):
    """授權錯誤"""
    def __init__(self, message: str = "Access denied", details: Optional[Dict] = None):
        super().__init__(
            error_code=ErrorCodes.AUTHORIZATION_FAILED,
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
            suggestions=["請確認您有相應的權限", "聯繫管理員獲取授權"]
        )

class ResourceNotFoundError(APIError):
    """資源不存在錯誤"""
    def __init__(self, resource_type: str, resource_id: str = "", details: Optional[Dict] = None):
        message = f"{resource_type} not found"
        if resource_id:
            message += f": {resource_id}"
        
        super().__init__(
            error_code=ErrorCodes.RESOURCE_NOT_FOUND,
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
            suggestions=["檢查資源ID是否正確", "確認資源是否存在"]
        )

class ValidationError(APIError):
    """驗證錯誤"""
    def __init__(self, message: str, field: str = "", details: Optional[Dict] = None):
        super().__init__(
            error_code=ErrorCodes.VALIDATION_ERROR,
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details or {"field": field},
            suggestions=["檢查輸入格式", "參考API文檔中的要求"]
        )

class FileProcessingError(APIError):
    """檔案處理錯誤"""
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            error_code=ErrorCodes.FILE_PROCESSING_FAILED,
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
            suggestions=["檢查檔案格式", "嘗試重新上傳檔案", "確認檔案未損壞"]
        )

class DatabaseError(APIError):
    """資料庫錯誤"""
    def __init__(self, message: str = "Database operation failed", details: Optional[Dict] = None):
        super().__init__(
            error_code=ErrorCodes.DATABASE_ERROR,
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details,
            suggestions=["請稍後重試", "如果問題持續，請聯繫技術支援"]
        )

# 重試裝飾器
def retry_on_failure(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    重試裝飾器，用於暫時性錯誤的自動重試
    
    Args:
        max_retries: 最大重試次數
        delay: 初始延遲時間（秒）
        backoff: 退避係數
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except (DatabaseError, APIError) as e:
                    last_exception = e
                    
                    # 如果是最後一次嘗試，直接拋出異常
                    if attempt == max_retries:
                        break
                    
                    # 只對特定錯誤進行重試
                    if e.status_code >= 500:  # 服務器錯誤才重試
                        logger.warning(f"Attempt {attempt + 1} failed, retrying in {current_delay}s: {e}")
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        # 客戶端錯誤不重試
                        break
                except Exception as e:
                    last_exception = APIError(
                        error_code=ErrorCodes.INTERNAL_SERVER_ERROR,
                        message="Internal server error",
                        status_code=500,
                        details={"original_error": str(e)}
                    )
                    break
            
            raise last_exception
        
        return wrapper
    return decorator

# Circuit Breaker（斷路器）實現
class CircuitBreaker:
    """
    簡單的斷路器實現，防止級聯失敗
    """
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def can_execute(self) -> bool:
        """檢查是否可以執行操作"""
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        else:  # HALF_OPEN
            return True
    
    def record_success(self):
        """記錄成功操作"""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def record_failure(self):
        """記錄失敗操作"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"

# 全域斷路器實例
database_circuit_breaker = CircuitBreaker()
external_api_circuit_breaker = CircuitBreaker()

def with_circuit_breaker(circuit_breaker: CircuitBreaker):
    """
    斷路器裝飾器
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not circuit_breaker.can_execute():
                raise APIError(
                    error_code=ErrorCodes.EXTERNAL_SERVICE_ERROR,
                    message="Service temporarily unavailable",
                    status_code=503,
                    suggestions=["請稍後重試", "服務正在恢復中"]
                )
            
            try:
                result = await func(*args, **kwargs)
                circuit_breaker.record_success()
                return result
            except Exception as e:
                circuit_breaker.record_failure()
                raise
        
        return wrapper
    return decorator

# 錯誤處理器
async def create_error_response(
    request: Request,
    error: Union[APIError, HTTPException, Exception],
    request_id: Optional[str] = None
) -> JSONResponse:
    """
    創建統一的錯誤響應
    
    Args:
        request: FastAPI請求對象
        error: 錯誤對象
        request_id: 請求ID
    
    Returns:
        JSON錯誤響應
    """
    
    if isinstance(error, APIError):
        error_response = ErrorResponse(
            error_code=error.error_code,
            message=error.message,
            details=error.details,
            timestamp=datetime.utcnow(),
            request_id=request_id,
            suggestions=error.suggestions
        )
        status_code = error.status_code
        
    elif isinstance(error, HTTPException):
        # 將FastAPI的HTTPException轉換為我們的格式
        error_code = _map_http_status_to_error_code(error.status_code)
        error_response = ErrorResponse(
            error_code=error_code,
            message=error.detail,
            details={},
            timestamp=datetime.utcnow(),
            request_id=request_id
        )
        status_code = error.status_code
        
    else:
        # 未預期的錯誤
        logger.error(f"Unexpected error: {error}", exc_info=True)
        error_response = ErrorResponse(
            error_code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message="Internal server error",
            details={"error_type": type(error).__name__} if logger.level == "DEBUG" else {},
            timestamp=datetime.utcnow(),
            request_id=request_id,
            suggestions=["請稍後重試", "如果問題持續，請聯繫技術支援"]
        )
        status_code = 500
    
    # 記錄錯誤
    logger.error(
        "API Error",
        error_code=error_response.error_code,
        message=error_response.message,
        status_code=status_code,
        path=request.url.path,
        method=request.method,
        request_id=request_id
    )
    
    return JSONResponse(
        status_code=status_code,
        content=error_response.dict()
    )

def _map_http_status_to_error_code(status_code: int) -> str:
    """
    將HTTP狀態碼映射到錯誤代碼
    """
    mapping = {
        400: ErrorCodes.VALIDATION_ERROR,
        401: ErrorCodes.AUTHENTICATION_FAILED,
        403: ErrorCodes.AUTHORIZATION_FAILED,
        404: ErrorCodes.RESOURCE_NOT_FOUND,
        409: ErrorCodes.RESOURCE_CONFLICT,
        422: ErrorCodes.VALIDATION_ERROR,
        429: ErrorCodes.RATE_LIMIT_EXCEEDED,
        500: ErrorCodes.INTERNAL_SERVER_ERROR,
        503: ErrorCodes.EXTERNAL_SERVICE_ERROR
    }
    return mapping.get(status_code, ErrorCodes.INTERNAL_SERVER_ERROR)

# 健康檢查相關函數
async def check_database_health() -> Dict[str, Any]:
    """檢查資料庫健康狀態"""
    try:
        from .database import async_engine
        from sqlalchemy import text
        
        async with async_engine.begin() as conn:
            start_time = time.time()
            await conn.execute(text("SELECT 1"))
            response_time = time.time() - start_time
            
        return {
            "status": "healthy",
            "response_time_ms": round(response_time * 1000, 2)
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

async def check_external_services_health() -> Dict[str, Any]:
    """檢查外部服務健康狀態"""
    from ..core.config import settings
    import httpx
    
    services = {
        "grobid": settings.grobid_url,
        "n8n": settings.n8n_base_url,
        "split_sentences": settings.split_sentences_url
    }
    
    results = {}
    
    for service_name, url in services.items():
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                start_time = time.time()
                response = await client.get(f"{url}/health", timeout=5.0)
                response_time = time.time() - start_time
                
                results[service_name] = {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "response_time_ms": round(response_time * 1000, 2),
                    "status_code": response.status_code
                }
        except Exception as e:
            results[service_name] = {
                "status": "unhealthy",
                "error": str(e)
            }
    
    return results 