"""
結構化日誌系統
使用structlog提供結構化,高效能的日誌記錄
"""

import sys
import logging
import structlog
from typing import Any, Dict
from datetime import datetime

from .config import settings


def setup_logging():
    """設置結構化日誌"""
    
    # 設置基本日誌等級
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    
    # 配置structlog
    structlog.configure(
        processors=[
            # 添加時間戳
            structlog.processors.TimeStamper(fmt="ISO"),
            # 添加日誌等級
            structlog.processors.add_log_level,
            # 添加程序名稱
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            # JSON格式化（生產環境）或美化輸出（開發環境）
            structlog.processors.JSONRenderer() if not settings.debug 
            else structlog.dev.ConsoleRenderer(colors=True)
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # 配置標準庫日誌
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )
    
    # 設置第三方套件的日誌等級
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.debug else logging.WARNING
    )
    logging.getLogger("asyncpg").setLevel(logging.WARNING)


def get_logger(name: str = None) -> structlog.stdlib.BoundLogger:
    """取得結構化日誌記錄器"""
    return structlog.get_logger(name)


class RequestLogger:
    """請求日誌記錄器"""
    
    def __init__(self):
        self.logger = get_logger("request")
    
    def log_request(
        self,
        method: str,
        path: str,
        client_ip: str,
        user_agent: str = None,
        request_id: str = None
    ):
        """記錄請求資訊"""
        self.logger.info(
            "HTTP請求",
            method=method,
            path=path,
            client_ip=client_ip,
            user_agent=user_agent,
            request_id=request_id
        )
    
    def log_response(
        self,
        method: str,
        path: str,
        status_code: int,
        response_time: float,
        request_id: str = None
    ):
        """記錄回應資訊"""
        self.logger.info(
            "HTTP回應",
            method=method,
            path=path,
            status_code=status_code,
            response_time_ms=round(response_time * 1000, 2),
            request_id=request_id
        )


class DatabaseLogger:
    """資料庫操作日誌記錄器"""
    
    def __init__(self):
        self.logger = get_logger("database")
    
    def log_query(self, operation: str, table: str, duration: float = None):
        """記錄資料庫查詢"""
        self.logger.debug(
            "資料庫查詢",
            operation=operation,
            table=table,
            duration_ms=round(duration * 1000, 2) if duration else None
        )
    
    def log_error(self, operation: str, error: str, table: str = None):
        """記錄資料庫錯誤"""
        self.logger.error(
            "資料庫錯誤",
            operation=operation,
            table=table,
            error=error
        )


class ProcessingLogger:
    """處理流程日誌記錄器"""
    
    def __init__(self):
        self.logger = get_logger("processing")
    
    def log_start(self, process: str, paper_id: str = None, **kwargs):
        """記錄處理開始"""
        self.logger.info(
            "處理開始",
            process=process,
            paper_id=paper_id,
            **kwargs
        )
    
    def log_progress(self, process: str, progress: float, paper_id: str = None, **kwargs):
        """記錄處理進度"""
        self.logger.info(
            "處理進度",
            process=process,
            progress_percent=round(progress, 2),
            paper_id=paper_id,
            **kwargs
        )
    
    def log_complete(self, process: str, duration: float = None, paper_id: str = None, **kwargs):
        """記錄處理完成"""
        self.logger.info(
            "處理完成",
            process=process,
            duration_seconds=round(duration, 2) if duration else None,
            paper_id=paper_id,
            **kwargs
        )
    
    def log_error(self, process: str, error: str, paper_id: str = None, **kwargs):
        """記錄處理錯誤"""
        self.logger.error(
            "處理錯誤",
            process=process,
            error=error,
            paper_id=paper_id,
            **kwargs
        )


class ExternalAPILogger:
    """外部API呼叫日誌記錄器"""
    
    def __init__(self):
        self.logger = get_logger("external_api")
    
    def log_request(self, service: str, endpoint: str, method: str = "POST"):
        """記錄外部API請求"""
        self.logger.debug(
            "外部API請求",
            service=service,
            endpoint=endpoint,
            method=method
        )
    
    def log_response(self, service: str, endpoint: str, status_code: int, duration: float):
        """記錄外部API回應"""
        self.logger.info(
            "外部API回應",
            service=service,
            endpoint=endpoint,
            status_code=status_code,
            duration_ms=round(duration * 1000, 2)
        )
    
    def log_error(self, service: str, endpoint: str, error: str):
        """記錄外部API錯誤"""
        self.logger.error(
            "外部API錯誤",
            service=service,
            endpoint=endpoint,
            error=error
        )


# 全域日誌記錄器實例
request_logger = RequestLogger()
db_logger = DatabaseLogger()
processing_logger = ProcessingLogger()
api_logger = ExternalAPILogger()

# 一般用途日誌記錄器
logger = get_logger("app")


def log_startup():
    """記錄應用程式啟動資訊"""
    logger.info(
        "應用程式啟動",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        debug=settings.debug
    )


def log_shutdown():
    """記錄應用程式關閉資訊"""
    logger.info("應用程式關閉")


if __name__ == "__main__":
    # 測試日誌系統
    setup_logging()
    
    test_logger = get_logger("test")
    test_logger.info("測試訊息", key1="value1", key2=123)
    test_logger.warning("警告訊息", warning_type="test")
    test_logger.error("錯誤訊息", error_code=500) 