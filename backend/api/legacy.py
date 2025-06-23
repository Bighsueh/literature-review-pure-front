"""
遺留資料存取API
為新使用者提供訪問升級前歷史資料的能力
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, text
from typing import List, Optional, Dict, Any
from uuid import UUID

from ..core.database import get_db
from ..models.user import User, Workspace
from ..models.paper import Paper, PaperResponse
from ..api.dependencies import get_current_user
from ..core.logging import get_logger
from ..services.db_service import db_service

logger = get_logger(__name__)

router = APIRouter(prefix="/api/legacy", tags=["legacy-data"])

@router.get("/papers", response_model=List[PaperResponse])
async def get_legacy_papers(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=100, description="每頁顯示數量"),
    offset: int = Query(0, ge=0, description="跳過數量")
):
    """
    獲取遺留系統中的論文（無工作區關聯的論文）
    
    這些論文是在系統升級前上傳的，還沒有與任何工作區關聯
    新用戶可以選擇將這些論文導入到自己的工作區中
    
    Args:
        current_user: 當前用戶
        db: 數據庫會話
        limit: 每頁顯示數量
        offset: 跳過數量
    
    Returns:
        遺留論文列表
    """
    try:
        # 查詢沒有workspace_id的論文（遺留數據）
        stmt = (
            select(Paper)
            .where(Paper.workspace_id.is_(None))
            .order_by(Paper.upload_time.desc())
            .limit(limit)
            .offset(offset)
        )
        
        result = await db.execute(stmt)
        papers = result.scalars().all()
        
        logger.debug(f"Retrieved {len(papers)} legacy papers for user {current_user.email}")
        
        # 轉換為響應格式
        paper_responses = []
        for paper in papers:
            paper_dict = {
                "id": str(paper.id),
                "title": paper.title or "未命名論文",
                "file_name": paper.file_name,
                "original_filename": paper.original_filename,
                "file_hash": paper.file_hash,
                "upload_time": paper.upload_time,
                "processing_status": paper.processing_status,
                "selected": False,  # 遺留數據默認未選中
                "section_count": paper.section_count or 0,
                "sentence_count": paper.sentence_count or 0,
                "is_legacy": True  # 標記為遺留數據
            }
            paper_responses.append(PaperResponse(**paper_dict))
        
        return paper_responses
        
    except Exception as e:
        logger.error(f"Failed to get legacy papers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve legacy papers"
        )

@router.get("/papers/count")
async def get_legacy_papers_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    獲取遺留論文總數
    
    Args:
        current_user: 當前用戶
        db: 數據庫會話
    
    Returns:
        遺留論文總數
    """
    try:
        stmt = select(Paper.id).where(Paper.workspace_id.is_(None))
        result = await db.execute(stmt)
        count = len(result.scalars().all())
        
        logger.debug(f"Legacy papers count: {count}")
        
        return {
            "total_count": count,
            "available_for_import": count
        }
        
    except Exception as e:
        logger.error(f"Failed to get legacy papers count: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get legacy papers count"
        )

@router.post("/papers/{paper_id}/import")
async def import_legacy_paper(
    paper_id: UUID,
    workspace_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    將遺留論文導入到指定工作區
    
    Args:
        paper_id: 論文ID
        workspace_id: 目標工作區ID
        current_user: 當前用戶
        db: 數據庫會話
    
    Returns:
        導入結果
    
    Raises:
        HTTPException: 當論文不存在、工作區無權限或論文已被導入時
    """
    try:
        # 1. 驗證工作區屬於當前用戶
        workspace_stmt = select(Workspace).where(
            and_(
                Workspace.id == workspace_id,
                Workspace.user_id == current_user.id
            )
        )
        workspace_result = await db.execute(workspace_stmt)
        workspace = workspace_result.scalar_one_or_none()
        
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this workspace"
            )
        
        # 2. 驗證論文是遺留數據且存在
        paper_stmt = select(Paper).where(
            and_(
                Paper.id == paper_id,
                Paper.workspace_id.is_(None)  # 確保是遺留數據
            )
        )
        paper_result = await db.execute(paper_stmt)
        paper = paper_result.scalar_one_or_none()
        
        if not paper:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Legacy paper not found or already imported"
            )
        
        # 3. 檢查目標工作區是否已有相同檔案雜湊的論文
        existing_paper_stmt = select(Paper).where(
            and_(
                Paper.workspace_id == workspace_id,
                Paper.file_hash == paper.file_hash
            )
        )
        existing_result = await db.execute(existing_paper_stmt)
        existing_paper = existing_result.scalar_one_or_none()
        
        if existing_paper:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A paper with the same content already exists in this workspace"
            )
        
        # 4. 將論文關聯到工作區
        paper.workspace_id = workspace_id
        
        # 5. 同時需要更新相關的句子和章節數據
        # 更新 sentences 表
        await db.execute(text("""
            UPDATE sentences 
            SET workspace_id = :workspace_id 
            WHERE paper_id = :paper_id AND workspace_id IS NULL
        """), {"workspace_id": workspace_id, "paper_id": paper_id})
        
        # 更新 paper_sections 表
        await db.execute(text("""
            UPDATE paper_sections 
            SET workspace_id = :workspace_id 
            WHERE paper_id = :paper_id AND workspace_id IS NULL
        """), {"workspace_id": workspace_id, "paper_id": paper_id})
        
        # 更新 paper_selections 表
        await db.execute(text("""
            UPDATE paper_selections 
            SET workspace_id = :workspace_id 
            WHERE paper_id = :paper_id AND workspace_id IS NULL
        """), {"workspace_id": workspace_id, "paper_id": paper_id})
        
        await db.commit()
        
        logger.info(f"Successfully imported legacy paper {paper_id} to workspace {workspace_id} for user {current_user.email}")
        
        return {
            "success": True,
            "message": "Paper imported successfully",
            "paper_id": str(paper_id),
            "workspace_id": str(workspace_id),
            "workspace_name": workspace.name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to import legacy paper: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to import paper"
        )

@router.post("/papers/batch-import")
async def batch_import_legacy_papers(
    paper_ids: List[UUID],
    workspace_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    批量導入遺留論文到指定工作區
    
    Args:
        paper_ids: 論文ID列表
        workspace_id: 目標工作區ID
        current_user: 當前用戶
        db: 數據庫會話
    
    Returns:
        批量導入結果
    """
    try:
        # 1. 驗證工作區屬於當前用戶
        workspace_stmt = select(Workspace).where(
            and_(
                Workspace.id == workspace_id,
                Workspace.user_id == current_user.id
            )
        )
        workspace_result = await db.execute(workspace_stmt)
        workspace = workspace_result.scalar_one_or_none()
        
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this workspace"
            )
        
        imported_count = 0
        failed_papers = []
        duplicate_papers = []
        
        for paper_id in paper_ids:
            try:
                # 2. 驗證論文是遺留數據且存在
                paper_stmt = select(Paper).where(
                    and_(
                        Paper.id == paper_id,
                        Paper.workspace_id.is_(None)
                    )
                )
                paper_result = await db.execute(paper_stmt)
                paper = paper_result.scalar_one_or_none()
                
                if not paper:
                    failed_papers.append(str(paper_id))
                    continue
                
                # 3. 檢查重複
                existing_paper_stmt = select(Paper).where(
                    and_(
                        Paper.workspace_id == workspace_id,
                        Paper.file_hash == paper.file_hash
                    )
                )
                existing_result = await db.execute(existing_paper_stmt)
                existing_paper = existing_result.scalar_one_or_none()
                
                if existing_paper:
                    duplicate_papers.append(str(paper_id))
                    continue
                
                # 4. 導入論文
                paper.workspace_id = workspace_id
                
                # 更新相關數據
                await db.execute(text("""
                    UPDATE sentences 
                    SET workspace_id = :workspace_id 
                    WHERE paper_id = :paper_id AND workspace_id IS NULL
                """), {"workspace_id": workspace_id, "paper_id": paper_id})
                
                await db.execute(text("""
                    UPDATE paper_sections 
                    SET workspace_id = :workspace_id 
                    WHERE paper_id = :paper_id AND workspace_id IS NULL
                """), {"workspace_id": workspace_id, "paper_id": paper_id})
                
                await db.execute(text("""
                    UPDATE paper_selections 
                    SET workspace_id = :workspace_id 
                    WHERE paper_id = :paper_id AND workspace_id IS NULL
                """), {"workspace_id": workspace_id, "paper_id": paper_id})
                
                imported_count += 1
                
            except Exception as e:
                logger.warning(f"Failed to import paper {paper_id}: {e}")
                failed_papers.append(str(paper_id))
        
        await db.commit()
        
        logger.info(f"Batch import completed: {imported_count} papers imported to workspace {workspace_id}")
        
        return {
            "success": True,
            "imported_count": imported_count,
            "total_requested": len(paper_ids),
            "failed_papers": failed_papers,
            "duplicate_papers": duplicate_papers,
            "workspace_id": str(workspace_id),
            "workspace_name": workspace.name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Batch import failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Batch import failed"
        ) 