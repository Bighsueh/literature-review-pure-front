"""
佇列管理服務
支援任務優先序、進度追蹤、狀態管理和持久化
"""

import asyncio
import uuid
import time
import json
from enum import Enum
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import threading
from concurrent.futures import ThreadPoolExecutor

from ..core.config import settings
from ..core.logging import get_logger
from .db_service import db_service

logger = get_logger("queue_service")

class TaskStatus(Enum):
    """任務狀態"""
    PENDING = "pending"          # 等待處理
    PROCESSING = "processing"    # 處理中
    COMPLETED = "completed"      # 完成
    FAILED = "failed"           # 失敗
    CANCELLED = "cancelled"     # 取消
    RETRYING = "retrying"       # 重試中

class TaskPriority(Enum):
    """任務優先序"""
    URGENT = 1     # 緊急
    HIGH = 2       # 高
    NORMAL = 3     # 正常
    LOW = 4        # 低

@dataclass
class TaskProgress:
    """任務進度"""
    current_step: int = 0
    total_steps: int = 0
    step_name: str = ""
    percentage: float = 0.0
    estimated_remaining: Optional[float] = None  # 預估剩餘時間（秒）
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}
    
    def update(self, current_step: int = None, step_name: str = None, details: Dict = None):
        """更新進度"""
        if current_step is not None:
            self.current_step = current_step
        if step_name:
            self.step_name = step_name
        if details:
            self.details.update(details)
        
        # 計算百分比
        if self.total_steps > 0:
            self.percentage = (self.current_step / self.total_steps) * 100

@dataclass
class QueueTask:
    """佇列任務"""
    task_id: str
    task_type: str
    data: Dict[str, Any]
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: TaskProgress = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: int = 300  # 5分鐘預設超時
    
    # 關聯信息
    user_id: Optional[str] = None
    file_id: Optional[str] = None
    parent_task_id: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.progress is None:
            self.progress = TaskProgress()
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "data": self.data,
            "priority": self.priority.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "progress": asdict(self.progress),
            "result": self.result,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "timeout_seconds": self.timeout_seconds,
            "user_id": self.user_id,
            "file_id": self.file_id,
            "parent_task_id": self.parent_task_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QueueTask':
        """從字典創建任務"""
        task = cls(
            task_id=data["task_id"],
            task_type=data["task_type"],
            data=data["data"],
            priority=TaskPriority(data["priority"]),
            status=TaskStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
            timeout_seconds=data.get("timeout_seconds", 300),
            user_id=data.get("user_id"),
            file_id=data.get("file_id"),
            parent_task_id=data.get("parent_task_id")
        )
        
        if data.get("started_at"):
            task.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            task.completed_at = datetime.fromisoformat(data["completed_at"])
        if data.get("progress"):
            task.progress = TaskProgress(**data["progress"])
        if data.get("result"):
            task.result = data["result"]
        if data.get("error_message"):
            task.error_message = data["error_message"]
        
        return task

class QueueService:
    """佇列管理服務"""
    
    def __init__(self):
        # 內存佇列 (優先序排序)
        self._queue: List[QueueTask] = []
        self._processing_tasks: Dict[str, QueueTask] = {}
        self._completed_tasks: Dict[str, QueueTask] = {}
        
        # 狀態管理
        self._running = False
        self._worker_count = 3  # 工作者數量
        self._workers: List[asyncio.Task] = []
        
        # 進度回調
        self._progress_callbacks: Dict[str, List[Callable]] = {}
        
        # 統計
        self._stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "processing_tasks": 0,
            "queue_size": 0
        }
        
        # 任務處理器映射
        self._task_handlers: Dict[str, Callable] = {}
        
        # 線程鎖
        self._lock = asyncio.Lock()
        
        logger.info("佇列服務初始化完成")
    
    # ===== 任務處理器註冊 =====
    
    def register_handler(self, task_type: str, handler: Callable):
        """註冊任務處理器"""
        self._task_handlers[task_type] = handler
        logger.info(f"註冊任務處理器: {task_type}")
    
    def unregister_handler(self, task_type: str):
        """取消註冊任務處理器"""
        if task_type in self._task_handlers:
            del self._task_handlers[task_type]
            logger.info(f"取消註冊任務處理器: {task_type}")
    
    # ===== 任務管理 =====
    
    async def add_task(
        self,
        task_type: str,
        data: Dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
        user_id: str = None,
        file_id: str = None,
        parent_task_id: str = None,
        max_retries: int = 3,
        timeout_seconds: int = 300
    ) -> str:
        """添加任務到佇列"""
        async with self._lock:
            # 檢查是否有相同的任務已經在處理或等待中
            if file_id:
                duplicate_task = await self._find_duplicate_task(file_id, task_type)
                if duplicate_task:
                    logger.warning(f"發現重複任務，跳過添加: {duplicate_task.task_id} (file_id: {file_id})")
                    return duplicate_task.task_id
            
            task_id = str(uuid.uuid4())
            
            task = QueueTask(
                task_id=task_id,
                task_type=task_type,
                data=data,
                priority=priority,
                user_id=user_id,
                file_id=file_id,
                parent_task_id=parent_task_id,
                max_retries=max_retries,
                timeout_seconds=timeout_seconds
            )
            
            # 插入到適當位置（優先序排序）
            inserted = False
            for i, queued_task in enumerate(self._queue):
                if task.priority.value < queued_task.priority.value:
                    self._queue.insert(i, task)
                    inserted = True
                    break
            
            if not inserted:
                self._queue.append(task)
            
            # 持久化到資料庫
            await self._persist_task(task)
            
            # 更新統計
            self._stats["total_tasks"] += 1
            self._stats["queue_size"] = len(self._queue)
            
            logger.info(f"任務已添加到佇列: {task_id} ({task_type}), 優先序: {priority.name}")
            return task_id
    
    async def get_task(self, task_id: str) -> Optional[QueueTask]:
        """獲取任務"""
        # 檢查處理中的任務
        if task_id in self._processing_tasks:
            return self._processing_tasks[task_id]
        
        # 檢查已完成的任務
        if task_id in self._completed_tasks:
            return self._completed_tasks[task_id]
        
        # 檢查佇列中的任務
        for task in self._queue:
            if task.task_id == task_id:
                return task
        
        # 注意：由於架構變更，目前不支援從資料庫恢復單個任務
        # 如果需要此功能，需要重新設計與資料庫的交互方式
        logger.debug(f"任務 {task_id} 未在內存中找到")
        
        return None
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任務"""
        async with self._lock:
            # 從佇列中移除
            for i, task in enumerate(self._queue):
                if task.task_id == task_id:
                    task.status = TaskStatus.CANCELLED
                    task.completed_at = datetime.now()
                    self._queue.pop(i)
                    self._completed_tasks[task_id] = task
                    await self._persist_task(task)
                    logger.info(f"任務已取消: {task_id}")
                    return True
            
            # 檢查處理中的任務
            if task_id in self._processing_tasks:
                task = self._processing_tasks[task_id]
                task.status = TaskStatus.CANCELLED
                task.completed_at = datetime.now()
                # 這裡可以發送中斷信號給工作者
                logger.info(f"處理中任務標記為取消: {task_id}")
                return True
        
        return False
    
    async def retry_task(self, task_id: str) -> bool:
        """重試失敗的任務"""
        task = await self.get_task(task_id)
        if not task or task.status != TaskStatus.FAILED:
            return False
        
        if task.retry_count >= task.max_retries:
            logger.warning(f"任務重試次數已達上限: {task_id}")
            return False
        
        # 檢查特定的錯誤類型，決定是否應該重試
        if task.error_message and any(error in task.error_message for error in [
            "檔案記錄不存在於資料庫",
            "檔案實體不存在",
            "處理失敗，任務已停止"
        ]):
            logger.warning(f"任務包含不可重試錯誤，停止重試: {task_id} - {task.error_message}")
            return False
        
        async with self._lock:
            # 重置任務狀態
            task.status = TaskStatus.PENDING
            task.started_at = None
            task.completed_at = None
            task.error_message = None
            task.retry_count += 1
            task.progress = TaskProgress()
            
            # 重新加入佇列
            if task_id in self._completed_tasks:
                del self._completed_tasks[task_id]
            
            self._queue.append(task)
            await self._persist_task(task)
            
            logger.info(f"任務已重新加入佇列: {task_id} (重試次數: {task.retry_count})")
            return True
    
    async def _find_duplicate_task(self, file_id: str, task_type: str) -> Optional[QueueTask]:
        """查找重複任務"""
        # 檢查佇列中的任務
        for task in self._queue:
            if task.file_id == file_id and task.task_type == task_type and task.status == TaskStatus.PENDING:
                return task
        
        # 檢查處理中的任務
        for task in self._processing_tasks.values():
            if task.file_id == file_id and task.task_type == task_type and task.status == TaskStatus.PROCESSING:
                return task
        
        return None
    
    async def cleanup_failed_tasks(self, file_id: str = None):
        """清理失敗的任務"""
        async with self._lock:
            tasks_to_remove = []
            
            # 從佇列中移除相關的失敗任務
            for i, task in enumerate(self._queue):
                if (file_id is None or task.file_id == file_id) and task.status in [TaskStatus.FAILED, TaskStatus.CANCELLED]:
                    tasks_to_remove.append(i)
            
            # 倒序移除，避免索引問題
            for i in reversed(tasks_to_remove):
                removed_task = self._queue.pop(i)
                self._completed_tasks[removed_task.task_id] = removed_task
                logger.info(f"清理失敗任務: {removed_task.task_id}")
            
            # 更新統計
            self._stats["queue_size"] = len(self._queue)
    
    # ===== 進度管理 =====
    
    async def update_progress(
        self,
        task_id: str,
        current_step: int = None,
        total_steps: int = None,
        step_name: str = None,
        details: Dict[str, Any] = None
    ):
        """更新任務進度"""
        task = await self.get_task(task_id)
        if not task:
            return
        
        if total_steps is not None:
            task.progress.total_steps = total_steps
        
        task.progress.update(
            current_step=current_step,
            step_name=step_name,
            details=details or {}
        )
        
        # 呼叫進度回調
        if task_id in self._progress_callbacks:
            for callback in self._progress_callbacks[task_id]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(task.progress)
                    else:
                        callback(task.progress)
                except Exception as e:
                    logger.error(f"進度回調錯誤: {e}")
        
        # 持久化進度
        await self._persist_task(task)
        
        logger.debug(f"任務進度更新: {task_id} - {task.progress.step_name} ({task.progress.percentage:.1f}%)")
    
    def add_progress_callback(self, task_id: str, callback: Callable):
        """添加進度回調函數"""
        if task_id not in self._progress_callbacks:
            self._progress_callbacks[task_id] = []
        self._progress_callbacks[task_id].append(callback)
    
    def remove_progress_callbacks(self, task_id: str):
        """移除進度回調函數"""
        if task_id in self._progress_callbacks:
            del self._progress_callbacks[task_id]
    
    # ===== 佇列管理 =====
    
    async def start_workers(self):
        """啟動工作者"""
        if self._running:
            return
        
        self._running = True
        
        # 創建工作者任務
        for i in range(self._worker_count):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self._workers.append(worker)
        
        # 從資料庫恢復未完成的任務
        await self._restore_tasks()
        
        logger.info(f"佇列服務已啟動，工作者數量: {self._worker_count}")
    
    async def stop_workers(self):
        """停止工作者"""
        if not self._running:
            return
        
        self._running = False
        
        # 取消所有工作者
        for worker in self._workers:
            worker.cancel()
        
        # 等待工作者結束
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        
        logger.info("佇列服務已停止")
    
    async def _worker(self, worker_name: str):
        """工作者主循環"""
        logger.info(f"工作者 {worker_name} 已啟動")
        
        while self._running:
            try:
                task = await self._get_next_task()
                
                if task:
                    await self._process_task(task, worker_name)
                else:
                    # 沒有任務，等待一段時間
                    await asyncio.sleep(1)
            
            except asyncio.CancelledError:
                logger.info(f"工作者 {worker_name} 被取消")
                break
            except Exception as e:
                logger.error(f"工作者 {worker_name} 異常: {e}")
                await asyncio.sleep(5)  # 錯誤後等待5秒
        
        logger.info(f"工作者 {worker_name} 已停止")
    
    async def _get_next_task(self) -> Optional[QueueTask]:
        """獲取下一個任務"""
        async with self._lock:
            if self._queue:
                task = self._queue.pop(0)
                task.status = TaskStatus.PROCESSING
                task.started_at = datetime.now()
                self._processing_tasks[task.task_id] = task
                self._stats["queue_size"] = len(self._queue)
                self._stats["processing_tasks"] = len(self._processing_tasks)
                return task
        
        return None
    
    async def _process_task(self, task: QueueTask, worker_name: str):
        """處理單個任務"""
        logger.info(f"開始處理任務: {task.task_id} ({task.task_type}) - 工作者: {worker_name}")
        
        try:
            # 檢查是否有對應的處理器
            if task.task_type not in self._task_handlers:
                raise ValueError(f"未找到任務處理器: {task.task_type}")
            
            handler = self._task_handlers[task.task_type]
            
            # 設置超時
            timeout = task.timeout_seconds
            
            # 執行任務處理器
            try:
                result = await asyncio.wait_for(
                    handler(task),
                    timeout=timeout
                )
                
                # 任務成功完成
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now()
                task.result = result
                task.progress.update(
                    current_step=task.progress.total_steps,
                    step_name="完成",
                    details={"completed_at": task.completed_at.isoformat()}
                )
                
                self._stats["completed_tasks"] += 1
                logger.info(f"任務處理完成: {task.task_id}")
                
            except asyncio.TimeoutError:
                raise Exception(f"任務超時 ({timeout}秒)")
            
        except Exception as e:
            # 任務處理失敗
            error_message = str(e)
            task.error_message = error_message
            task.completed_at = datetime.now()
            
            # 檢查是否需要重試
            if task.retry_count < task.max_retries:
                task.status = TaskStatus.RETRYING
                task.retry_count += 1
                task.started_at = None  # 重置開始時間
                
                # 指數退避延遲
                delay = 2 ** task.retry_count
                await asyncio.sleep(delay)
                
                # 重新加入佇列 (使用原任務，不創建新任務)
                async with self._lock:
                    task.status = TaskStatus.PENDING
                    # 按優先序插入佇列
                    inserted = False
                    for i, queued_task in enumerate(self._queue):
                        if task.priority.value < queued_task.priority.value:
                            self._queue.insert(i, task)
                            inserted = True
                            break
                    if not inserted:
                        self._queue.append(task)
                    
                    self._stats["queue_size"] = len(self._queue)
                
                logger.warning(f"任務重試中: {task.task_id} (次數: {task.retry_count})")
                return  # 重要：直接返回，不要移到完成列表
            else:
                task.status = TaskStatus.FAILED
                self._stats["failed_tasks"] += 1
                logger.error(f"任務處理失敗: {task.task_id} - {error_message}")
        
        finally:
            # 從處理中列表移除
            async with self._lock:
                if task.task_id in self._processing_tasks:
                    del self._processing_tasks[task.task_id]
                
                # 移動到已完成列表
                self._completed_tasks[task.task_id] = task
                self._stats["processing_tasks"] = len(self._processing_tasks)
            
            # 持久化任務狀態
            await self._persist_task(task)
            
            # 清理進度回調
            self.remove_progress_callbacks(task.task_id)
    
    # ===== 持久化 =====
    
    async def _persist_task(self, task: QueueTask):
        """持久化任務到資料庫 (目前簡化為內存模式)"""
        try:
            # 注意：由於架構變更，目前暫時使用內存持久化
            # 任務狀態已在內存佇列中管理，無需額外持久化
            logger.debug(f"任務 {task.task_id} 狀態已更新: {task.status.value}")
            
        except Exception as e:
            logger.error(f"持久化任務失敗: {e}")
    
    async def _restore_tasks(self):
        """從資料庫恢復任務 (目前簡化為空操作)"""
        try:
            # 注意：由於架構變更，目前使用內存模式，無需從資料庫恢復
            # 服務重啟時會從空佇列開始
            logger.info("佇列服務採用內存模式，無需恢復任務")
            
        except Exception as e:
            logger.error(f"恢復任務失敗: {e}")
    
    # ===== 查詢和統計 =====
    
    async def get_queue_status(self) -> Dict[str, Any]:
        """獲取佇列狀態"""
        return {
            "queue_size": len(self._queue),
            "processing_tasks": len(self._processing_tasks),
            "completed_tasks": len(self._completed_tasks),
            "running": self._running,
            "worker_count": self._worker_count,
            "stats": self._stats.copy()
        }
    
    async def get_tasks_by_status(self, status: TaskStatus) -> List[QueueTask]:
        """根據狀態獲取任務列表"""
        tasks = []
        
        if status == TaskStatus.PENDING:
            tasks.extend(self._queue)
        elif status == TaskStatus.PROCESSING:
            tasks.extend(self._processing_tasks.values())
        else:
            # 查詢已完成的任務
            tasks.extend([
                task for task in self._completed_tasks.values()
                if task.status == status
            ])
        
        return tasks
    
    async def get_tasks_by_user(self, user_id: str) -> List[QueueTask]:
        """獲取用戶的所有任務"""
        tasks = []
        
        # 檢查佇列中的任務
        tasks.extend([task for task in self._queue if task.user_id == user_id])
        
        # 檢查處理中的任務
        tasks.extend([task for task in self._processing_tasks.values() if task.user_id == user_id])
        
        # 檢查已完成的任務
        tasks.extend([task for task in self._completed_tasks.values() if task.user_id == user_id])
        
        return tasks
    
    async def find_task_by_file_id(self, file_id: str) -> Optional[QueueTask]:
        """根據 file_id 查找正在處理的任務"""
        async with self._lock:
            # 首先在處理中的任務裡尋找
            for task in self._processing_tasks.values():
                if task.file_id == file_id:
                    return task
            
            # 如果不在處理中，可能在等待佇列裡
            for task in self._queue:
                if task.file_id == file_id:
                    return task
        return None
    
    async def cleanup_old_tasks(self, days: int = 7):
        """清理舊的已完成任務"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        try:
            # 清理內存中的舊任務
            deleted_count = 0
            tasks_to_remove = []
            
            for task_id, task in self._completed_tasks.items():
                if (task.completed_at and 
                    task.completed_at < cutoff_date and 
                    task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]):
                    tasks_to_remove.append(task_id)
            
            for task_id in tasks_to_remove:
                del self._completed_tasks[task_id]
                deleted_count += 1
            
            logger.info(f"清理舊任務: {deleted_count} 個")
            return deleted_count
            
        except Exception as e:
            logger.error(f"清理舊任務失敗: {e}")
            return 0

# 建立服務實例
queue_service = QueueService() 