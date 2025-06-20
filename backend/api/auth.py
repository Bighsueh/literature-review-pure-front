"""
身份驗證API端點
處理Google OAuth登入流程和JWT令牌管理
"""

import os
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from datetime import timedelta

from ..core.database import get_db
from ..core.security import (
    create_access_token, 
    exchange_code_for_token, 
    get_google_user_info, 
    get_authorization_url,
    JWT_EXPIRE_HOURS,
    get_current_user
)
from ..models.user import User, UserCreate, UserResponse
from ..core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/auth", tags=["authentication"])

# 請求和響應模型
class GoogleAuthRequest(BaseModel):
    """Google OAuth授權請求"""
    redirect_uri: str
    state: Optional[str] = None

class GoogleCallbackRequest(BaseModel):
    """Google OAuth回調請求"""
    code: str
    redirect_uri: str
    state: Optional[str] = None

class TokenResponse(BaseModel):
    """JWT令牌響應"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse

@router.get("/google/url")
async def get_google_auth_url():
    """
    生成Google OAuth授權URL
    
    Returns:
        Google OAuth授權URL
    """
    try:
        from ..core.config import get_settings
        settings = get_settings()
        
        # 檢查OAuth配置
        if not settings.validate_oauth_config():
            oauth_status = settings.get_oauth_status()
            logger.error(f"Google OAuth配置不完整: {oauth_status}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google OAuth not configured properly. Missing CLIENT_ID or CLIENT_SECRET."
            )
        
        authorization_url = get_authorization_url()
        logger.info(f"Generated Google OAuth URL")
        
        return {
            "authorization_url": authorization_url,
            "message": "Please visit the authorization URL to complete login"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate Google OAuth URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate OAuth flow"
        )

@router.get("/google/callback")
async def google_callback_get(
    code: str,
    state: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    處理Google OAuth回調 (GET 請求)
    
    Args:
        code: Google OAuth 授權碼
        state: 可選的狀態參數
        db: 數據庫會話
    
    Returns:
        重定向到前端並附帶 JWT 令牌
    """
    try:
        # 1. 將授權碼交換為訪問令牌
        token_data = await exchange_code_for_token(code)
        access_token = token_data.get("access_token")
        
        # 2. 使用訪問令牌獲取用戶信息
        google_user = await get_google_user_info(access_token)
        
        # 3. 查找或創建用戶
        user = await get_or_create_user(db, google_user)
        
        # 4. 創建JWT令牌
        jwt_data = {
            "sub": str(user.id),
            "email": user.email
        }
        jwt_token = create_access_token(jwt_data)
        
        logger.info(f"User successfully authenticated via GET callback: {user.email}")
        
        # 5. 重定向到前端並附帶令牌和用戶信息
        from urllib.parse import urlencode
        from ..core.config import get_settings
        settings = get_settings()
        
        # 構建用戶數據
        user_data = UserResponse.from_orm(user)
        
        # 構建重定向 URL 參數
        redirect_params = {
            'token': jwt_token,
            'user': user_data.json()
        }
        
        # 重定向到前端 URL（添加令牌和用戶信息作為查詢參數）
        redirect_url = f"{settings.frontend_url}?{urlencode(redirect_params)}"
        
        return RedirectResponse(url=redirect_url)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth GET callback processing failed: {e}")
        
        # 重定向到前端並附帶錯誤信息
        from urllib.parse import urlencode
        from ..core.config import get_settings
        settings = get_settings()
        
        error_params = {
            'error': 'authentication_failed',
            'message': 'Failed to complete Google login'
        }
        
        redirect_url = f"{settings.frontend_url}?{urlencode(error_params)}"
        return RedirectResponse(url=redirect_url)

@router.post("/google/callback", response_model=TokenResponse)
async def google_callback(
    callback_data: GoogleCallbackRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    處理Google OAuth回調
    
    Args:
        callback_data: 包含授權碼的回調數據
        db: 數據庫會話
    
    Returns:
        JWT令牌和用戶信息
    """
    try:
        # 1. 將授權碼交換為訪問令牌
        token_data = await exchange_code_for_token(callback_data.code)
        access_token = token_data.get("access_token")
        
        # 2. 使用訪問令牌獲取用戶信息
        google_user = await get_google_user_info(access_token)
        
        # 3. 查找或創建用戶
        user = await get_or_create_user(db, google_user)
        
        # 4. 創建JWT令牌
        jwt_data = {
            "sub": str(user.id),
            "email": user.email
        }
        jwt_token = create_access_token(jwt_data)
        
        logger.info(f"User successfully authenticated: {user.email}")
        
        return TokenResponse(
            access_token=jwt_token,
            expires_in=JWT_EXPIRE_HOURS * 3600,  # 轉換為秒
            user=UserResponse.from_orm(user)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth callback processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        )

@router.post("/refresh")
async def refresh_token(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    刷新JWT令牌
    
    Args:
        current_user: 當前認證的用戶
    
    Returns:
        新的JWT令牌
    """
    try:
        # 創建新的JWT令牌
        jwt_data = {
            "sub": str(current_user.id),
            "email": current_user.email
        }
        jwt_token = create_access_token(jwt_data)
        
        logger.debug(f"Token refreshed for user: {current_user.email}")
        
        return TokenResponse(
            access_token=jwt_token,
            expires_in=JWT_EXPIRE_HOURS * 3600,
            user=UserResponse.from_orm(current_user)
        )
        
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )

@router.post("/logout")
async def logout():
    """
    用戶登出
    
    Note: 由於JWT是無狀態的，實際的登出邏輯在前端實現（刪除本地存儲的令牌）
    """
    return {"message": "Logged out successfully"}

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    獲取當前用戶信息
    
    Args:
        current_user: 當前認證的用戶
    
    Returns:
        當前用戶的詳細信息
    """
    return UserResponse.from_orm(current_user)

@router.get("/status")
async def get_auth_status():
    """
    獲取認證服務狀態和配置信息
    
    Returns:
        認證配置狀態
    """
    from ..core.config import get_settings
    settings = get_settings()
    
    oauth_status = settings.get_oauth_status()
    
    return {
        "service": "Authentication Service",
        "status": "healthy" if oauth_status["google_oauth_configured"] else "misconfigured",
        "oauth_configuration": oauth_status,
        "endpoints": {
            "google_auth_url": "/api/auth/google/url",
            "google_callback": "/api/auth/google/callback",
            "refresh_token": "/api/auth/refresh",
            "logout": "/api/auth/logout",
            "user_info": "/api/auth/me"
        }
    }

# 輔助函數
async def get_or_create_user(db: AsyncSession, google_user: Dict[str, Any]) -> User:
    """
    根據Google用戶信息查找或創建用戶
    
    Args:
        db: 數據庫會話
        google_user: Google用戶信息字典
    
    Returns:
        用戶對象
    """
    # 添加調試日誌
    logger.info(f"處理Google用戶數據: {google_user}")
    
    # 從字典中提取數據（Google OAuth v2 userinfo API 格式）
    google_id = google_user.get('id')
    email = google_user.get('email') 
    name = google_user.get('name')
    picture_url = google_user.get('picture')
    
    # 檢查必要欄位
    if not google_id or not email:
        logger.error(f"Google用戶數據缺少必要欄位: id={google_id}, email={email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google用戶數據不完整"
        )
    
    # 首先嘗試根據Google ID查找用戶
    stmt = select(User).where(User.google_id == google_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user:
        # 更新用戶信息（以防用戶在Google更改了資料）
        user.email = email
        user.name = name or user.name  # 保留原名稱如果 Google 沒有提供
        user.picture_url = picture_url or user.picture_url  # 保留原頭像如果 Google 沒有提供
        await db.commit()
        await db.refresh(user)
        logger.debug(f"Updated existing user: {user.email}")
        return user
    
    # 檢查是否有相同email的用戶（可能是舊系統遷移的情況）
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        # 更新現有用戶的Google ID
        existing_user.google_id = google_id
        existing_user.name = name or existing_user.name
        existing_user.picture_url = picture_url or existing_user.picture_url
        await db.commit()
        await db.refresh(existing_user)
        logger.info(f"Linked existing user with Google account: {existing_user.email}")
        return existing_user
    
    # 創建新用戶
    user_data = UserCreate(
        google_id=google_id,
        email=email,
        name=name or "Google User",  # 如果沒有名稱，提供預設值
        picture_url=picture_url
    )
    
    new_user = User(**user_data.dict())
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    logger.info(f"Created new user: {new_user.email}")
    return new_user 