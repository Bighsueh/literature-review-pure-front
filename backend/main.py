"""
論文分析系統FastAPI主應用程式
"""

import time
import uuid
from contextlib import asynccontextmanager
from typing import Dict, Any
import json

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette import status

# 導入核心模組
from .core.config import settings, print_settings
from .core.logging import (
    setup_logging, 
    get_logger, 
    request_logger, 
    log_startup, 
    log_shutdown
)
from .core.exceptions import (
    BaseAPIException,
    ValidationException,
    DatabaseException,
    FileProcessingException,
    ExternalAPIException,
    InternalServerException,
    error_handler,
    HTTPExceptionHandler
)
from .core.database import init_database, close_database

# 導入API路由
from .api.upload import router as files_router
from .api.papers import router as papers_router
from .api.processing import router as processing_router
from .api.health import router as health_router
from .api.debug import router as debug_router
from .api.auth import router as auth_router
from .api.workspaces import router as workspaces_router
from .api.legacy import router as legacy_router
from .api.chats import router as chats_router
from .api.workspace_files import router as workspace_files_router
from .api.workspace_query import router as workspace_query_router


# 設置日誌
setup_logging()
logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用程式生命週期管理"""
    
    # 啟動事件
    try:
        log_startup()
        print_settings()
        
        # 初始化資料庫
        await init_database()
        logger.info("資料庫初始化完成")
        
        # 執行自動遷移檢查和執行
        from .simplified_migration import ensure_database_schema
        schema_ok = await ensure_database_schema()
        if schema_ok:
            logger.info("資料庫結構檢查完成")
        else:
            logger.warning("資料庫結構檢查發現問題，但系統將繼續運行")
        
        # 建立temp_files目錄
        import os
        os.makedirs(settings.temp_files_dir, exist_ok=True)
        logger.info(f"暫存檔案目錄已準備: {settings.temp_files_dir}")
        
        # 初始化處理服務 (會自動註冊任務處理器)
        from .services.processing_service import ProcessingService
        processing_service = ProcessingService()
        logger.info("檔案處理服務已初始化")
        
        # 啟動佇列處理服務
        from .services.queue_service import queue_service
        await queue_service.start_workers()
        logger.info("佇列處理服務已啟動")
        
        yield
        
    except Exception as e:
        logger.error(f"應用程式啟動失敗: {e}")
        raise
    
    finally:
        # 關閉事件
        try:
            # 停止佇列處理服務
            from .services.queue_service import queue_service
            await queue_service.stop_workers()
            logger.info("佇列處理服務已停止")
            
            await close_database()
            log_shutdown()
        except Exception as e:
            logger.error(f"應用程式關閉時發生錯誤: {e}")


# 建立FastAPI應用程式
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="基於AI的學術論文深度分析與比較系統",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)


# CORS中間件設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        # 開發環境
        "http://localhost:5173",
        "http://localhost:3000", 
        "http://127.0.0.1:5173",
        # Docker 容器環境
        "http://localhost:20080",
        "http://127.0.0.1:20080",
        # 生產環境
        "https://chat.hsueh.tw",
        "https://backend.hsueh.tw",
        # 動態設定（從環境變數）
        settings.frontend_url if hasattr(settings, 'frontend_url') else "http://localhost:5173"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type", 
        "X-Requested-With",
        "X-Request-ID"
    ],
    expose_headers=["X-Request-ID", "X-Process-Time"],
)


# 請求日誌中間件
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """請求日誌中間件"""
    
    # 生成請求ID
    request_id = str(uuid.uuid4())
    
    # 記錄請求
    start_time = time.time()
    
    request_logger.log_request(
        method=request.method,
        path=request.url.path,
        client_ip=request.client.host if request.client else "unknown",
        user_agent=request.headers.get("user-agent"),
        request_id=request_id
    )
    
    # 處理請求
    response = await call_next(request)
    
    # 記錄回應
    process_time = time.time() - start_time
    
    request_logger.log_response(
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        response_time=process_time,
        request_id=request_id
    )
    
    # 添加回應標頭
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = str(round(process_time * 1000, 2))
    
    return response


# 全域例外處理器
@app.exception_handler(BaseAPIException)
async def api_exception_handler(request: Request, exc: BaseAPIException):
    """API例外處理器"""
    error_handler.log_error(exc, {
        "path": request.url.path,
        "method": request.method,
        "client_ip": request.client.host if request.client else "unknown"
    })
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": str(exc.detail),
            "error_code": exc.error_type,
            "details": exc.details
        }
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """HTTP例外處理器"""
    logger.warning(
        "HTTP例外",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": str(exc.detail),
            "error_code": "HTTP_ERROR",
            "details": {}
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """請求驗證錯誤處理器"""
    logger.warning(
        "請求驗證錯誤",
        errors=exc.errors(),
        path=request.url.path
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "請求資料驗證失敗",
            "error_code": "VALIDATION_ERROR",
            "details": {"validation_errors": exc.errors()}
        }
    )


# 添加 JSON 解析錯誤處理器
@app.middleware("http")
async def json_parsing_middleware(request: Request, call_next):
    """簡化的 JSON 解析錯誤中間件"""
    content_type = request.headers.get("content-type", "")
    
    # 如果是檔案上傳請求，則跳過 JSON 解析
    if "multipart/form-data" in content_type:
        return await call_next(request)
    
    # 對於其他請求，直接處理，讓 FastAPI 自己處理 JSON 解析
    return await call_next(request)


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """通用例外處理器"""
    logger.error(f"未處理的例外: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "內部伺服器錯誤", "error_code": "UNEXPECTED_ERROR"}
    )


# 包含API路由
app.include_router(auth_router, tags=["authentication"])
app.include_router(workspaces_router, tags=["workspaces"])
app.include_router(chats_router, tags=["chats"])
app.include_router(legacy_router, prefix="/api", tags=["legacy-data"])
app.include_router(files_router, prefix="/api", tags=["upload"])
app.include_router(papers_router, prefix="/api", tags=["papers"])
app.include_router(processing_router, prefix="/api", tags=["processing"])
app.include_router(health_router, tags=["健康檢查"])
app.include_router(debug_router, prefix="/api", tags=["debug"])
app.include_router(workspace_files_router, tags=["workspace-files"])
app.include_router(workspace_query_router, tags=["workspace-query"])


@app.get("/")
async def root():
    """根端點，顯示應用程式資訊"""
    return {
        "success": True,
        "message": "論文分析系統API",
        "version": settings.app_version,
        "environment": settings.environment,
        "docs": "/docs" if settings.debug else "文檔在生產環境中不可用"
    }


@app.get("/health")
async def health_check():
    """健康檢查"""
    return {
        "success": True,
        "status": "healthy",
        "timestamp": time.time(),
        "version": settings.app_version
    }


@app.get("/api/info")
async def api_info():
    """API資訊"""
    return {
        "success": True,
        "data": {
            "app_name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "features": {
                "grobid_integration": True,
                "n8n_integration": True,
                "postgresql_database": True,
                "batch_processing": True,
                "file_deduplication": True,
                "multi_paper_analysis": True
            },
            "limits": {
                "max_file_size_mb": settings.max_file_size_mb,
                "batch_processing_size": settings.batch_processing_size,
                "max_retries": settings.max_retries
            }
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    # 開發模式運行
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    ) 