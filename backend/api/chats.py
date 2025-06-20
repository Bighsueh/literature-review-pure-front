"""
工作區化的對話API端點
支援工作區隔離的AI對話和歷史記錄管理
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from typing import List, Optional, Dict, Any
from uuid import UUID

from ..core.database import get_db
from ..models.user import User, Workspace
from ..models.chat import ChatHistory, ChatHistoryCreate, ChatHistoryResponse, ChatHistoryListResponse
from ..api.dependencies import get_current_user, get_workspace_for_user
from ..core.pagination import (
    PaginationParams, 
    create_pagination_params, 
    paginate_workspace_chats,
    FilterParams,
    create_filter_params
)
from ..core.logging import get_logger
from ..services.unified_query_service import unified_query_processor

logger = get_logger(__name__)

router = APIRouter(prefix="/api/workspaces/{workspace_id}/chats", tags=["chats"])

@router.get("/", response_model=ChatHistoryListResponse)
async def get_chat_history(
    workspace: Workspace = Depends(get_workspace_for_user),
    pagination: PaginationParams = Depends(create_pagination_params),
    filters: FilterParams = Depends(create_filter_params),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    獲取工作區的對話歷史
    
    Args:
        workspace: 工作區對象（通過依賴項驗證）
        pagination: 分頁參數
        filters: 過濾參數
        current_user: 當前用戶
        db: 數據庫會話
    
    Returns:
        分頁的對話歷史列表
    """
    try:
        # 使用分頁輔助函數
        chats, meta = await paginate_workspace_chats(
            db, str(workspace.id), pagination, filters
        )
        
        # 轉換為響應格式
        chat_responses = [
            ChatHistoryResponse(
                id=str(chat.id),
                workspace_id=str(chat.workspace_id),
                user_question=chat.user_question,
                ai_response=chat.ai_response,
                context_papers=chat.context_papers,
                context_sentences=chat.context_sentences,
                query_metadata=chat.query_metadata,
                created_at=chat.created_at
            )
            for chat in chats
        ]
        
        logger.debug(f"Retrieved {len(chat_responses)} chats for workspace {workspace.id}")
        
        return ChatHistoryListResponse(
            chats=chat_responses,
            total_count=meta.total,
            page=meta.page,
            page_size=meta.size,
            has_next=meta.has_next,
            has_previous=meta.has_previous
        )
        
    except Exception as e:
        logger.error(f"Failed to get chat history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat history"
        )

@router.get("/{chat_id}", response_model=ChatHistoryResponse)
async def get_chat_by_id(
    chat_id: UUID,
    workspace: Workspace = Depends(get_workspace_for_user),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    獲取特定對話的詳細信息
    
    Args:
        chat_id: 對話ID
        workspace: 工作區對象
        current_user: 當前用戶
        db: 數據庫會話
    
    Returns:
        對話詳細信息
    """
    try:
        stmt = select(ChatHistory).where(
            and_(
                ChatHistory.id == chat_id,
                ChatHistory.workspace_id == workspace.id
            )
        )
        result = await db.execute(stmt)
        chat = result.scalar_one_or_none()
        
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat not found"
            )
        
        logger.debug(f"Retrieved chat {chat_id} for workspace {workspace.id}")
        
        return ChatHistoryResponse(
            id=str(chat.id),
            workspace_id=str(chat.workspace_id),
            user_question=chat.user_question,
            ai_response=chat.ai_response,
            context_papers=chat.context_papers,
            context_sentences=chat.context_sentences,
            query_metadata=chat.query_metadata,
            created_at=chat.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get chat: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat"
        )

@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat(
    chat_id: UUID,
    workspace: Workspace = Depends(get_workspace_for_user),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    刪除特定對話
    
    Args:
        chat_id: 對話ID
        workspace: 工作區對象
        current_user: 當前用戶
        db: 數據庫會話
    """
    try:
        stmt = select(ChatHistory).where(
            and_(
                ChatHistory.id == chat_id,
                ChatHistory.workspace_id == workspace.id
            )
        )
        result = await db.execute(stmt)
        chat = result.scalar_one_or_none()
        
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat not found"
            )
        
        await db.delete(chat)
        await db.commit()
        
        logger.info(f"Deleted chat {chat_id} from workspace {workspace.id}")
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete chat: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete chat"
        )

@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
async def clear_chat_history(
    workspace: Workspace = Depends(get_workspace_for_user),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    confirm: bool = Query(False, description="確認清除所有對話歷史")
):
    """
    清除工作區的所有對話歷史
    
    Args:
        workspace: 工作區對象
        current_user: 當前用戶
        db: 數據庫會話
        confirm: 確認參數，必須設為true才會執行刪除
    """
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must set confirm=true to clear all chat history"
        )
    
    try:
        # 刪除工作區的所有對話歷史
        stmt = select(ChatHistory).where(ChatHistory.workspace_id == workspace.id)
        result = await db.execute(stmt)
        chats = result.scalars().all()
        
        chat_count = len(chats)
        
        for chat in chats:
            await db.delete(chat)
        
        await db.commit()
        
        logger.info(f"Cleared {chat_count} chats from workspace {workspace.id}")
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to clear chat history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear chat history"
        )

@router.get("/stats/summary")
async def get_chat_stats(
    workspace: Workspace = Depends(get_workspace_for_user),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    獲取工作區對話統計信息
    
    Args:
        workspace: 工作區對象
        current_user: 當前用戶
        db: 數據庫會話
    
    Returns:
        對話統計信息
    """
    try:
        from sqlalchemy import func, text
        
        # 總對話數
        total_stmt = select(func.count(ChatHistory.id)).where(
            ChatHistory.workspace_id == workspace.id
        )
        total_result = await db.execute(total_stmt)
        total_chats = total_result.scalar() or 0
        
        # 今日對話數
        today_stmt = select(func.count(ChatHistory.id)).where(
            and_(
                ChatHistory.workspace_id == workspace.id,
                func.date(ChatHistory.created_at) == func.current_date()
            )
        )
        today_result = await db.execute(today_stmt)
        today_chats = today_result.scalar() or 0
        
        # 最近對話時間
        latest_stmt = select(func.max(ChatHistory.created_at)).where(
            ChatHistory.workspace_id == workspace.id
        )
        latest_result = await db.execute(latest_stmt)
        latest_chat_time = latest_result.scalar()
        
        stats = {
            "workspace_id": str(workspace.id),
            "total_chats": total_chats,
            "today_chats": today_chats,
            "latest_chat_time": latest_chat_time.isoformat() if latest_chat_time else None,
        }
        
        logger.debug(f"Retrieved chat stats for workspace {workspace.id}")
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get chat stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat statistics"
        ) 