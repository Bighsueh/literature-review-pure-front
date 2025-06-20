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
from .error_handling import (
    APIError,
    AuthenticationError,
    AuthorizationError,
    ResourceNotFoundError,
    ValidationError,
    FileProcessingError,
    DatabaseError,
    ErrorCodes,
    ErrorResponse,
    create_error_response,
    retry_on_failure,
    with_circuit_breaker,
    database_circuit_breaker,
    external_api_circuit_breaker
)

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

# 重新導出以保持向後兼容
BaseAPIException = APIError

# 保持現有的異常類以支持遺留代碼
class BaseAPIException(APIError):
    """基礎API異常類 - 向後兼容"""
    def __init__(self, detail: str, status_code: int = 500, error_type: str = None):
        super().__init__(
            error_code=error_type or ErrorCodes.INTERNAL_SERVER_ERROR,
            message=detail,
            status_code=status_code
        )
        self.detail = detail
        self.error_type = error_type

class ValidationException(ValidationError):
    """驗證異常 - 向後兼容"""
    pass

class DatabaseException(DatabaseError):
    """數據庫異常 - 向後兼容"""
    pass

class FileProcessingException(FileProcessingError):
    """檔案處理異常 - 向後兼容"""
    pass

class ExternalAPIException(APIError):
    """外部API異常"""
    def __init__(self, message: str = "External API error", details=None):
        super().__init__(
            error_code=ErrorCodes.EXTERNAL_SERVICE_ERROR,
            message=message,
            status_code=503,
            details=details
        )

class InternalServerException(APIError):
    """內部伺服器異常"""
    def __init__(self, message: str = "Internal server error", details=None):
        super().__init__(
            error_code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message=message,
            status_code=500,
            details=details
        )

# 新增查詢處理相關的異常類別
class QueryProcessingError(APIError):
    """查詢處理異常"""
    def __init__(self, message: str = "Query processing failed", details=None):
        super().__init__(
            error_code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message=message,
            status_code=500,
            details=details
        )

class DataValidationError(ValidationError):
    """資料驗證異常"""
    def __init__(self, message: str = "Data validation failed", field: str = "", details=None):
        super().__init__(message, field, details)

# 錯誤處理器
class ErrorHandler:
    """錯誤處理器類 - 向後兼容"""
    @staticmethod
    def log_error(error, context=None):
        from .logging import get_logger
        logger = get_logger("error_handler")
        logger.error(f"Error: {error}", extra=context or {})

class HTTPExceptionHandler:
    """HTTP異常處理器 - 向後兼容"""
    pass

# 實例化錯誤處理器
error_handler = ErrorHandler()

# 便利函數以保持向後兼容
def handle_validation_error(message: str, field: str = ""):
    """處理驗證錯誤"""
    return ValidationError(message, field)

def handle_not_found_error(message: str):
    """處理資源不存在錯誤"""
    return ResourceNotFoundError("Resource", message)

def handle_internal_error(message: str):
    """處理內部錯誤"""
    return InternalServerException(message)

# 導出所有需要的符號
__all__ = [
    "APIError",
    "AuthenticationError", 
    "AuthorizationError",
    "ResourceNotFoundError",
    "ValidationError",
    "FileProcessingError",
    "DatabaseError",
    "ExternalAPIException",
    "InternalServerException",
    "QueryProcessingError",
    "DataValidationError",
    "BaseAPIException",
    "ValidationException",
    "DatabaseException", 
    "FileProcessingException",
    "ErrorCodes",
    "ErrorResponse",
    "create_error_response",
    "retry_on_failure",
    "with_circuit_breaker",
    "database_circuit_breaker",
    "external_api_circuit_breaker",
    "error_handler",
    "HTTPExceptionHandler",
    "handle_validation_error",
    "handle_not_found_error",
    "handle_internal_error"
]

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