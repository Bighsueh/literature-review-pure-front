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
from ..simplified_migration import migration_manager
from ..core.logging import get_logger
from ..core.config import get_settings
from ..core.observability import observability

logger = get_logger(__name__)
router = APIRouter(prefix="/api/health", tags=["健康檢查"])

@router.get("/", response_model=Dict[str, Any])
async def health_check():
    """基本健康檢查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "學術研究管理平台後端",
        "version": "1.0.0"
    }

@router.get("/detailed", response_model=Dict[str, Any])
async def detailed_health_check():
    """詳細健康檢查，包含系統指標和可觀測性資料"""
    try:
        # 取得完整的可觀測性資料
        observability_data = await observability.get_observability_data()
        
        return {
            "service": "學術研究管理平台後端",
        "version": "1.0.0",
            "status": observability_data['health']['status'],
            "timestamp": observability_data['timestamp'],
            "health_checks": observability_data['health']['checks'],
            "system_metrics": {
                "cpu_percent": observability_data['metrics']['gauges'].get('system_cpu_percent', 0),
                "memory_percent": observability_data['metrics']['gauges'].get('system_memory_percent', 0),
                "disk_percent": observability_data['metrics']['gauges'].get('system_disk_percent', 0),
            },
            "performance": {
                "active_requests": len(observability_data['active_requests']),
                "total_requests": sum(observability_data['metrics']['counters'].values()) if observability_data['metrics']['counters'] else 0,
            },
            "system_info": observability_data['system_info']
        }
        
    except Exception as e:
        logger.error(f"詳細健康檢查失敗: {str(e)}")
        return {
            "service": "學術研究管理平台後端",
            "version": "1.0.0",
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

@router.get("/metrics", response_model=Dict[str, Any])
async def get_metrics():
    """取得系統指標"""
    try:
        # 收集最新的系統指標
        observability.system_monitor.collect_system_metrics()
        
        # 返回指標資料
        metrics = observability.metrics_collector.get_metrics()
        
        return {
            "success": True,
            "metrics": metrics,
            "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"取得指標失敗: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.get("/performance", response_model=Dict[str, Any])
async def get_performance_stats():
    """取得效能統計"""
    try:
        active_requests = observability.performance_monitor.get_active_requests()
        metrics = observability.metrics_collector.get_metrics()
        
        # 計算效能統計
        request_counts = {}
        error_counts = {}
        response_times = {}
        
        for key, value in metrics['counters'].items():
            if 'http_requests_total' in key:
                request_counts[key] = value
            elif 'http_errors_total' in key:
                error_counts[key] = value
                
        for key, values in metrics['histograms'].items():
            if 'http_request_duration_seconds' in key:
                if values:
                    durations = [v['value'] for v in values]
                    response_times[key] = {
                        'count': len(durations),
                        'avg': sum(durations) / len(durations),
                        'min': min(durations),
                        'max': max(durations),
                        'p95': sorted(durations)[int(len(durations) * 0.95)] if durations else 0
                    }
        
        return {
            "success": True,
            "active_requests": {
                "count": len(active_requests),
                "requests": active_requests
            },
            "request_counts": request_counts,
            "error_counts": error_counts,
            "response_times": response_times,
            "timestamp": datetime.now().isoformat()
        }
            
    except Exception as e:
        logger.error(f"取得效能統計失敗: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@router.post("/metrics/reset")
async def reset_metrics():
    """重設指標 (僅用於測試環境)"""
    try:
        observability.metrics_collector.reset_metrics()
        
        return {
            "success": True,
            "message": "指標已重設",
            "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"重設指標失敗: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

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
    """資料庫結構健康檢查（簡化版）"""
    
    try:
        # 檢查資料庫連接
        connection_ok = await migration_manager.check_database_connection()
        
        # 獲取遷移版本資訊
        current_rev = migration_manager.get_current_revision()
        head_rev = migration_manager.get_head_revision()
        
        return {
            "status": "healthy" if connection_ok and current_rev == head_rev else "warning",
            "database_connected": connection_ok,
            "migration_info": {
                "current_revision": current_rev,
                "head_revision": head_rev,
                "up_to_date": current_rev == head_rev
            },
            "message": "資料庫結構正常" if connection_ok and current_rev == head_rev else "需要檢查遷移狀態",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Schema health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Schema health check failed: {str(e)}")

@router.post("/schema/fix")
async def fix_schema_issues():
    """執行資料庫遷移來修復問題（簡化版）"""
    
    try:
        # 檢查當前遷移狀態
        current_rev = migration_manager.get_current_revision()
        head_rev = migration_manager.get_head_revision()
        
        if current_rev == head_rev:
            return {
                "status": "no_action_needed",
                "message": "資料庫已是最新版本，無需修復",
                "current_revision": current_rev,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # 執行自動遷移
        success = await migration_manager.auto_migrate()
        
        if success:
            new_current_rev = migration_manager.get_current_revision()
            return {
                "status": "fixed",
                "message": "資料庫遷移成功完成",
                "previous_revision": current_rev,
                "current_revision": new_current_rev,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return {
                "status": "fix_failed",
                "message": "資料庫遷移失敗，請檢查日誌",
                "current_revision": current_rev,
                "timestamp": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Schema fix failed: {e}")
        raise HTTPException(status_code=500, detail=f"Schema fix failed: {str(e)}")

@router.get("/migrations")
async def migrations_status():
    """遷移狀態檢查（簡化版）"""
    
    try:
        # 獲取遷移狀態
        status = await migration_manager.get_migration_status()
        
        return {
            **status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Migration status check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Migration status check failed: {str(e)}")

@router.post("/migrations/apply")
async def apply_pending_migrations():
    """應用待執行的遷移（簡化版）"""
    
    try:
        # 執行自動遷移
        success = await migration_manager.auto_migrate()
        
        if success:
            # 獲取最新狀態
            status = await migration_manager.get_migration_status()
            return {
                "status": "success",
                "message": "遷移應用成功",
                "migration_status": status,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return {
                "status": "failed",
                "message": "遷移應用失敗，請檢查日誌",
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