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
from ..core.migration_manager import migration_manager
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
    
    # 2. Schema Drift 檢查
    try:
        has_drift, drift_report = await migration_manager.detect_schema_drift()
        
        if has_drift:
            health_data["checks"]["schema"] = {
                "status": "warning" if not drift_report.get('critical_issues') else "unhealthy",
                "has_drift": True,
                "critical_issues": drift_report.get('critical_issues', []),
                "warnings": drift_report.get('warnings', []),
                "missing_tables": drift_report.get('missing_tables', []),
                "missing_columns": drift_report.get('missing_columns', {}),
                "message": f"檢測到 schema drift: {len(drift_report.get('critical_issues', []))} 個關鍵問題, {len(drift_report.get('warnings', []))} 個警告"
            }
            
            if drift_report.get('critical_issues'):
                overall_healthy = False
        else:
            health_data["checks"]["schema"] = {
                "status": "healthy",
                "has_drift": False,
                "message": "資料庫結構正常"
            }
            
    except Exception as e:
        overall_healthy = False
        health_data["checks"]["schema"] = {
            "status": "error",
            "error": str(e),
            "message": "Schema drift 檢查失敗"
        }
    
    # 3. 遷移狀態檢查
    try:
        current_rev = migration_manager.get_current_revision()
        head_rev = migration_manager.get_head_revision()
        
        health_data["checks"]["migrations"] = {
            "status": "healthy" if current_rev == head_rev else "warning",
            "current_revision": current_rev,
            "head_revision": head_rev,
            "up_to_date": current_rev == head_rev,
            "message": "遷移狀態正常" if current_rev == head_rev else "有待應用的遷移"
        }
        
        if current_rev != head_rev:
            overall_healthy = False
            
    except Exception as e:
        overall_healthy = False
        health_data["checks"]["migrations"] = {
            "status": "unhealthy",
            "error": str(e),
            "message": "遷移狀態檢查失敗"
        }
    
    # 4. 系統資源檢查
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
    
    # 5. 檔案系統檢查
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
            "pool_status": pool_status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Database health check failed: {str(e)}")

@router.get("/schema")
async def schema_health():
    """資料庫結構健康檢查和 Schema Drift 檢測"""
    
    try:
        # 執行 schema drift 檢測
        has_drift, drift_report = await migration_manager.detect_schema_drift()
        
        # 獲取實際資料庫結構
        actual_schema = await migration_manager.get_actual_schema()
        
        # 獲取遷移版本資訊
        current_rev = migration_manager.get_current_revision()
        head_rev = migration_manager.get_head_revision()
        
        return {
            "status": "unhealthy" if has_drift and drift_report.get('critical_issues') else "healthy",
            "has_drift": has_drift,
            "drift_report": drift_report,
            "actual_schema": actual_schema,
            "migration_info": {
                "current_revision": current_rev,
                "head_revision": head_rev,
                "up_to_date": current_rev == head_rev
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Schema health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Schema health check failed: {str(e)}")

@router.post("/schema/fix")
async def fix_schema_issues():
    """自動修復 Schema 問題"""
    
    try:
        # 檢測問題
        has_drift, drift_report = await migration_manager.detect_schema_drift()
        
        if not has_drift:
            return {
                "status": "no_action_needed",
                "message": "未檢測到需要修復的 schema 問題",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        critical_issues = drift_report.get('critical_issues', [])
        if not critical_issues:
            return {
                "status": "no_critical_issues",
                "message": "沒有關鍵問題需要修復",
                "warnings": drift_report.get('warnings', []),
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # 嘗試自動修復
        fix_success = await migration_manager.auto_fix_critical_issues()
        
        if fix_success:
            # 驗證修復結果
            has_drift_after, drift_report_after = await migration_manager.detect_schema_drift()
            
            return {
                "status": "fixed" if not has_drift_after else "partially_fixed",
                "message": "關鍵問題已修復" if not has_drift_after else "部分問題已修復",
                "issues_before": critical_issues,
                "remaining_issues": drift_report_after.get('critical_issues', []),
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return {
                "status": "fix_failed",
                "message": "自動修復失敗，請手動檢查",
                "issues": critical_issues,
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Schema fix failed: {e}")
        raise HTTPException(status_code=500, detail=f"Schema fix failed: {str(e)}")

@router.get("/migrations")
async def migrations_status():
    """遷移狀態檢查"""
    
    try:
        current_rev = migration_manager.get_current_revision()
        head_rev = migration_manager.get_head_revision()
        
        # 檢查表格和欄位狀態
        table_status = await migration_manager.check_tables_exist()
        column_status = await migration_manager.check_columns_exist()
        
        return {
            "status": "up_to_date" if current_rev == head_rev else "pending",
            "current_revision": current_rev,
            "head_revision": head_rev,
            "needs_migration": current_rev != head_rev,
            "table_status": table_status,
            "column_status": column_status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Migration status check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Migration status check failed: {str(e)}")

@router.post("/migrations/apply")
async def apply_pending_migrations():
    """應用待執行的遷移"""
    
    try:
        current_rev = migration_manager.get_current_revision()
        head_rev = migration_manager.get_head_revision()
        
        if current_rev == head_rev:
            return {
                "status": "no_action_needed",
                "message": "沒有待應用的遷移",
                "current_revision": current_rev,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # 執行遷移
        success = migration_manager.run_migrations()
        
        if success:
            new_current_rev = migration_manager.get_current_revision()
            return {
                "status": "success",
                "message": "遷移應用成功",
                "previous_revision": current_rev,
                "current_revision": new_current_rev,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return {
                "status": "failed",
                "message": "遷移應用失敗",
                "current_revision": current_rev,
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Migration apply failed: {e}")
        raise HTTPException(status_code=500, detail=f"Migration apply failed: {str(e)}")

@router.get("/system")
async def system_info():
    """系統資訊"""
    
    try:
        # CPU 資訊
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        
        # 記憶體資訊
        memory = psutil.virtual_memory()
        
        # 硬碟資訊
        disk = psutil.disk_usage('/')
        
        # 系統負載
        load_avg = os.getloadavg() if hasattr(os, 'getloadavg') else None
        
        # 啟動時間
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        
        return {
            "status": "healthy",
            "cpu": {
                "percent": cpu_percent,
                "count": cpu_count,
                "load_average": load_avg
            },
            "memory": {
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "percent": memory.percent
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "percent": round((disk.used / disk.total) * 100, 2)
            },
            "boot_time": boot_time.isoformat(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"System info failed: {e}")
        raise HTTPException(status_code=503, detail=f"System info failed: {str(e)}") 