import os
import hashlib
import shutil
import uuid
from typing import Optional, Tuple, Dict, Any, List
from pathlib import Path
from datetime import datetime, timedelta
from uuid import UUID
from fastapi import UploadFile
try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False
import aiofiles
import asyncio

from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger("file_service")

class FileService:
    """檔案管理服務類"""
    
    def __init__(self):
        self.temp_dir = Path(settings.temp_files_dir)
        self.max_file_size = settings.max_file_size_mb * 1024 * 1024
        self.allowed_mime_types = {
            'application/pdf',
            'application/x-pdf',
            'application/acrobat',
            'applications/vnd.pdf',
            'text/pdf',
            'text/x-pdf'
        }
        
        # 確保暫存目錄存在
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"檔案服務初始化完成，暫存目錄: {self.temp_dir}")
    
    # ===== 檔案上傳相關 =====
    
    async def validate_file(self, file: UploadFile) -> Tuple[bool, Optional[str]]:
        """
        驗證上傳檔案
        返回: (是否有效, 錯誤訊息)
        """
        try:
            # 檢查檔案大小
            if hasattr(file, 'size') and file.size:
                if file.size > self.max_file_size:
                    return False, f"檔案大小超過限制 ({settings.max_file_size_mb}MB)"
            
            # 檢查檔案副檔名
            if not file.filename.lower().endswith('.pdf'):
                return False, "僅支援PDF檔案"
            
            # 讀取檔案前幾個位元組檢查MIME類型
            content = await file.read(1024)
            await file.seek(0)  # 重設檔案指標
            
            # 使用magic檢查檔案類型（如果可用）
            if HAS_MAGIC:
                try:
                    mime_type = magic.from_buffer(content, mime=True)
                    if mime_type not in self.allowed_mime_types:
                        return False, f"不支援的檔案類型: {mime_type}"
                except Exception as e:
                    logger.warning(f"MIME類型檢查失敗: {e}")
                    # 如果magic檢查失敗，就檢查PDF魔數
                    if not content.startswith(b'%PDF'):
                        return False, "檔案不是有效的PDF格式"
            else:
                # 沒有magic時，只檢查PDF魔數
                if not content.startswith(b'%PDF'):
                    return False, "檔案不是有效的PDF格式"
            
            return True, None
            
        except Exception as e:
            logger.error(f"檔案驗證失敗: {e}")
            return False, f"檔案驗證失敗: {str(e)}"
    
    async def calculate_file_hash(self, file: UploadFile) -> str:
        """計算檔案SHA-256雜湊值"""
        try:
            hasher = hashlib.sha256()
            
            # 讀取檔案內容計算雜湊
            await file.seek(0)
            chunk_size = 8192
            
            while chunk := await file.read(chunk_size):
                hasher.update(chunk)
            
            await file.seek(0)  # 重設檔案指標
            file_hash = hasher.hexdigest()
            
            logger.debug(f"檔案雜湊計算完成: {file_hash}")
            return file_hash
            
        except Exception as e:
            logger.error(f"檔案雜湊計算失敗: {e}")
            raise
    
    async def save_temp_file(self, file: UploadFile, file_hash: str) -> Tuple[str, str]:
        """
        儲存暫存檔案
        返回: (檔案路徑, 內部檔案名)
        """
        try:
            # 生成內部檔案名 (使用雜湊值 + 時間戳記)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            internal_filename = f"{file_hash}_{timestamp}.pdf"
            file_path = self.temp_dir / internal_filename
            
            # 使用aiofiles異步儲存檔案
            async with aiofiles.open(file_path, 'wb') as f:
                await file.seek(0)
                content = await file.read()
                await f.write(content)
            
            logger.info(f"檔案已儲存: {file_path}")
            return str(file_path), internal_filename
            
        except Exception as e:
            logger.error(f"儲存暫存檔案失敗: {e}")
            raise
    
    # ===== 工作區化檔案管理 =====
    
    async def save_workspace_temp_file(self, file: UploadFile, file_hash: str, workspace_id: UUID) -> Tuple[str, str]:
        """
        儲存工作區暫存檔案
        返回: (檔案路徑, 內部檔案名)
        """
        try:
            # 創建工作區特定目錄
            workspace_dir = self.temp_dir / str(workspace_id)
            workspace_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成內部檔案名 (使用雜湊值 + 時間戳記)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            internal_filename = f"{file_hash}_{timestamp}.pdf"
            file_path = workspace_dir / internal_filename
            
            # 使用aiofiles異步儲存檔案
            async with aiofiles.open(file_path, 'wb') as f:
                await file.seek(0)
                content = await file.read()
                await f.write(content)
            
            logger.info(f"工作區檔案已儲存: {file_path}")
            return str(file_path), internal_filename
            
        except Exception as e:
            logger.error(f"儲存工作區暫存檔案失敗: {e}")
            raise
    
    async def delete_workspace_file(self, file_hash: str, workspace_id: UUID) -> bool:
        """刪除工作區檔案"""
        try:
            workspace_dir = self.temp_dir / str(workspace_id)
            
            # 尋找符合雜湊值的檔案
            if workspace_dir.exists():
                for file_path in workspace_dir.glob(f"{file_hash}_*.pdf"):
                    if file_path.is_file():
                        file_path.unlink()
                        logger.info(f"工作區檔案已刪除: {file_path}")
                        return True
            
            logger.warning(f"工作區檔案不存在，無法刪除: {file_hash} in workspace {workspace_id}")
            return False
            
        except Exception as e:
            logger.error(f"刪除工作區檔案失敗: {e}")
            return False
    
    def get_workspace_temp_directory_info(self, workspace_id: UUID) -> Dict[str, Any]:
        """取得工作區暫存目錄資訊"""
        try:
            workspace_dir = self.temp_dir / str(workspace_id)
            
            if not workspace_dir.exists():
                return {
                    "workspace_directory": str(workspace_dir),
                    "exists": False,
                    "file_count": 0,
                    "total_size_mb": 0,
                    "files": []
                }
            
            files = []
            total_size = 0
            
            for file_path in workspace_dir.iterdir():
                if file_path.is_file():
                    file_stat = file_path.stat()
                    file_info = {
                        "name": file_path.name,
                        "size_bytes": file_stat.st_size,
                        "size_mb": round(file_stat.st_size / (1024 * 1024), 2),
                        "modified_time": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                    }
                    files.append(file_info)
                    total_size += file_stat.st_size
            
            return {
                "workspace_directory": str(workspace_dir),
                "exists": True,
                "file_count": len(files),
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "files": files
            }
            
        except Exception as e:
            logger.error(f"取得工作區目錄資訊失敗: {e}")
            return {
                "workspace_directory": str(self.temp_dir / str(workspace_id)),
                "exists": False,
                "error": str(e),
                "file_count": 0,
                "total_size_mb": 0,
                "files": []
            }
    
    async def cleanup_workspace_temp_files(self, workspace_id: UUID, max_age_hours: int = 24) -> Dict[str, Any]:
        """
        清理工作區內過期的暫存檔案
        max_age_hours: 檔案最大保留時間（小時）
        """
        try:
            workspace_dir = self.temp_dir / str(workspace_id)
            
            if not workspace_dir.exists():
                return {
                    "deleted_count": 0,
                    "total_size_freed_mb": 0,
                    "deleted_files": [],
                    "message": "工作區目錄不存在"
                }
            
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            deleted_files = []
            total_size_freed = 0
            
            for file_path in workspace_dir.iterdir():
                if file_path.is_file():
                    # 檢查檔案修改時間
                    file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    
                    if file_mtime < cutoff_time:
                        try:
                            file_size = file_path.stat().st_size
                            file_path.unlink()
                            deleted_files.append(str(file_path.name))
                            total_size_freed += file_size
                            logger.debug(f"已清理工作區過期檔案: {file_path.name}")
                        except Exception as e:
                            logger.error(f"清理工作區檔案失敗 {file_path.name}: {e}")
            
            # 如果工作區目錄為空，可選擇性刪除目錄
            try:
                if not any(workspace_dir.iterdir()):
                    workspace_dir.rmdir()
                    logger.info(f"已清理空的工作區目錄: {workspace_dir}")
            except Exception as e:
                logger.debug(f"清理工作區目錄失敗: {e}")
            
            return {
                "deleted_count": len(deleted_files),
                "total_size_freed_mb": round(total_size_freed / (1024 * 1024), 2),
                "deleted_files": deleted_files,
                "workspace_id": str(workspace_id)
            }
            
        except Exception as e:
            logger.error(f"清理工作區暫存檔案失敗: {e}")
            return {
                "deleted_count": 0,
                "total_size_freed_mb": 0,
                "deleted_files": [],
                "error": str(e),
                "workspace_id": str(workspace_id)
            }
    
    async def cleanup_orphaned_workspace_files(self, workspace_id: UUID, valid_file_hashes: List[str]) -> Dict[str, Any]:
        """
        清理工作區內的孤立檔案（資料庫中沒有記錄的檔案）
        valid_file_hashes: 資料庫中有效的檔案雜湊值列表
        """
        try:
            workspace_dir = self.temp_dir / str(workspace_id)
            
            if not workspace_dir.exists():
                return {
                    "deleted_count": 0,
                    "total_size_freed_mb": 0,
                    "deleted_files": [],
                    "message": "工作區目錄不存在"
                }
            
            deleted_files = []
            total_size_freed = 0
            
            for file_path in workspace_dir.iterdir():
                if file_path.is_file() and file_path.suffix.lower() == '.pdf':
                    # 從檔案名提取雜湊值
                    file_hash = file_path.stem.split('_')[0]
                    
                    if file_hash not in valid_file_hashes:
                        try:
                            file_size = file_path.stat().st_size
                            file_path.unlink()
                            deleted_files.append(str(file_path.name))
                            total_size_freed += file_size
                            logger.debug(f"已清理工作區孤立檔案: {file_path.name}")
                        except Exception as e:
                            logger.error(f"清理工作區孤立檔案失敗 {file_path.name}: {e}")
            
            return {
                "deleted_count": len(deleted_files),
                "total_size_freed_mb": round(total_size_freed / (1024 * 1024), 2),
                "deleted_files": deleted_files,
                "workspace_id": str(workspace_id)
            }
            
        except Exception as e:
            logger.error(f"清理工作區孤立檔案失敗: {e}")
            return {
                "deleted_count": 0,
                "total_size_freed_mb": 0,
                "deleted_files": [],
                "error": str(e),
                "workspace_id": str(workspace_id)
            }
    
    # ===== 檔案管理相關 =====
    
    def get_file_size(self, file_path: str) -> int:
        """取得檔案大小（位元組）"""
        try:
            return os.path.getsize(file_path)
        except Exception as e:
            logger.error(f"取得檔案大小失敗: {e}")
            return 0
    
    def file_exists(self, file_path: str) -> bool:
        """檢查檔案是否存在"""
        return os.path.exists(file_path)
    
    async def delete_file(self, file_path: str) -> bool:
        """刪除檔案"""
        try:
            if self.file_exists(file_path):
                os.remove(file_path)
                logger.info(f"檔案已刪除: {file_path}")
                return True
            else:
                logger.warning(f"檔案不存在，無法刪除: {file_path}")
                return False
        except Exception as e:
            logger.error(f"刪除檔案失敗: {e}")
            return False
    
    async def move_file(self, source_path: str, destination_path: str) -> bool:
        """移動檔案"""
        try:
            destination_dir = os.path.dirname(destination_path)
            os.makedirs(destination_dir, exist_ok=True)
            
            shutil.move(source_path, destination_path)
            logger.info(f"檔案已移動: {source_path} -> {destination_path}")
            return True
        except Exception as e:
            logger.error(f"移動檔案失敗: {e}")
            return False
    
    # ===== 檔案清理相關 =====
    
    async def cleanup_temp_files(self, max_age_hours: int = 24) -> Dict[str, Any]:
        """
        清理過期的暫存檔案
        max_age_hours: 檔案最大保留時間（小時）
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            deleted_files = []
            total_size_freed = 0
            
            for file_path in self.temp_dir.iterdir():
                if file_path.is_file():
                    # 檢查檔案修改時間
                    file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    
                    if file_mtime < cutoff_time:
                        try:
                            file_size = file_path.stat().st_size
                            file_path.unlink()
                            deleted_files.append(str(file_path.name))
                            total_size_freed += file_size
                            logger.debug(f"已清理過期檔案: {file_path.name}")
                        except Exception as e:
                            logger.error(f"清理檔案失敗 {file_path.name}: {e}")
            
            cleanup_result = {
                "deleted_count": len(deleted_files),
                "total_size_freed_mb": round(total_size_freed / (1024 * 1024), 2),
                "deleted_files": deleted_files
            }
            
            if deleted_files:
                logger.info(f"檔案清理完成: 刪除 {len(deleted_files)} 個檔案，釋放 {cleanup_result['total_size_freed_mb']}MB")
            
            return cleanup_result
            
        except Exception as e:
            logger.error(f"檔案清理失敗: {e}")
            return {"error": str(e)}
    
    async def cleanup_orphaned_files(self, valid_file_hashes: List[str]) -> Dict[str, Any]:
        """
        清理孤立檔案（資料庫中沒有記錄的檔案）
        valid_file_hashes: 資料庫中有效的檔案雜湊列表
        """
        try:
            deleted_files = []
            total_size_freed = 0
            
            for file_path in self.temp_dir.iterdir():
                if file_path.is_file() and file_path.suffix == '.pdf':
                    # 從檔案名提取雜湊值
                    filename = file_path.stem
                    if '_' in filename:
                        file_hash = filename.split('_')[0]
                        
                        # 檢查雜湊值是否在有效列表中
                        if file_hash not in valid_file_hashes:
                            try:
                                file_size = file_path.stat().st_size
                                file_path.unlink()
                                deleted_files.append(str(file_path.name))
                                total_size_freed += file_size
                                logger.debug(f"已清理孤立檔案: {file_path.name}")
                            except Exception as e:
                                logger.error(f"清理孤立檔案失敗 {file_path.name}: {e}")
            
            cleanup_result = {
                "deleted_count": len(deleted_files),
                "total_size_freed_mb": round(total_size_freed / (1024 * 1024), 2),
                "deleted_files": deleted_files
            }
            
            if deleted_files:
                logger.info(f"孤立檔案清理完成: 刪除 {len(deleted_files)} 個檔案，釋放 {cleanup_result['total_size_freed_mb']}MB")
            
            return cleanup_result
            
        except Exception as e:
            logger.error(f"孤立檔案清理失敗: {e}")
            return {"error": str(e)}
    
    def get_temp_directory_info(self) -> Dict[str, Any]:
        """取得暫存目錄資訊"""
        try:
            total_files = 0
            total_size = 0
            file_types = {}
            
            for file_path in self.temp_dir.iterdir():
                if file_path.is_file():
                    total_files += 1
                    file_size = file_path.stat().st_size
                    total_size += file_size
                    
                    # 統計檔案類型
                    ext = file_path.suffix.lower()
                    file_types[ext] = file_types.get(ext, 0) + 1
            
            return {
                "directory": str(self.temp_dir),
                "total_files": total_files,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "file_types": file_types,
                "free_space_gb": round(shutil.disk_usage(self.temp_dir).free / (1024 * 1024 * 1024), 2)
            }
            
        except Exception as e:
            logger.error(f"取得目錄資訊失敗: {e}")
            return {"error": str(e)}
    
    # ===== 檔案重複檢測 =====
    
    async def check_duplicate_file(self, file_hash: str) -> Optional[str]:
        """
        檢查是否有重複檔案
        返回: 現有檔案路徑（如果存在）
        """
        try:
            for file_path in self.temp_dir.iterdir():
                if file_path.is_file() and file_path.suffix == '.pdf':
                    filename = file_path.stem
                    if '_' in filename:
                        existing_hash = filename.split('_')[0]
                        if existing_hash == file_hash:
                            logger.info(f"發現重複檔案: {file_path}")
                            return str(file_path)
            
            return None
            
        except Exception as e:
            logger.error(f"檢查重複檔案失敗: {e}")
            return None

    # ===== 相容性方法 (為了支援驗證測試) =====
    
    async def save_file(self, file_data: bytes, filename: str, file_id: str = None) -> str:
        """保存檔案 - 相容性方法"""
        if file_id is None:
            file_id = str(uuid.uuid4())
        
        file_path = self.temp_dir / f"{file_id}_{filename}"
        
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(file_data)
        
        logger.info(f"檔案已保存: {file_path}")
        return file_id
    
    async def upload_file(self, file_data: bytes, filename: str) -> Dict[str, Any]:
        """上傳檔案 - 相容性方法"""
        file_id = await self.save_file(file_data, filename)
        
        # 計算檔案雜湊
        hasher = hashlib.sha256()
        hasher.update(file_data)
        file_hash = hasher.hexdigest()
        
        return {
            "file_id": file_id,
            "filename": filename,
            "file_hash": file_hash,
            "file_size": len(file_data),
            "upload_time": datetime.now()
        }
    
    async def is_file_duplicate(self, file_hash: str) -> bool:
        """檢查檔案是否重複 - 相容性方法"""
        duplicate_file = await self.check_duplicate_file(file_hash)
        return duplicate_file is not None
    
    async def cleanup_expired_files(self, days: int = 7) -> int:
        """清理過期檔案 - 相容性方法"""
        result = await self.cleanup_temp_files(max_age_hours=days * 24)
        return result.get("deleted_count", 0)
    
    async def get_file_metadata(self, file_id: str) -> Optional[Dict[str, Any]]:
        """獲取檔案元數據 - 相容性方法"""
        file_info = await self.get_file_info(file_id)
        if file_info:
            return {
                "file_id": file_id,
                "metadata": file_info
            }
        return None
    
    async def get_file_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """獲取檔案資訊 - 基礎方法"""
        try:
            # 在暫存目錄中尋找以 file_id 開頭的檔案
            for file_path in self.temp_dir.iterdir():
                if file_path.is_file() and file_path.name.startswith(file_id):
                    stat = file_path.stat()
                    return {
                        "file_id": file_id,
                        "file_path": str(file_path),
                        "filename": file_path.name,
                        "file_size": stat.st_size,
                        "created_time": datetime.fromtimestamp(stat.st_ctime),
                        "modified_time": datetime.fromtimestamp(stat.st_mtime),
                        "status": "uploaded"
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"獲取檔案資訊失敗: {e}")
            return None
    
    async def list_files(self) -> List[Dict[str, Any]]:
        """列出所有檔案"""
        try:
            files = []
            for file_path in self.temp_dir.iterdir():
                if file_path.is_file():
                    stat = file_path.stat()
                    files.append({
                        "filename": file_path.name,
                        "file_path": str(file_path),
                        "file_size": stat.st_size,
                        "created_time": datetime.fromtimestamp(stat.st_ctime),
                        "modified_time": datetime.fromtimestamp(stat.st_mtime)
                    })
            
            return files
            
        except Exception as e:
            logger.error(f"列出檔案失敗: {e}")
            return []

# 建立服務實例
file_service = FileService() 