from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from typing import AsyncGenerator
import os
from .config import settings

# 建立資料庫引擎
async_engine = create_async_engine(
    settings.async_database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=10,
    max_overflow=20
)

# 建立AsyncSession工廠
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=True,
    autocommit=False
)

# 基礎模型類
Base = declarative_base()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    資料庫依賴注入函數
    用於FastAPI路由中獲取資料庫session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_database():
    """初始化資料庫連線"""
    try:
        # 測試連線
        async with async_engine.begin() as conn:
            # 這裡可以加入建立表格的邏輯
            # await conn.run_sync(Base.metadata.create_all)
            pass
        print("資料庫連線初始化成功")
    except Exception as e:
        print(f"資料庫連線初始化失敗: {e}")
        raise

async def close_database():
    """關閉資料庫連線"""
    try:
        await async_engine.dispose()
        print("資料庫連線已關閉")
    except Exception as e:
        print(f"關閉資料庫連線時發生錯誤: {e}") 
from sqlalchemy.orm import declarative_base
from typing import AsyncGenerator
import os
from .config import settings

# 建立資料庫引擎
async_engine = create_async_engine(
    settings.async_database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=10,
    max_overflow=20
)

# 建立AsyncSession工廠
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=True,
    autocommit=False
)

# 基礎模型類
Base = declarative_base()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    資料庫依賴注入函數
    用於FastAPI路由中獲取資料庫session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_database():
    """初始化資料庫連線"""
    try:
        # 測試連線
        async with async_engine.begin() as conn:
            # 這裡可以加入建立表格的邏輯
            # await conn.run_sync(Base.metadata.create_all)
            pass
        print("資料庫連線初始化成功")
    except Exception as e:
        print(f"資料庫連線初始化失敗: {e}")
        raise

async def close_database():
    """關閉資料庫連線"""
    try:
        await async_engine.dispose()
        print("資料庫連線已關閉")
    except Exception as e:
        print(f"關閉資料庫連線時發生錯誤: {e}") 