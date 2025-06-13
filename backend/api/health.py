"""
系統健康檢查和監控端點
提供詳細的系統狀態和資料庫連接資訊
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, Any, List
import os
import psutil

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.connection import db_manager
from ..database.migration_manager import migration_manager
from ..core.logging import get_logger
from ..core.config import get_settings

logger = get_logger(__name__)
router = APIRouter(prefix="/api/health", tags=["健康檢查"])

@router.get("/")
async def basic_health_check():
    """基本健康檢查"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "Paper Analysis API"
    }

@router.get("/detailed")
async def detailed_health_check():
    """詳細健康檢查"""
    
    health_data = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "Paper Analysis API",
        "version": "1.0.0",
        "checks": {}
    }
    
    overall_healthy = True
    
    # 1. 資料庫連接檢查
    try:
        start_time = time.time()
        async with db_manager.get_async_session() as session:
            await session.execute(text("SELECT 1"))
        
        db_response_time = (time.time() - start_time) * 1000
        
        health_data["checks"]["database"] = {
            "status": "healthy",
            "response_time_ms": round(db_response_time, 2),
            "message": "資料庫連接正常"
        }
    except Exception as e:
        overall_healthy = False
        health_data["checks"]["database"] = {
            "status": "unhealthy",
            "error": str(e),
            "message": "資料庫連接失敗"
        }
    
    # 2. 遷移狀態檢查
    try:
        migration_status = await migration_manager.get_migration_status()
        
        health_data["checks"]["migrations"] = {
            "status": "healthy" if migration_status["status"] == "up_to_date" else "warning",
            "current_version": migration_status["current_version"],
            "pending_count": migration_status["pending_count"],
            "total_migrations": migration_status["total_migrations"],
            "message": "遷移狀態正常" if migration_status["status"] == "up_to_date" else f"有 {migration_status['pending_count']} 個待應用的遷移"
        }
        
        if migration_status["status"] != "up_to_date":
            overall_healthy = False
            
    except Exception as e:
        overall_healthy = False
        health_data["checks"]["migrations"] = {
            "status": "unhealthy",
            "error": str(e),
            "message": "遷移狀態檢查失敗"
        }
    
    # 3. 系統資源檢查
    try:
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        health_data["checks"]["system_resources"] = {
            "status": "healthy",
            "memory": {
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "percent_used": memory.percent
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "percent_used": round((disk.used / disk.total) * 100, 2)
            },
            "message": "系統資源正常"
        }
        
        # 警告閾值檢查
        if memory.percent > 85 or disk.percent > 85:
            health_data["checks"]["system_resources"]["status"] = "warning"
            health_data["checks"]["system_resources"]["message"] = "系統資源使用率較高"
            
    except Exception as e:
        health_data["checks"]["system_resources"] = {
            "status": "error",
            "error": str(e),
            "message": "系統資源檢查失敗"
        }
    
    # 4. 檔案系統檢查
    try:
        settings = get_settings()
        temp_dir = settings.temp_files_dir
        
        # 檢查暫存目錄是否存在且可寫
        if os.path.exists(temp_dir) and os.access(temp_dir, os.W_OK):
            # 計算暫存目錄大小
            total_size = 0
            file_count = 0
            for dirpath, dirnames, filenames in os.walk(temp_dir):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)
                        file_count += 1
            
            health_data["checks"]["file_system"] = {
                "status": "healthy",
                "temp_dir": temp_dir,
                "temp_files_count": file_count,
                "temp_files_size_mb": round(total_size / (1024**2), 2),
                "message": "檔案系統正常"
            }
        else:
            overall_healthy = False
            health_data["checks"]["file_system"] = {
                "status": "unhealthy",
                "temp_dir": temp_dir,
                "message": "暫存目錄不存在或不可寫"
            }
            
    except Exception as e:
        health_data["checks"]["file_system"] = {
            "status": "error",
            "error": str(e),
            "message": "檔案系統檢查失敗"
        }
    
    # 設置整體狀態
    health_data["status"] = "healthy" if overall_healthy else "unhealthy"
    
    return health_data

@router.get("/database")
async def database_health():
    """資料庫詳細健康檢查"""
    
    try:
        start_time = time.time()
        
        # 基本連接測試
        async with db_manager.get_async_session() as session:
            # 測試查詢
            result = await session.execute(text("SELECT version()"))
            db_version = result.scalar()
            
            # 測試表格存在性
            table_result = await session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """))
            tables = [row[0] for row in table_result.fetchall()]
            
            # 測試資料庫大小
            size_result = await session.execute(text("""
                SELECT pg_size_pretty(pg_database_size('paper_analysis')) as size
            """))
            db_size = size_result.scalar()
            
            # 測試連接池狀態
            pool_status = {
                "pool_size": db_manager.engine.pool.size(),
                "checked_in": db_manager.engine.pool.checkedin(),
                "checked_out": db_manager.engine.pool.checkedout(),
                "overflow": db_manager.engine.pool.overflow(),
                "invalid": db_manager.engine.pool.invalid()
            }
        
        response_time = (time.time() - start_time) * 1000
        
        return {
            "status": "healthy",
            "response_time_ms": round(response_time, 2),
            "database_version": db_version,
            "database_size": db_size,
            "tables": tables,
            "table_count": len(tables),
            "connection_pool": pool_status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"資料庫健康檢查失敗: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "error": str(e),
                "message": "資料庫連接失敗"
            }
        )

@router.get("/migrations")
async def migrations_status():
    """遷移狀態檢查"""
    
    try:
        status = await migration_manager.get_migration_status()
        pending_migrations = await migration_manager.get_pending_migrations()
        
        return {
            "status": status["status"],
            "summary": status,
            "pending_migrations": [
                {
                    "version": m.version,
                    "description": m.description,
                    "filename": m.filename
                }
                for m in pending_migrations
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"遷移狀態檢查失敗: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "error": str(e),
                "message": "遷移狀態檢查失敗"
            }
        )

@router.post("/migrations/apply")
async def apply_pending_migrations():
    """手動應用待處理的遷移"""
    
    try:
        result = await migration_manager.migrate()
        
        if result["status"] == "failed":
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "failed",
                    "message": "遷移應用失敗",
                    "failed_migrations": result["failed_migrations"]
                }
            )
        
        return {
            "status": "success",
            "message": "遷移應用完成",
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"手動遷移失敗: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "error": str(e),
                "message": "遷移應用過程中發生錯誤"
            }
        )

@router.get("/system")
async def system_info():
    """系統資訊"""
    
    try:
        import platform
        
        # CPU 資訊
        cpu_info = {
            "count": psutil.cpu_count(),
            "usage_percent": psutil.cpu_percent(interval=1)
        }
        
        # 記憶體資訊
        memory = psutil.virtual_memory()
        memory_info = {
            "total_gb": round(memory.total / (1024**3), 2),
            "available_gb": round(memory.available / (1024**3), 2),
            "used_gb": round(memory.used / (1024**3), 2),
            "percent_used": memory.percent
        }
        
        # 磁碟資訊
        disk = psutil.disk_usage('/')
        disk_info = {
            "total_gb": round(disk.total / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2),
            "percent_used": round((disk.used / disk.total) * 100, 2)
        }
        
        # 網路資訊
        network = psutil.net_io_counters()
        network_info = {
            "bytes_sent": network.bytes_sent,
            "bytes_recv": network.bytes_recv,
            "packets_sent": network.packets_sent,
            "packets_recv": network.packets_recv
        }
        
        return {
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor()
            },
            "cpu": cpu_info,
            "memory": memory_info,
            "disk": disk_info,
            "network": network_info,
            "python_version": platform.python_version(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"系統資訊取得失敗: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "error": str(e),
                "message": "系統資訊取得失敗"
            }
        ) 