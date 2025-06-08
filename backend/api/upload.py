from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List
import asyncio
from datetime import datetime
import os

from ..core.database import get_db
from ..services.file_service import file_service
from ..services.db_service import db_service
# 移除不再需要的服務imports，因為現在使用統一的processing_service
from ..services.queue_service import TaskPriority
from ..models.paper import PaperCreate, PaperResponse
from ..core.logging import get_logger

logger = get_logger("upload")

router = APIRouter(prefix="/upload", tags=["upload"])

# 處理管道函數
# ❌ 移除 process_paper_pipeline 函數
# 這個函數已被移除，因為processing_service已經提供了相同功能

# ===== 檔案上傳 =====

@router.post("/", response_model=Dict[str, Any])
async def upload_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    上傳PDF檔案
    """
    try:
        # 1. 驗證檔案
        is_valid, error_message = await file_service.validate_file(file)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message
            )
        
        # 2. 計算檔案雜湊值
        file_hash = await file_service.calculate_file_hash(file)
        
        # 3. 檢查是否為重複檔案
        existing_paper = await db_service.get_paper_by_hash(db, file_hash)
        if existing_paper:
            return {
                "success": True,
                "duplicate": True,
                "message": "檔案已存在",
                "paper_id": str(existing_paper.id),
                "existing_filename": existing_paper.file_name,
                "original_filename": file.filename
            }
        
        # 4. 儲存暫存檔案
        file_path, internal_filename = await file_service.save_temp_file(file, file_hash)
        file_size = file_service.get_file_size(file_path)
        
        # 5. 建立論文記錄
        paper_data = PaperCreate(
            file_name=internal_filename,
            original_filename=file.filename,
            file_hash=file_hash,
            file_size=file_size
        )
        
        paper_id = await db_service.create_paper(db, paper_data)
        
        # 6. 加入處理佇列 - 由processing_service自動處理
        
        # 7. 自動選取新上傳的論文
        await db_service.mark_paper_selected(db, paper_id)
        
        # ✅ 8. 使用正式的處理服務 (而非直接處理)
        from ..services.processing_service import processing_service
        task_id = await processing_service.process_file(
            file_id=paper_id,
            user_id=None,  # 如果沒有用戶系統就用None
            priority=TaskPriority.HIGH,  # 上傳的檔案給高優先級
            options={
                "detect_od_cd": True,
                "extract_keywords": True,
                "auto_cleanup": True
            }
        )
        
        return {
            "success": True,
            "duplicate": False,
            "message": "檔案上傳成功，正在處理中",
            "paper_id": paper_id,
            "task_id": task_id,  # 提供task_id用於進度追蹤
            "filename": internal_filename,
            "original_filename": file.filename,
            "file_size": file_size,
            "file_hash": file_hash
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"檔案上傳失敗: {str(e)}"
        )

@router.post("/batch", response_model=Dict[str, Any])
async def upload_multiple_files(
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    批次上傳多個PDF檔案
    """
    try:
        results = []
        total_files = len(files)
        
        if total_files > 10:  # 限制批次上傳數量
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="批次上傳最多支援10個檔案"
            )
        
        for i, file in enumerate(files):
            try:
                # 1. 驗證檔案
                is_valid, error_message = await file_service.validate_file(file)
                if not is_valid:
                    results.append({
                        "filename": file.filename,
                        "success": False,
                        "error": error_message
                    })
                    continue
                
                # 2. 計算檔案雜湊值
                file_hash = await file_service.calculate_file_hash(file)
                
                # 3. 檢查是否為重複檔案
                existing_paper = await db_service.get_paper_by_hash(db, file_hash)
                if existing_paper:
                    results.append({
                        "filename": file.filename,
                        "success": True,
                        "duplicate": True,
                        "paper_id": str(existing_paper.id),
                        "message": "檔案已存在"
                    })
                    continue
                
                # 4. 儲存暫存檔案
                file_path, internal_filename = await file_service.save_temp_file(file, file_hash)
                file_size = file_service.get_file_size(file_path)
                
                # 5. 建立論文記錄
                paper_data = PaperCreate(
                    file_name=internal_filename,
                    original_filename=file.filename,
                    file_hash=file_hash,
                    file_size=file_size
                )
                
                paper_id = await db_service.create_paper(db, paper_data)
                
                # 6. 加入處理佇列 - 由processing_service自動處理
                
                # 7. 自動選取新上傳的論文
                await db_service.mark_paper_selected(db, paper_id)
                
                # ✅ 8. 使用processing_service處理檔案
                from ..services.processing_service import processing_service
                task_id = await processing_service.process_file(
                    file_id=paper_id,
                    user_id=None,
                    priority=TaskPriority.NORMAL,  # 批量上傳使用一般優先級
                    options={
                        "detect_od_cd": True,
                        "extract_keywords": True,
                        "auto_cleanup": True
                    }
                )
                
                results.append({
                    "filename": file.filename,
                    "success": True,
                    "duplicate": False,
                    "paper_id": paper_id,
                    "task_id": task_id,  # 提供task_id用於進度追蹤
                    "internal_filename": internal_filename,
                    "file_size": file_size
                })
                
            except Exception as e:
                results.append({
                    "filename": file.filename,
                    "success": False,
                    "error": str(e)
                })
        
        # 統計結果
        successful_uploads = sum(1 for r in results if r["success"] and not r.get("duplicate", False))
        duplicates = sum(1 for r in results if r.get("duplicate", False))
        failures = sum(1 for r in results if not r["success"])
        
        return {
            "success": True,
            "total_files": total_files,
            "successful_uploads": successful_uploads,
            "duplicates": duplicates,
            "failures": failures,
            "results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批次上傳失敗: {str(e)}"
        )

# ===== 檔案管理 =====

@router.get("/info", response_model=Dict[str, Any])
async def get_upload_info():
    """取得上傳相關資訊"""
    try:
        directory_info = file_service.get_temp_directory_info()
        
        return {
            "success": True,
            "upload_limits": {
                "max_file_size_mb": file_service.max_file_size // (1024 * 1024),
                "allowed_formats": ["PDF"],
                "batch_upload_limit": 10
            },
            "directory_info": directory_info
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"取得上傳資訊失敗: {str(e)}"
        )

@router.post("/cleanup", response_model=Dict[str, Any])
async def cleanup_files(
    max_age_hours: int = 24,
    db: AsyncSession = Depends(get_db)
):
    """清理暫存檔案"""
    try:
        # 1. 清理過期檔案
        cleanup_result = await file_service.cleanup_temp_files(max_age_hours)
        
        # 2. 清理孤立檔案
        # 取得資料庫中所有有效的檔案雜湊
        papers = await db_service.get_all_papers(db)
        valid_hashes = [paper.file_hash for paper in papers if paper.file_hash]
        
        orphan_cleanup_result = await file_service.cleanup_orphaned_files(valid_hashes)
        
        return {
            "success": True,
            "expired_files_cleanup": cleanup_result,
            "orphaned_files_cleanup": orphan_cleanup_result,
            "total_files_deleted": cleanup_result.get("deleted_count", 0) + orphan_cleanup_result.get("deleted_count", 0),
            "total_space_freed_mb": cleanup_result.get("total_size_freed_mb", 0) + orphan_cleanup_result.get("total_size_freed_mb", 0)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"檔案清理失敗: {str(e)}"
        )

@router.delete("/{paper_id}")
async def delete_uploaded_file(
    paper_id: str,
    db: AsyncSession = Depends(get_db)
):
    """刪除已上傳的檔案和相關記錄"""
    try:
        # 1. 檢查論文是否存在
        paper = await db_service.get_paper_by_id(db, paper_id)
        if not paper:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="論文不存在"
            )
        
        # 2. 找到對應的檔案路徑
        file_hash = paper.file_hash
        existing_file_path = await file_service.check_duplicate_file(file_hash)
        
        # 3. 刪除實體檔案
        if existing_file_path:
            await file_service.delete_file(existing_file_path)
        
        # 4. 這裡之後會實作完整的資料庫記錄刪除
        # await db_service.delete_paper(db, paper_id)
        
        return {
            "success": True,
            "message": f"檔案 {paper.original_filename} 已刪除",
            "paper_id": paper_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"刪除檔案失敗: {str(e)}"
        ) 