"""
檔案處理相關 API 端點
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..services.processing_service import processing_service
from ..services.queue_service import queue_service, TaskPriority, TaskStatus
from ..services.file_service import file_service
from ..services.db_service import db_service
from ..core.logging import get_logger

logger = get_logger("api_processing")

router = APIRouter(prefix="/processing", tags=["processing"])

# ===== 請求模型 =====

class ProcessFileRequest(BaseModel):
    file_id: str
    priority: str = "normal"  # urgent, high, normal, low
    options: Optional[Dict[str, Any]] = None

class BatchProcessRequest(BaseModel):
    file_ids: List[str]
    priority: str = "normal"
    options: Optional[Dict[str, Any]] = None

class TaskProgressUpdate(BaseModel):
    current_step: Optional[int] = None
    total_steps: Optional[int] = None
    step_name: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

# ===== 工具函數 =====

def parse_priority(priority_str: str) -> TaskPriority:
    """解析優先序字符串"""
    priority_map = {
        "urgent": TaskPriority.URGENT,
        "high": TaskPriority.HIGH,
        "normal": TaskPriority.NORMAL,
        "low": TaskPriority.LOW
    }
    return priority_map.get(priority_str.lower(), TaskPriority.NORMAL)

# ===== 檔案處理端點 =====

@router.post("/process-file")
async def process_file(request: ProcessFileRequest):
    """開始處理單個檔案"""
    try:
        # 驗證檔案存在
        file_info = await file_service.get_file_info(request.file_id)
        if not file_info:
            raise HTTPException(status_code=404, detail="檔案不存在")
        
        # 檢查檔案狀態
        if file_info.get("status") == "processed":
            return {
                "message": "檔案已處理完成",
                "file_id": request.file_id,
                "status": "already_processed"
            }
        
        # 開始處理
        priority = parse_priority(request.priority)
        task_id = await processing_service.process_file(
            file_id=request.file_id,
            priority=priority,
            options=request.options
        )
        
        return {
            "message": "檔案處理任務已創建",
            "task_id": task_id,
            "file_id": request.file_id,
            "priority": request.priority,
            "estimated_duration": "10-30分鐘"
        }
        
    except Exception as e:
        logger.error(f"處理檔案失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/batch-process")
async def batch_process_files(request: BatchProcessRequest):
    """批次處理多個檔案"""
    try:
        # 驗證所有檔案
        invalid_files = []
        for file_id in request.file_ids:
            file_info = await file_service.get_file_info(file_id)
            if not file_info:
                invalid_files.append(file_id)
        
        if invalid_files:
            raise HTTPException(
                status_code=400, 
                detail=f"以下檔案不存在: {invalid_files}"
            )
        
        # 開始批次處理
        priority = parse_priority(request.priority)
        task_ids = await processing_service.batch_process_files(
            file_ids=request.file_ids,
            priority=priority,
            options=request.options
        )
        
        return {
            "message": "批次處理任務已創建",
            "task_ids": task_ids,
            "file_count": len(request.file_ids),
            "priority": request.priority,
            "estimated_duration": f"{len(request.file_ids) * 15}-{len(request.file_ids) * 45}分鐘"
        }
        
    except Exception as e:
        logger.error(f"批次處理失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/start")
async def start_processing_selected(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    開始處理所有已選取的論文
    """
    try:
        selected_papers = await db_service.get_selected_papers(db)
        if not selected_papers:
            raise HTTPException(status_code=404, detail="沒有選取任何論文")

        paper_ids = [paper.id for paper in selected_papers]
        task_ids = []
        
        # 對每個選取的論文開始處理
        for paper_id in paper_ids:
            # 使用 ProcessingService.process_file 方法，傳入 file_id（即 paper_id）
            task_id = await processing_service.process_file(
                file_id=paper_id,
                user_id=None,  # 可以根據需要傳入實際的用戶ID
                priority=TaskPriority.NORMAL,
                options={
                    "extract_keywords": True,
                    "detect_od_cd": True,
                    "analyze_sections": True,
                    "max_sentences_per_batch": 50
                }
            )
            task_ids.append(task_id)
        
        return {
            "success": True,
            "message": f"已成功將 {len(paper_ids)} 篇論文加入處理佇列",
            "paper_ids": paper_ids,
            "task_ids": task_ids
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"開始處理失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"開始處理時發生內部錯誤: {e}")

# ===== 狀態查詢端點 =====

@router.get("/status/{file_id}")
async def get_processing_status(file_id: str):
    """獲取檔案處理狀態"""
    try:
        status = await processing_service.get_processing_status(file_id)
        
        if not status:
            # 檢查檔案是否存在
            file_info = await file_service.get_file_info(file_id)
            if not file_info:
                raise HTTPException(status_code=404, detail="檔案不存在")
            
            # 檔案存在但沒有處理任務
            return {
                "file_id": file_id,
                "status": "not_started",
                "message": "尚未開始處理"
            }
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查詢處理狀態失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """獲取任務狀態"""
    try:
        task = await queue_service.get_task(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail="任務不存在")
        
        return {
            "task_id": task.task_id,
            "task_type": task.task_type,
            "status": task.status.value,
            "priority": task.priority.value,
            "progress": {
                "current_step": task.progress.current_step,
                "total_steps": task.progress.total_steps,
                "step_name": task.progress.step_name,
                "percentage": task.progress.percentage,
                "details": task.progress.details
            },
            "created_at": task.created_at.isoformat(),
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "error_message": task.error_message,
            "retry_count": task.retry_count,
            "file_id": task.file_id,
            "result": task.result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查詢任務狀態失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===== 佇列管理端點 =====

@router.get("/queue/status")
async def get_queue_status():
    """獲取佇列狀態"""
    try:
        status = await queue_service.get_queue_status()
        return status
        
    except Exception as e:
        logger.error(f"查詢佇列狀態失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/queue/tasks")
async def get_queue_tasks(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """獲取佇列任務列表"""
    try:
        if status:
            try:
                task_status = TaskStatus(status)
                tasks = await queue_service.get_tasks_by_status(task_status)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"無效的狀態: {status}")
        else:
            # 獲取所有任務（這裡簡化實作）
            all_statuses = [TaskStatus.PENDING, TaskStatus.PROCESSING, TaskStatus.COMPLETED, TaskStatus.FAILED]
            tasks = []
            for task_status in all_statuses:
                tasks.extend(await queue_service.get_tasks_by_status(task_status))
        
        # 分頁
        total = len(tasks)
        tasks = tasks[offset:offset + limit]
        
        # 轉換為字典格式
        task_list = [task.to_dict() for task in tasks]
        
        return {
            "tasks": task_list,
            "total": total,
            "limit": limit,
            "offset": offset
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查詢佇列任務失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/task/{task_id}/cancel")
async def cancel_task(task_id: str):
    """取消任務"""
    try:
        success = await queue_service.cancel_task(task_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="任務不存在或無法取消")
        
        return {
            "message": "任務已取消",
            "task_id": task_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取消任務失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/task/{task_id}/retry")
async def retry_task(task_id: str):
    """重試失敗的任務"""
    try:
        success = await queue_service.retry_task(task_id)
        
        if not success:
            raise HTTPException(
                status_code=400, 
                detail="任務不存在,不是失敗狀態或已達重試上限"
            )
        
        return {
            "message": "任務已重新加入佇列",
            "task_id": task_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重試任務失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===== 系統控制端點 =====

@router.post("/queue/start")
async def start_queue():
    """啟動佇列處理"""
    try:
        await queue_service.start_workers()
        return {"message": "佇列處理已啟動"}
        
    except Exception as e:
        logger.error(f"啟動佇列失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/queue/stop")
async def stop_queue():
    """停止佇列處理"""
    try:
        await queue_service.stop_workers()
        return {"message": "佇列處理已停止"}
        
    except Exception as e:
        logger.error(f"停止佇列失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/queue/cleanup")
async def cleanup_old_tasks(days: int = 7):
    """清理舊任務"""
    try:
        deleted_count = await queue_service.cleanup_old_tasks(days)
        return {
            "message": f"已清理 {deleted_count} 個舊任務",
            "deleted_count": deleted_count,
            "days": days
        }
        
    except Exception as e:
        logger.error(f"清理舊任務失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===== 統計和監控端點 =====

@router.get("/stats/summary")
async def get_processing_stats():
    """獲取處理統計摘要"""
    try:
        queue_status = await queue_service.get_queue_status()
        
        # 計算一些基本統計
        total_tasks = queue_status["stats"]["total_tasks"]
        completed_tasks = queue_status["stats"]["completed_tasks"]
        failed_tasks = queue_status["stats"]["failed_tasks"]
        
        success_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        return {
            "queue_status": queue_status,
            "processing_metrics": {
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "failed_tasks": failed_tasks,
                "success_rate": round(success_rate, 2),
                "current_queue_size": queue_status["queue_size"],
                "processing_tasks": queue_status["processing_tasks"]
            },
            "system_status": {
                "queue_running": queue_status["running"],
                "worker_count": queue_status["worker_count"]
            }
        }
        
    except Exception as e:
        logger.error(f"查詢處理統計失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """健康檢查"""
    try:
        queue_status = await queue_service.get_queue_status()
        
        # 檢查各個服務狀態
        health_status = {
            "processing_service": "healthy",
            "queue_service": "healthy" if queue_status["running"] else "stopped",
            "database": "unknown",  # 這裡可以加入資料庫健康檢查
            "grobid": "unknown",    # 這裡可以加入 Grobid 健康檢查
            "n8n": "unknown"        # 這裡可以加入 N8N 健康檢查
        }
        
        overall_status = "healthy" if all(
            status in ["healthy", "unknown"] for status in health_status.values()
        ) else "unhealthy"
        
        return {
            "status": overall_status,
            "services": health_status,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"健康檢查失敗: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
