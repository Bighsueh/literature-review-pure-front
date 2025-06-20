"""
工作區管理API端點
提供工作區的建立、查詢、更新和刪除功能
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List
from uuid import UUID

from ..core.database import get_db
from ..models.user import User, Workspace, WorkspaceCreate, WorkspaceResponse, WorkspaceUpdate
from ..api.dependencies import get_current_user
from ..core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])

@router.post("/", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    workspace_data: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    建立新的工作區
    
    Args:
        workspace_data: 工作區建立數據
        current_user: 當前用戶
        db: 數據庫會話
    
    Returns:
        創建的工作區信息
    
    Raises:
        HTTPException: 當工作區名稱重複時
    """
    try:
        # 檢查用戶是否已有相同名稱的工作區
        stmt = select(Workspace).where(
            and_(
                Workspace.user_id == current_user.id,
                Workspace.name == workspace_data.name
            )
        )
        result = await db.execute(stmt)
        existing_workspace = result.scalar_one_or_none()
        
        if existing_workspace:
            logger.warning(f"Duplicate workspace name '{workspace_data.name}' for user {current_user.id}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Workspace with name '{workspace_data.name}' already exists"
            )
        
        # 創建新工作區
        new_workspace = Workspace(
            name=workspace_data.name,
            user_id=current_user.id
        )
        
        db.add(new_workspace)
        await db.commit()
        await db.refresh(new_workspace)
        
        logger.info(f"Created workspace '{workspace_data.name}' for user {current_user.email}")
        
        return WorkspaceResponse.from_orm(new_workspace)
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create workspace: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create workspace"
        )

@router.get("/", response_model=List[WorkspaceResponse])
async def get_workspaces(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    獲取當前用戶的所有工作區
    
    Args:
        current_user: 當前用戶
        db: 數據庫會話
    
    Returns:
        用戶的工作區列表
    """
    try:
        stmt = select(Workspace).where(Workspace.user_id == current_user.id).order_by(Workspace.created_at.desc())
        result = await db.execute(stmt)
        workspaces = result.scalars().all()
        
        logger.debug(f"Retrieved {len(workspaces)} workspaces for user {current_user.email}")
        
        return [WorkspaceResponse.from_orm(workspace) for workspace in workspaces]
        
    except Exception as e:
        logger.error(f"Failed to get workspaces: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve workspaces"
        )

@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    獲取特定工作區的詳細信息
    
    Args:
        workspace_id: 工作區ID
        current_user: 當前用戶
        db: 數據庫會話
    
    Returns:
        工作區詳細信息
    
    Raises:
        HTTPException: 當工作區不存在或無權限時
    """
    try:
        stmt = select(Workspace).where(
            and_(
                Workspace.id == workspace_id,
                Workspace.user_id == current_user.id
            )
        )
        result = await db.execute(stmt)
        workspace = result.scalar_one_or_none()
        
        if not workspace:
            logger.warning(f"Workspace {workspace_id} not found or access denied for user {current_user.id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )
        
        logger.debug(f"Retrieved workspace {workspace_id} for user {current_user.email}")
        
        return WorkspaceResponse.from_orm(workspace)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workspace: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve workspace"
        )

@router.put("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: UUID,
    workspace_update: WorkspaceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    更新工作區信息
    
    Args:
        workspace_id: 工作區ID
        workspace_update: 更新數據
        current_user: 當前用戶
        db: 數據庫會話
    
    Returns:
        更新後的工作區信息
    
    Raises:
        HTTPException: 當工作區不存在、無權限或名稱重複時
    """
    try:
        # 獲取要更新的工作區
        stmt = select(Workspace).where(
            and_(
                Workspace.id == workspace_id,
                Workspace.user_id == current_user.id
            )
        )
        result = await db.execute(stmt)
        workspace = result.scalar_one_or_none()
        
        if not workspace:
            logger.warning(f"Workspace {workspace_id} not found or access denied for user {current_user.id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )
        
        # 檢查新名稱是否與其他工作區重複
        if workspace_update.name and workspace_update.name != workspace.name:
            stmt_check = select(Workspace).where(
                and_(
                    Workspace.user_id == current_user.id,
                    Workspace.name == workspace_update.name,
                    Workspace.id != workspace_id
                )
            )
            result_check = await db.execute(stmt_check)
            existing_workspace = result_check.scalar_one_or_none()
            
            if existing_workspace:
                logger.warning(f"Duplicate workspace name '{workspace_update.name}' for user {current_user.id}")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Workspace with name '{workspace_update.name}' already exists"
                )
        
        # 更新工作區
        update_data = workspace_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(workspace, field, value)
        
        await db.commit()
        await db.refresh(workspace)
        
        logger.info(f"Updated workspace {workspace_id} for user {current_user.email}")
        
        return WorkspaceResponse.from_orm(workspace)
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update workspace: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update workspace"
        )

@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    刪除工作區
    
    由於數據庫設置了CASCADE刪除，相關的papers、sections、sentences等都會被自動刪除
    
    Args:
        workspace_id: 工作區ID
        current_user: 當前用戶
        db: 數據庫會話
    
    Raises:
        HTTPException: 當工作區不存在或無權限時
    """
    try:
        # 獲取要刪除的工作區
        stmt = select(Workspace).where(
            and_(
                Workspace.id == workspace_id,
                Workspace.user_id == current_user.id
            )
        )
        result = await db.execute(stmt)
        workspace = result.scalar_one_or_none()
        
        if not workspace:
            logger.warning(f"Workspace {workspace_id} not found or access denied for user {current_user.id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )
        
        # 刪除工作區
        await db.delete(workspace)
        await db.commit()
        
        logger.info(f"Deleted workspace {workspace_id} for user {current_user.email}")
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete workspace: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete workspace"
        )

@router.get("/{workspace_id}/stats")
async def get_workspace_stats(
    workspace_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    獲取工作區統計信息
    
    Args:
        workspace_id: 工作區ID
        current_user: 當前用戶
        db: 數據庫會話
    
    Returns:
        工作區統計信息
    """
    try:
        # 首先驗證工作區存在且屬於當前用戶
        stmt = select(Workspace).where(
            and_(
                Workspace.id == workspace_id,
                Workspace.user_id == current_user.id
            )
        )
        result = await db.execute(stmt)
        workspace = result.scalar_one_or_none()
        
        if not workspace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found"
            )
        
        # 獲取統計信息
        # TODO: 實現具體的統計查詢（papers數量、sentences數量等）
        stats = {
            "workspace_id": str(workspace_id),
            "name": workspace.name,
            "created_at": workspace.created_at,
            "papers_count": 0,  # TODO: 從papers表查詢
            "sentences_count": 0,  # TODO: 從sentences表查詢
            "chat_history_count": 0,  # TODO: 從chat_histories表查詢
        }
        
        logger.debug(f"Retrieved stats for workspace {workspace_id}")
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workspace stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve workspace statistics"
        ) 