"""
安全性模組
處理JWT令牌、Google OAuth認證等安全相關功能
"""

import os
import httpx
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .config import settings
from .database import get_db
from .logging import get_logger

logger = get_logger(__name__)

# JWT 設定
JWT_SECRET_KEY = settings.jwt_secret_key
JWT_ALGORITHM = settings.jwt_algorithm
JWT_EXPIRE_HOURS = settings.jwt_expire_hours

# Google OAuth 設定
GOOGLE_CLIENT_ID = settings.google_client_id
GOOGLE_CLIENT_SECRET = settings.google_client_secret
GOOGLE_REDIRECT_URI = settings.google_redirect_uri

# HTTP Bearer token 檢查器
security = HTTPBearer()

def create_access_token(data: dict) -> str:
    """
    建立JWT存取令牌
    
    Args:
        data: 要編碼的資料字典
        
    Returns:
        JWT令牌字串
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS)
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    
    try:
        encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        logger.debug(f"JWT令牌已建立，過期時間: {expire}")
        return encoded_jwt
    except Exception as e:
        logger.error(f"JWT令牌建立失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="令牌建立失敗"
        )

def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    驗證JWT令牌
    
    Args:
        token: JWT令牌字串
        
    Returns:
        解碼後的令牌資料，如果無效則返回None
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        
        # 檢查令牌是否過期
        exp = payload.get("exp")
        if exp and datetime.utcfromtimestamp(exp) < datetime.utcnow():
            logger.warning("JWT令牌已過期")
            return None
            
        return payload
    except JWTError as e:
        logger.warning(f"JWT令牌驗證失敗: {e}")
        return None
    except Exception as e:
        logger.error(f"令牌驗證時發生意外錯誤: {e}")
        return None

def get_authorization_url() -> str:
    """
    生成Google OAuth 2.0授權URL
    
    Returns:
        Google OAuth授權URL
    """
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth未正確配置"
        )
    
    base_url = "https://accounts.google.com/o/oauth2/v2/auth"
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "scope": "openid email profile",
        "response_type": "code",
        "access_type": "offline",
        "prompt": "consent"
    }
    
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    authorization_url = f"{base_url}?{query_string}"
    
    logger.info(f"生成Google OAuth授權URL: {authorization_url}")
    return authorization_url

async def exchange_code_for_token(code: str) -> Dict[str, Any]:
    """
    用授權碼換取Google存取令牌
    
    Args:
        code: Google OAuth授權碼
        
    Returns:
        包含存取令牌的字典
    """
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth未正確配置"
        )
    
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": GOOGLE_REDIRECT_URI
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data)
            response.raise_for_status()
            token_data = response.json()
            
        logger.info("成功獲取Google存取令牌")
        return token_data
        
    except httpx.HTTPError as e:
        logger.error(f"獲取Google令牌失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"獲取Google令牌失敗: {str(e)}"
        )

async def get_google_user_info(access_token: str) -> Dict[str, Any]:
    """
    使用Google存取令牌獲取使用者資訊
    
    Args:
        access_token: Google存取令牌
        
    Returns:
        使用者資訊字典
    """
    user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(user_info_url, headers=headers)
            response.raise_for_status()
            user_info = response.json()
            
        logger.info(f"成功獲取Google使用者資訊: {user_info.get('email', 'unknown')}")
        return user_info
        
    except httpx.HTTPError as e:
        logger.error(f"獲取Google使用者資訊失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"獲取使用者資訊失敗: {str(e)}"
        )

async def get_current_user(
    token: str = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """
    從JWT令牌獲取當前使用者
    
    Args:
        token: HTTP Bearer令牌
        db: 資料庫會話
        
    Returns:
        當前使用者物件
        
    Raises:
        HTTPException: 如果令牌無效或使用者不存在
    """
    # 提取Bearer令牌
    if not token.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供認證令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 驗證JWT令牌
    payload = verify_token(token.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無效的認證令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 獲取使用者ID
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌中缺少使用者ID",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 從資料庫查詢使用者
    try:
        from ..models.user import User  # 延遲導入避免循環引用
        
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="使用者不存在",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        logger.debug(f"成功驗證使用者: {user.email}")
        return user
        
    except Exception as e:
        logger.error(f"獲取當前使用者失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="獲取使用者資訊失敗"
        )

def generate_secure_secret_key() -> str:
    """
    生成安全的密鑰（用於開發時的建議）
    
    Returns:
        安全的密鑰字串
    """
    import secrets
    return secrets.token_urlsafe(32)

# 用於測試的函數
def test_token_functions():
    """測試JWT令牌功能"""
    test_data = {"sub": "test-user", "email": "test@example.com"}
    
    # 建立令牌
    token = create_access_token(test_data)
    print(f"建立的令牌: {token}")
    
    # 驗證令牌
    payload = verify_token(token)
    print(f"驗證結果: {payload}")
    
    return token, payload

if __name__ == "__main__":
    # 測試功能
    print("🔐 測試JWT令牌功能...")
    test_token_functions()
    
    print("\n🔑 生成安全密鑰建議:")
    print(f"JWT_SECRET_KEY={generate_secure_secret_key()}")
    print(f"SECRET_KEY={generate_secure_secret_key()}") 