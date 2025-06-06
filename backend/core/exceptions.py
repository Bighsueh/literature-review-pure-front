"""
自定義例外類別和錯誤處理系統
"""

from typing import Any, Dict, Optional
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from enum import Enum
import logging
import traceback
from datetime import datetime

logger = logging.getLogger(__name__)

class ErrorType(Enum):
    """錯誤類型枚舉"""
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    RATE_LIMIT = "rate_limit"
    EXTERNAL_API = "external_api"
    DATABASE = "database"
    FILE_PROCESSING = "file_processing"
    INTERNAL_SERVER = "internal_server"

class ErrorSeverity(Enum):
    """錯誤嚴重程度枚舉"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class BaseAPIException(HTTPException):
    """基礎 API 異常類別"""
    
    def __init__(
        self,
        status_code: int,
        message: str,
        error_type: ErrorType = ErrorType.INTERNAL_SERVER,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: Optional[Dict[str, Any]] = None,
        retryable: bool = False
    ):
        self.error_type = error_type
        self.severity = severity
        self.retryable = retryable
        self.timestamp = datetime.utcnow()
        self.details = details or {}
        
        super().__init__(
            status_code=status_code,
            detail={
                "message": message,
                "error_type": error_type.value,
                "severity": severity.value,
                "retryable": retryable,
                "timestamp": self.timestamp.isoformat(),
                "details": self.details
            }
        )

class ValidationException(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class AuthenticationException(BaseAPIException):
    """身份驗證錯誤"""
    
    def __init__(self, message: str = "身份驗證失敗"):
        super().__init__(
            status_code=401,
            message=message,
            error_type=ErrorType.AUTHENTICATION,
            severity=ErrorSeverity.HIGH,
            retryable=False
        )

class AuthorizationException(BaseAPIException):
    """授權錯誤"""
    
    def __init__(self, message: str = "沒有權限執行此操作"):
        super().__init__(
            status_code=403,
            message=message,
            error_type=ErrorType.AUTHORIZATION,
            severity=ErrorSeverity.HIGH,
            retryable=False
        )

class NotFoundException(BaseAPIException):
    """資源未找到錯誤"""
    
    def __init__(self, message: str, resource_type: Optional[str] = None):
        details = {}
        if resource_type:
            details["resource_type"] = resource_type
            
        super().__init__(
            status_code=404,
            message=message,
            error_type=ErrorType.NOT_FOUND,
            severity=ErrorSeverity.LOW,
            details=details,
            retryable=False
        )

class ConflictException(BaseAPIException):
    """衝突錯誤"""
    
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            status_code=409,
            message=message,
            error_type=ErrorType.CONFLICT,
            severity=ErrorSeverity.MEDIUM,
            details=details,
            retryable=False
        )

class RateLimitException(BaseAPIException):
    """速率限制錯誤"""
    
    def __init__(self, message: str = "請求過於頻繁，請稍後重試"):
        super().__init__(
            status_code=429,
            message=message,
            error_type=ErrorType.RATE_LIMIT,
            severity=ErrorSeverity.MEDIUM,
            retryable=True
        )

class ExternalAPIException(BaseAPIException):
    """外部 API 錯誤"""
    
    def __init__(self, message: str, service_name: Optional[str] = None, details: Optional[Dict] = None):
        error_details = details or {}
        if service_name:
            error_details["service"] = service_name
            
        super().__init__(
            status_code=502,
            message=message,
            error_type=ErrorType.EXTERNAL_API,
            severity=ErrorSeverity.HIGH,
            details=error_details,
            retryable=True
        )

class DatabaseException(BaseAPIException):
    """資料庫錯誤"""
    
    def __init__(self, message: str = "資料庫操作失敗", details: Optional[Dict] = None):
        super().__init__(
            status_code=500,
            message=message,
            error_type=ErrorType.DATABASE,
            severity=ErrorSeverity.CRITICAL,
            details=details,
            retryable=True
        )

class FileProcessingException(BaseAPIException):
    """檔案處理錯誤"""
    
    def __init__(self, message: str, file_name: Optional[str] = None, details: Optional[Dict] = None):
        error_details = details or {}
        if file_name:
            error_details["file_name"] = file_name
            
        super().__init__(
            status_code=422,
            message=message,
            error_type=ErrorType.FILE_PROCESSING,
            severity=ErrorSeverity.MEDIUM,
            details=error_details,
            retryable=True
        )

class InternalServerException(BaseAPIException):
    """內部伺服器錯誤"""
    
    def __init__(self, message: str = "內部伺服器錯誤", details: Optional[Dict] = None):
        super().__init__(
            status_code=500,
            message=message,
            error_type=ErrorType.INTERNAL_SERVER,
            severity=ErrorSeverity.CRITICAL,
            details=details,
            retryable=False
        )

class QueryProcessingError(BaseAPIException):
    """查詢處理錯誤"""
    
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            status_code=422,
            message=message,
            error_type=ErrorType.FILE_PROCESSING,
            severity=ErrorSeverity.MEDIUM,
            details=details,
            retryable=True
        )

class DataValidationError(BaseAPIException):
    """資料驗證錯誤"""
    
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            status_code=400,
            message=message,
            error_type=ErrorType.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            details=details,
            retryable=False
        )

class ErrorHandler:
    """錯誤處理器"""
    
    @staticmethod
    def log_error(exception: Exception, context: Optional[Dict[str, Any]] = None):
        """記錄錯誤"""
        error_info = {
            "error_type": type(exception).__name__,
            "message": str(exception),
            "traceback": traceback.format_exc(),
            "context": context or {}
        }
        
        if isinstance(exception, BaseAPIException):
            error_info.update({
                "api_error_type": exception.error_type.value,
                "severity": exception.severity.value,
                "retryable": exception.retryable,
                "details": exception.details
            })
            
            # 根據嚴重程度選擇日誌級別
            if exception.severity == ErrorSeverity.CRITICAL:
                logger.critical("Critical error occurred", extra=error_info)
            elif exception.severity == ErrorSeverity.HIGH:
                logger.error("High severity error occurred", extra=error_info)
            elif exception.severity == ErrorSeverity.MEDIUM:
                logger.warning("Medium severity error occurred", extra=error_info)
            else:
                logger.info("Low severity error occurred", extra=error_info)
        else:
            logger.error("Unhandled exception occurred", extra=error_info)
    
    @staticmethod
    def format_error_response(exception: Exception) -> Dict[str, Any]:
        """格式化錯誤回應"""
        if isinstance(exception, BaseAPIException):
            return exception.detail
        
        # 對於未處理的異常，返回通用錯誤訊息
        return {
            "message": "內部伺服器錯誤",
            "error_type": ErrorType.INTERNAL_SERVER.value,
            "severity": ErrorSeverity.CRITICAL.value,
            "retryable": False,
            "timestamp": datetime.utcnow().isoformat(),
            "details": {}
        }

# 錯誤處理器實例
error_handler = ErrorHandler()

# HTTP例外處理器
class HTTPExceptionHandler:
    """HTTP例外處理器"""
    
    @staticmethod
    def create_error_response(
        status_code: int,
        message: str,
        error_code: str = "HTTP_ERROR",
        details: Optional[Dict[str, Any]] = None
    ) -> JSONResponse:
        """建立錯誤回應"""
        
        content = {
            "success": False,
            "error": {
                "message": message,
                "error_code": error_code,
                "details": details or {}
            }
        }
        
        return JSONResponse(
            status_code=status_code,
            content=content
        )
    
    @staticmethod
    def bad_request(message: str, details: Optional[Dict[str, Any]] = None) -> JSONResponse:
        """400 錯誤請求"""
        return HTTPExceptionHandler.create_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=message,
            error_code="BAD_REQUEST",
            details=details
        )
    
    @staticmethod
    def unauthorized(message: str = "未授權存取") -> JSONResponse:
        """401 未授權"""
        return HTTPExceptionHandler.create_error_response(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message=message,
            error_code="UNAUTHORIZED"
        )
    
    @staticmethod
    def forbidden(message: str = "禁止存取") -> JSONResponse:
        """403 禁止存取"""
        return HTTPExceptionHandler.create_error_response(
            status_code=status.HTTP_403_FORBIDDEN,
            message=message,
            error_code="FORBIDDEN"
        )
    
    @staticmethod
    def not_found(message: str = "資源不存在") -> JSONResponse:
        """404 找不到資源"""
        return HTTPExceptionHandler.create_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message=message,
            error_code="NOT_FOUND"
        )
    
    @staticmethod
    def unprocessable_entity(message: str, details: Optional[Dict[str, Any]] = None) -> JSONResponse:
        """422 無法處理的實體"""
        return HTTPExceptionHandler.create_error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message=message,
            error_code="UNPROCESSABLE_ENTITY",
            details=details
        )
    
    @staticmethod
    def internal_server_error(message: str = "內部服務器錯誤") -> JSONResponse:
        """500 內部服務器錯誤"""
        return HTTPExceptionHandler.create_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=message,
            error_code="INTERNAL_SERVER_ERROR"
        )
    
    @staticmethod
    def service_unavailable(message: str = "服務暫時無法使用") -> JSONResponse:
        """503 服務不可用"""
        return HTTPExceptionHandler.create_error_response(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message=message,
            error_code="SERVICE_UNAVAILABLE"
        )


# 例外映射
def map_exception_to_http_response(exc: Exception) -> JSONResponse:
    """將自定義例外映射到HTTP回應"""
    
    if isinstance(exc, ValidationException):
        return HTTPExceptionHandler.unprocessable_entity(
            message=exc.message,
            details=exc.details
        )
    
    elif isinstance(exc, DatabaseException):
        return HTTPExceptionHandler.internal_server_error(
            message="資料庫操作失敗"
        )
    
    elif isinstance(exc, FileProcessingException):
        return HTTPExceptionHandler.bad_request(
            message=exc.message,
            details=exc.details
        )
    
    elif isinstance(exc, (ExternalAPIException)):
        return HTTPExceptionHandler.service_unavailable(
            message=exc.message
        )
    
    elif isinstance(exc, InternalServerException):
        return HTTPExceptionHandler.internal_server_error(
            message=exc.message
        )
    
    else:
        # 未預期的例外
        return HTTPExceptionHandler.internal_server_error(
            message="系統發生未預期的錯誤"
        )


# 常用的HTTPException快捷方式
def raise_bad_request(message: str, details: Optional[Dict[str, Any]] = None):
    """拋出400錯誤"""
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={
            "message": message,
            "error_code": "BAD_REQUEST",
            "details": details or {}
        }
    )


def raise_not_found(message: str = "資源不存在"):
    """拋出404錯誤"""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "message": message,
            "error_code": "NOT_FOUND"
        }
    )


def raise_unprocessable_entity(message: str, details: Optional[Dict[str, Any]] = None):
    """拋出422錯誤"""
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={
            "message": message,
            "error_code": "UNPROCESSABLE_ENTITY", 
            "details": details or {}
        }
    )


def raise_internal_server_error(message: str = "內部服務器錯誤"):
    """拋出500錯誤"""
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={
            "message": message,
            "error_code": "INTERNAL_SERVER_ERROR"
        }
    )

def format_error_response(message: str, error_code: str = None, details: Optional[Dict[str, Any]] = None) -> dict:
    """格式化錯誤回應"""
    return {
        "detail": message,
        "error_code": error_code or "UNKNOWN_ERROR",
        "details": details or {}
    }

def handle_validation_error(exc: ValidationException) -> HTTPException:
    """處理驗證錯誤"""
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=format_error_response(
            message=str(exc),
            error_code="VALIDATION_ERROR"
        )
    )

def handle_not_found_error(message: str) -> HTTPException:
    """處理找不到資源錯誤"""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=format_error_response(
            message=message,
            error_code="NOT_FOUND"
        )
    )

def handle_internal_error(message: str, error_code: str = None) -> HTTPException:
    """處理內部錯誤"""
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=format_error_response(
            message=message,
            error_code=error_code or "INTERNAL_ERROR"
        )
    ) 