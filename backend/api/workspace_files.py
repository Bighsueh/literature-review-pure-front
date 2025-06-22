from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
from uuid import UUID
import asyncio
from datetime import datetime
import os

from ..core.database import get_db
from ..api.dependencies import get_workspace_for_user, get_current_user
from ..models.user import User, Workspace
from ..models.paper import PaperCreate, PaperResponse
from ..services.file_service import file_service
from ..services.db_service import db_service
from ..services.queue_service import TaskPriority
from ..core.logging import get_logger
from ..core.pagination import PaginationParams, create_pagination_params, paginate_query, PaginatedResponse
from ..core.error_handling import APIError, ErrorCodes

logger = get_logger("workspace_files")

router = APIRouter(prefix="/api/workspaces/{workspace_id}/files", tags=["workspace-files"])

# ===== 檔案上傳 =====

@router.post("/", response_model=Dict[str, Any])
async def upload_file_to_workspace(
    workspace_id: UUID,
    file: UploadFile = File(...),
    workspace: Workspace = Depends(get_workspace_for_user),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    上傳PDF檔案到指定工作區
    """
    try:
        # 1. 驗證檔案
        is_valid, error_message = await file_service.validate_file(file)
        if not is_valid:
                    raise APIError(
            error_code=ErrorCodes.VALIDATION_ERROR,
            message=error_message,
            status_code=status.HTTP_400_BAD_REQUEST
        )
        
        # 2. 計算檔案雜湊值
        file_hash = await file_service.calculate_file_hash(file)
        
        # 3. 檢查是否為工作區內重複檔案
        existing_paper = await db_service.get_paper_by_hash_and_workspace(db, file_hash, workspace_id)
        if existing_paper:
            return {
                "success": True,
                "duplicate": True,
                "message": "檔案在此工作區已存在",
                "paper_id": str(existing_paper.id),
                "existing_filename": existing_paper.file_name,
                "original_filename": file.filename
            }
        
        # 4. 儲存工作區暫存檔案
        file_path, internal_filename = await file_service.save_workspace_temp_file(
            file, file_hash, workspace_id
        )
        file_size = file_service.get_file_size(file_path)
        
        # 5. 建立論文記錄
        paper_data = PaperCreate(
            file_name=internal_filename,
            original_filename=file.filename,
            file_hash=file_hash,
            file_size=file_size,
            workspace_id=workspace_id
        )
        
        paper_id = await db_service.create_paper(db, paper_data, workspace_id)
        
        # 6. 自動選取新上傳的論文
        await db_service.mark_paper_selected(db, paper_id)
        
        # 7. 使用正式的處理服務
        from ..services.processing_service import processing_service
        task_id = await processing_service.process_file(
            file_id=paper_id,
            user_id=str(current_user.id),
            priority=TaskPriority.HIGH,
            options={
                "detect_od_cd": True,
                "extract_keywords": False,
                "auto_cleanup": True
            }
        )
        
        return {
            "success": True,
            "duplicate": False,
            "message": "檔案上傳成功，正在處理中",
            "paper_id": paper_id,
            "task_id": task_id,
            "filename": internal_filename,
            "original_filename": file.filename,
            "file_size": file_size,
            "file_hash": file_hash,
            "workspace_id": str(workspace_id)
        }
        
    except HTTPException:
        raise
    except APIError:
        raise
    except Exception as e:
        logger.error(f"檔案上傳失敗: {str(e)}")
        raise APIError(
            error_code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message=f"檔案上傳失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.post("/batch", response_model=Dict[str, Any])
async def upload_multiple_files_to_workspace(
    workspace_id: UUID,
    files: List[UploadFile] = File(...),
    workspace: Workspace = Depends(get_workspace_for_user),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    批次上傳多個PDF檔案到指定工作區
    """
    try:
        results = []
        total_files = len(files)
        
        if total_files > 10:  # 限制批次上傳數量
                    raise APIError(
            error_code=ErrorCodes.VALIDATION_ERROR,
            message="批次上傳最多支援10個檔案",
            status_code=status.HTTP_400_BAD_REQUEST
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
                
                # 3. 檢查是否為工作區內重複檔案
                existing_paper = await db_service.get_paper_by_hash_and_workspace(db, file_hash, workspace_id)
                if existing_paper:
                    results.append({
                        "filename": file.filename,
                        "success": True,
                        "duplicate": True,
                        "paper_id": str(existing_paper.id),
                        "message": "檔案在此工作區已存在"
                    })
                    continue
                
                # 4. 儲存工作區暫存檔案
                file_path, internal_filename = await file_service.save_workspace_temp_file(
                    file, file_hash, workspace_id
                )
                file_size = file_service.get_file_size(file_path)
                
                # 5. 建立論文記錄
                paper_data = PaperCreate(
                    file_name=internal_filename,
                    original_filename=file.filename,
                    file_hash=file_hash,
                    file_size=file_size,
                    workspace_id=workspace_id
                )
                
                paper_id = await db_service.create_paper(db, paper_data, workspace_id)
                
                # 6. 自動選取新上傳的論文
                await db_service.mark_paper_selected(db, paper_id)
                
                # 7. 使用processing_service處理檔案
                from ..services.processing_service import processing_service
                task_id = await processing_service.process_file(
                    file_id=paper_id,
                    user_id=str(current_user.id),
                    priority=TaskPriority.NORMAL,
                    options={
                        "detect_od_cd": True,
                        "extract_keywords": False,
                        "auto_cleanup": True
                    }
                )
                
                results.append({
                    "filename": file.filename,
                    "success": True,
                    "duplicate": False,
                    "paper_id": paper_id,
                    "task_id": task_id,
                    "internal_filename": internal_filename,
                    "file_size": file_size,
                    "workspace_id": str(workspace_id)
                })
                
            except Exception as e:
                logger.error(f"批次上傳單一檔案失敗: {str(e)}")
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
            "workspace_id": str(workspace_id),
            "results": results
        }
        
    except HTTPException:
        raise
    except APIError:
        raise
    except Exception as e:
        logger.error(f"批次上傳失敗: {str(e)}")
        raise APIError(
            error_code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message=f"批次上傳失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# ===== 檔案管理 =====



@router.get("/selected-sentences")
async def get_selected_workspace_files_sentences(
    workspace_id: UUID,
    workspace: Workspace = Depends(get_workspace_for_user),
    db: AsyncSession = Depends(get_db)
):
    """
    獲取工作區中所有選中檔案的句子
    """
    try:
        # 1. 獲取工作區中選中的檔案
        selected_papers = await db_service.get_selected_papers_by_workspace(db, workspace_id)
        
        if not selected_papers:
            return {
                "success": True,
                "sentences": [],
                "total_sentences": 0,
                "total_papers": 0,
                "papers": []
            }
        
        # 2. 獲取所有選中檔案的句子
        from sqlalchemy import select
        from ..models.paper import Sentence
        
        all_sentences = []
        papers_info = []
        
        for paper in selected_papers:
            # 獲取該論文的句子
            query = select(Sentence).where(Sentence.paper_id == paper.id)
            result = await db.execute(query)
            sentences = result.scalars().all()
            
            # 格式化句子資料
            for sentence in sentences:
                all_sentences.append({
                    "id": str(sentence.id),
                    "content": sentence.content,
                    "type": sentence.defining_type or "regular",
                    "reason": sentence.defining_reason,
                    "pageNumber": sentence.page_num,
                    "fileName": paper.file_name,
                    "fileId": str(paper.id),
                    "sentenceOrder": sentence.sentence_order,
                    "sectionId": sentence.section_id,
                    "confidence": getattr(sentence, 'confidence', None),
                    "wordCount": len(sentence.content.split()) if sentence.content else 0
                })
            
            # 收集論文資訊
            papers_info.append({
                "id": str(paper.id),
                "fileName": paper.file_name,
                "processing_status": paper.processing_status
            })
        
        logger.info(f"工作區 {workspace_id} 獲取選中檔案句子: {len(all_sentences)} 個句子，來自 {len(selected_papers)} 個檔案")
        
        return {
            "success": True,
            "sentences": all_sentences,
            "total_sentences": len(all_sentences),
            "total_papers": len(selected_papers),
            "papers": papers_info
        }
        
    except Exception as e:
        logger.error(f"獲取工作區選中檔案句子失敗: {str(e)}")
        raise APIError(
            error_code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message=f"獲取工作區選中檔案句子失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.get("/", response_model=PaginatedResponse[PaperResponse])
async def get_workspace_files(
    workspace_id: UUID,
    pagination: PaginationParams = Depends(create_pagination_params),
    selected_only: bool = Query(False, description="只顯示已選取的檔案"),
    workspace: Workspace = Depends(get_workspace_for_user),
    db: AsyncSession = Depends(get_db)
):
    """
    取得工作區內的檔案列表
    """
    try:
        papers = await db_service.get_papers_by_workspace(
            db, workspace_id, pagination, selected_only
        )
        
        return papers
        
    except Exception as e:
        logger.error(f"取得工作區檔案列表失敗: {str(e)}")
        raise APIError(
            error_code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message=f"取得檔案列表失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.get("/{file_id}/sentences")
async def get_workspace_file_sentences(
    workspace_id: UUID,
    file_id: str,
    workspace: Workspace = Depends(get_workspace_for_user),
    db: AsyncSession = Depends(get_db)
):
    """
    獲取工作區中指定檔案的句子
    """
    try:
        # 1. 驗證論文屬於工作區
        paper = await db_service.get_paper_by_id(db, file_id)
        if not paper or str(paper.workspace_id) != str(workspace_id):
            raise APIError(
                error_code=ErrorCodes.NOT_FOUND,
                message="檔案不存在或不屬於此工作區",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # 2. 獲取該論文的句子
        from sqlalchemy import select
        from ..models.paper import Sentence
        
        query = select(Sentence).where(Sentence.paper_id == file_id)
        result = await db.execute(query)
        sentences = result.scalars().all()
        
        # 3. 格式化句子資料
        formatted_sentences = []
        for sentence in sentences:
            formatted_sentences.append({
                "id": str(sentence.id),
                "content": sentence.content,
                "type": sentence.defining_type or "regular",
                "reason": sentence.defining_reason if hasattr(sentence, 'defining_reason') else None,
                "pageNumber": sentence.page_num,
                "fileName": paper.file_name,
                "fileId": str(paper.id),
                "sentenceOrder": sentence.sentence_order,
                "sectionId": sentence.section_id,
                "confidence": getattr(sentence, 'confidence', None),
                "wordCount": len(sentence.content.split()) if sentence.content else 0
            })
        
        logger.info(f"工作區 {workspace_id} 檔案 {file_id} 獲取句子: {len(formatted_sentences)} 個句子")
        
        return {
            "paper_id": file_id,
            "sentences": formatted_sentences,
            "total_count": len(formatted_sentences),
            "processing_status": paper.processing_status
        }
        
    except Exception as e:
        logger.error(f"獲取工作區檔案句子失敗: {str(e)}")
        raise APIError(
            error_code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message=f"獲取檔案句子失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.get("/{file_id}", response_model=PaperResponse)
async def get_workspace_file(
    workspace_id: UUID,
    file_id: str,
    workspace: Workspace = Depends(get_workspace_for_user),
    db: AsyncSession = Depends(get_db)
):
    """
    取得工作區內指定檔案的詳細資訊
    """
    try:
        paper = await db_service.get_paper_by_id_and_workspace(db, file_id, workspace_id)
        if not paper:
            raise APIError(
                error_code=ErrorCodes.NOT_FOUND,
                message="檔案不存在或不屬於此工作區",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        return PaperResponse.model_validate(paper)
        
    except HTTPException:
        raise
    except APIError:
        raise
    except Exception as e:
        logger.error(f"取得檔案詳細資訊失敗: {str(e)}")
        raise APIError(
            error_code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message=f"取得檔案詳細資訊失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.delete("/{file_id}")
async def delete_workspace_file(
    workspace_id: UUID,
    file_id: str,
    workspace: Workspace = Depends(get_workspace_for_user),
    db: AsyncSession = Depends(get_db)
):
    """
    刪除工作區內的指定檔案
    """
    try:
        # 檢查檔案是否存在且屬於此工作區
        paper = await db_service.get_paper_by_id_and_workspace(db, file_id, workspace_id)
        if not paper:
            raise APIError(
                error_code=ErrorCodes.NOT_FOUND,
                message="檔案不存在或不屬於此工作區",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # 刪除檔案記錄和實體檔案
        await db_service.delete_paper(db, file_id)
        await file_service.delete_workspace_file(paper.file_hash, workspace_id)
        
        return {"success": True, "message": "檔案刪除成功"}
        
    except HTTPException:
        raise
    except APIError:
        raise
    except Exception as e:
        logger.error(f"刪除檔案失敗: {str(e)}")
        raise APIError(
            error_code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message=f"刪除檔案失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.get("/selected", response_model=List[PaperResponse])
async def get_selected_workspace_files(
    workspace_id: UUID,
    workspace: Workspace = Depends(get_workspace_for_user),
    db: AsyncSession = Depends(get_db)
):
    """
    取得工作區內已選取的檔案
    """
    try:
        papers = await db_service.get_selected_papers_by_workspace(db, workspace_id)
        return [PaperResponse.model_validate(paper) for paper in papers]
        
    except Exception as e:
        logger.error(f"取得已選取檔案失敗: {str(e)}")
        raise APIError(
            error_code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message=f"取得已選取檔案失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.post("/select-all")
async def select_all_workspace_files(
    workspace_id: UUID,
    workspace: Workspace = Depends(get_workspace_for_user),
    db: AsyncSession = Depends(get_db)
):
    """
    選取工作區內所有檔案
    """
    try:
        count = await db_service.select_all_papers_in_workspace(db, workspace_id)
        return {
            "success": True,
            "message": f"已選取工作區內 {count} 個檔案",
            "selected_count": count
        }
        
    except Exception as e:
        logger.error(f"選取所有檔案失敗: {str(e)}")
        raise APIError(
            error_code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message=f"選取所有檔案失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.post("/deselect-all")
async def deselect_all_workspace_files(
    workspace_id: UUID,
    workspace: Workspace = Depends(get_workspace_for_user),
    db: AsyncSession = Depends(get_db)
):
    """
    取消選取工作區內所有檔案
    """
    try:
        count = await db_service.deselect_all_papers_in_workspace(db, workspace_id)
        return {
            "success": True,
            "message": f"已取消選取工作區內 {count} 個檔案",
            "deselected_count": count
        }
        
    except Exception as e:
        logger.error(f"取消選取所有檔案失敗: {str(e)}")
        raise APIError(
            error_code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message=f"取消選取所有檔案失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.post("/batch-select")
async def batch_select_workspace_files(
    workspace_id: UUID,
    file_ids: List[str],
    workspace: Workspace = Depends(get_workspace_for_user),
    db: AsyncSession = Depends(get_db)
):
    """
    批次選取工作區內指定檔案
    """
    try:
        count = await db_service.batch_select_papers_in_workspace(db, file_ids, workspace_id)
        return {
            "success": True,
            "message": f"已選取 {count} 個檔案",
            "selected_count": count
        }
        
    except Exception as e:
        logger.error(f"批次選取檔案失敗: {str(e)}")
        raise APIError(
            error_code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message=f"批次選取檔案失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.get("/sections-summary")
async def get_workspace_files_sections_summary(
    workspace_id: UUID,
    workspace: Workspace = Depends(get_workspace_for_user),
    db: AsyncSession = Depends(get_db)
):
    """
    取得工作區內檔案的章節摘要
    """
    try:
        summary = await db_service.get_papers_sections_summary_by_workspace(db, workspace_id)
        return summary
        
    except Exception as e:
        logger.error(f"取得章節摘要失敗: {str(e)}")
        raise APIError(
            error_code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message=f"取得章節摘要失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# ===== 檔案資訊 =====

@router.get("/upload-info")
async def get_workspace_upload_info(
    workspace_id: UUID,
    workspace: Workspace = Depends(get_workspace_for_user)
):
    """取得工作區上傳相關資訊"""
    try:
        directory_info = file_service.get_workspace_temp_directory_info(workspace_id)
        
        return {
            "success": True,
            "workspace_id": str(workspace_id),
            "upload_limits": {
                "max_file_size_mb": file_service.max_file_size // (1024 * 1024),
                "allowed_formats": ["PDF"],
                "batch_upload_limit": 10
            },
            "directory_info": directory_info
        }
        
    except Exception as e:
        logger.error(f"取得上傳資訊失敗: {str(e)}")
        raise APIError(
            error_code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message=f"取得上傳資訊失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.post("/cleanup")
async def cleanup_workspace_files(
    workspace_id: UUID,
    workspace: Workspace = Depends(get_workspace_for_user),
    db: AsyncSession = Depends(get_db)
):
    """
    清理工作區中的臨時檔案和失敗的處理記錄
    """
    try:
        cleanup_stats = await file_service.cleanup_workspace_files(workspace_id)
        
        logger.info(f"工作區 {workspace_id} 清理完成: {cleanup_stats}")
        
        return {
            "success": True,
            "message": "工作區檔案清理完成",
            "stats": cleanup_stats
        }
        
    except Exception as e:
        logger.error(f"清理工作區檔案失敗: {str(e)}")
        raise APIError(
            error_code=ErrorCodes.INTERNAL_SERVER_ERROR,
            message=f"清理工作區檔案失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

