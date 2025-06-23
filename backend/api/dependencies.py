"""
FastAPI依賴項模組
提供可重用的身份驗證和授權檢查
"""

from fastapi import Depends, HTTPException, status, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, Dict, Any
from uuid import UUID
import uuid

from ..core.security import verify_token
from ..core.database import get_db
from ..models.user import User, Workspace
from ..core.logging import get_logger
from ..core.config import settings
from backend.services.db_service import db_service

logger = get_logger(__name__)

class OptionalHTTPBearer(HTTPBearer):
    """可選的 HTTP Bearer 認證，在開發模式下允許無認證請求"""
    
    async def __call__(self, request: Request) -> Optional[HTTPAuthorizationCredentials]:
        try:
            return await super().__call__(request)
        except HTTPException:
            # 在開發模式下，如果沒有認證標頭，返回 None 而不是拋出異常
            if settings.debug:
                return None
            raise

# 使用可選的安全依賴
optional_security = OptionalHTTPBearer()

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
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
    
    # 開發模式：總是使用第一個可用用戶進行認證繞過
    if settings.debug:
        logger.warning("🚨 開發模式：使用預設用戶進行認證繞過")
        try:
            # 獲取第一個可用用戶
            stmt = select(User).limit(1)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if user:
                logger.info(f"🚨 開發模式：使用用戶 {user.email} 進行認證繞過")
                return user
            else:
                logger.error("開發模式：資料庫中沒有可用用戶")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="No users available in development mode"
                )
        except Exception as e:
            logger.error(f"開發模式認證繞過失敗: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Development authentication bypass failed"
            )
    
    # 生產模式或有 credentials 時的正常認證流程
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
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
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Workspace:
    """
    獲取屬於當前用戶的工作區
    
    Args:
        workspace_id: 工作區ID
        current_user: 當前用戶（開發模式下可能為None）
        db: 數據庫會話
    
    Returns:
        工作區對象
    
    Raises:
        HTTPException: 當工作區不存在或無權限時
    """
    try:
        # 開發模式：如果沒有用戶，直接返回工作區（如果存在）
        if settings.debug and current_user is None:
            logger.warning(f"🚨 開發模式：無認證用戶嘗試存取工作區 {workspace_id}")
            stmt = select(Workspace).where(Workspace.id == workspace_id)
            result = await db.execute(stmt)
            workspace = result.scalar_one_or_none()
            
            if workspace:
                logger.info(f"🚨 開發模式：允許無認證存取工作區 {workspace_id}")
                return workspace
            else:
                logger.error(f"開發模式：工作區 {workspace_id} 不存在")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Workspace not found"
                )
        
        # 正常模式：需要有效用戶
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
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
                # 開發模式：允許存取其他用戶的工作區
                if settings.debug:
                    logger.warning(f"🚨 開發模式：允許用戶 {current_user.id} 存取工作區 {workspace_id} (屬於 {workspace_exists.user_id})")
                    return workspace_exists
                
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
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
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

def get_workspace_access_dependency():
    """
    創建工作區存取權限檢查依賴
    返回一個依賴函數，用於驗證當前用戶對指定工作區的存取權限
    """
    async def verify_workspace_access(
        workspace_id: str = Query(..., description="工作區ID"),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
    ) -> Dict[str, Any]:
        """
        驗證用戶對工作區的存取權限
        
        Args:
            workspace_id: 工作區ID
            db: 資料庫會話
            current_user: 當前用戶
            
        Returns:
            工作區存取資訊
            
        Raises:
            HTTPException: 當工作區不存在或用戶無權存取時
        """
        try:
            # 驗證工作區ID格式
            workspace_uuid = uuid.UUID(workspace_id)
            
            # 檢查用戶對工作區的存取權限
            has_access = await db_service.verify_workspace_access(
                db, current_user.id, workspace_uuid
            )
            
            if not has_access:
                logger.warning(f"用戶 {current_user.id} 嘗試存取無權限的工作區 {workspace_id}")
                raise HTTPException(
                    status_code=403,
                    detail=f"您沒有存取工作區 {workspace_id} 的權限"
                )
            
            # 獲取工作區詳細資訊
            workspace = await db_service.get_workspace_by_id(db, workspace_uuid)
            if not workspace:
                raise HTTPException(
                    status_code=404,
                    detail=f"工作區 {workspace_id} 不存在"
                )
            
            logger.debug(f"用戶 {current_user.id} 通過工作區 {workspace_id} 權限驗證")
            
            return {
                'workspace_id': workspace_id,
                'workspace_name': workspace.name,
                'user_id': str(current_user.id),
                'access_level': 'owner' if str(workspace.user_id) == str(current_user.id) else 'member',
                'verified_at': uuid.uuid4().hex  # 用於追蹤驗證會話
            }
            
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="無效的工作區ID格式"
            )
        except HTTPException:
            # 重新拋出 HTTP 異常
            raise
        except Exception as e:
            logger.error(f"工作區權限驗證失敗: user={current_user.id}, workspace={workspace_id}, error={str(e)}")
            raise HTTPException(
                status_code=500,
                detail="工作區權限驗證失敗"
            )
    
    return verify_workspace_access

# 建立常用的工作區權限依賴實例
workspace_access_dependency = get_workspace_access_dependency()

async def require_workspace_owner(
    workspace_access: Dict[str, Any] = Depends(workspace_access_dependency)
) -> Dict[str, Any]:
    """
    要求用戶是工作區擁有者
    
    Args:
        workspace_access: 工作區存取資訊
        
    Returns:
        工作區存取資訊
        
    Raises:
        HTTPException: 當用戶不是工作區擁有者時
    """
    if workspace_access.get('access_level') != 'owner':
        raise HTTPException(
            status_code=403,
            detail="只有工作區擁有者可以執行此操作"
        )
    
    return workspace_access

async def get_current_workspace_id(
    workspace_access: Dict[str, Any] = Depends(workspace_access_dependency)
) -> str:
    """
    獲取當前經過驗證的工作區ID
    
    Args:
        workspace_access: 工作區存取資訊
        
    Returns:
        工作區ID
    """
    return workspace_access['workspace_id']

async def get_workspace_context(
    workspace_access: Dict[str, Any] = Depends(workspace_access_dependency)
) -> Dict[str, Any]:
    """
    獲取完整的工作區上下文資訊
    
    Args:
        workspace_access: 工作區存取資訊
        
    Returns:
        工作區上下文
    """
    return {
        'workspace_id': workspace_access['workspace_id'],
        'workspace_name': workspace_access['workspace_name'],
        'user_id': workspace_access['user_id'],
        'access_level': workspace_access['access_level'],
        'is_owner': workspace_access['access_level'] == 'owner'
    } 