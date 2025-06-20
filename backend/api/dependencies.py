"""
FastAPI依賴項模組
提供可重用的身份驗證和授權檢查
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from uuid import UUID

from ..core.security import security, verify_token
from ..core.database import get_db
from ..models.user import User, Workspace
from ..core.logging import get_logger

logger = get_logger(__name__)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    獲取當前已認證的用戶
    
    Args:
        credentials: HTTP授權憑證
        db: 數據庫會話
    
    Returns:
        當前用戶對象
    
    Raises:
        HTTPException: 當認證失敗時
    """
    # 驗證JWT令牌
    token_data = verify_token(credentials.credentials)
    
    if token_data is None:
        logger.warning("Invalid JWT token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 從字典中獲取用戶ID（JWT 標準使用 'sub' 欄位）
    user_id_str = token_data.get("sub")
    if not user_id_str:
        logger.warning("No 'sub' field in JWT token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        user_id = UUID(user_id_str)
    except ValueError:
        logger.warning(f"Invalid user ID format in token: {user_id_str}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 從數據庫獲取用戶信息
    try:
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user is None:
            logger.warning(f"User not found in database: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        logger.debug(f"Current user authenticated: {user.email}")
        return user
        
    except Exception as e:
        logger.error(f"Database error when fetching user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error"
        )

async def get_workspace_for_user(
    workspace_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Workspace:
    """
    獲取屬於當前用戶的工作區
    
    Args:
        workspace_id: 工作區ID
        current_user: 當前用戶
        db: 數據庫會話
    
    Returns:
        工作區對象
    
    Raises:
        HTTPException: 當工作區不存在或無權限時
    """
    try:
        # 查詢工作區
        stmt = select(Workspace).where(
            Workspace.id == workspace_id,
            Workspace.user_id == current_user.id
        )
        result = await db.execute(stmt)
        workspace = result.scalar_one_or_none()
        
        if workspace is None:
            # 檢查工作區是否存在但不屬於當前用戶
            stmt_exists = select(Workspace).where(Workspace.id == workspace_id)
            result_exists = await db.execute(stmt_exists)
            workspace_exists = result_exists.scalar_one_or_none()
            
            if workspace_exists:
                logger.warning(f"User {current_user.id} attempted to access workspace {workspace_id} owned by {workspace_exists.user_id}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to access this workspace"
                )
            else:
                logger.warning(f"Workspace not found: {workspace_id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Workspace not found"
                )
        
        logger.debug(f"Workspace {workspace_id} authorized for user {current_user.id}")
        return workspace
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database error when fetching workspace: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authorization service error"
        )

async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    獲取可選的當前用戶（用於支持匿名訪問的端點）
    
    Args:
        credentials: 可選的HTTP授權憑證
        db: 數據庫會話
    
    Returns:
        當前用戶對象或None
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        # 忽略認證錯誤，返回None表示匿名用戶
        return None 