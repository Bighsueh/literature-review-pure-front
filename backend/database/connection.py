"""
資料庫連線管理模組
提供PostgreSQL連線池和異步資料庫操作
"""

import os
import asyncio
from typing import Optional, AsyncGenerator
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool
import asyncpg
import logging

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SQLAlchemy Base
Base = declarative_base()

class DatabaseManager:
    def __init__(self):
        self.database_url = self._get_database_url()
        self.async_database_url = self._get_async_database_url()
        self.engine = None
        self.async_engine = None
        self.async_session_maker = None
        self.session_maker = None
        
    def _get_database_url(self) -> str:
        """取得資料庫連線URL"""
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        database = os.getenv("POSTGRES_DB", "paper_analysis")
        username = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "password")
        
        return f"postgresql://{username}:{password}@{host}:{port}/{database}"
    
    def _get_async_database_url(self) -> str:
        """取得異步資料庫連線URL"""
        return self.database_url.replace("postgresql://", "postgresql+asyncpg://")
    
    async def initialize(self):
        """初始化資料庫連線"""
        try:
            # 建立異步引擎
            self.async_engine = create_async_engine(
                self.async_database_url,
                echo=False,  # 生產環境設為False
                pool_pre_ping=True,
                pool_recycle=3600,
                pool_size=10,
                max_overflow=20,
                poolclass=NullPool if os.getenv("TESTING") else None
            )
            
            # 建立異步session maker
            self.async_session_maker = async_sessionmaker(
                self.async_engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # 建立同步引擎（用於初始化）
            self.engine = create_engine(
                self.database_url,
                pool_pre_ping=True,
                pool_recycle=3600
            )
            
            self.session_maker = sessionmaker(bind=self.engine)
            
            logger.info("資料庫連線初始化成功")
            
        except Exception as e:
            logger.error(f"資料庫連線初始化失敗: {e}")
            raise
    
    async def create_tables(self):
        """建立資料庫表格（使用Alembic migration）"""
        logger.info("🚨 CREATE_TABLES 方法被調用！開始執行...")
        try:
            logger.info("📋 執行Alembic遷移...")
            
            # 使用Alembic配置執行遷移
            from alembic.config import Config
            from alembic import command
            import tempfile
            import os
            
            # 取得migration目錄路徑
            backend_dir = os.path.dirname(os.path.dirname(__file__))
            migrations_dir = os.path.join(backend_dir, "migrations")
            alembic_ini_path = os.path.join(backend_dir, "alembic.ini")
            
            logger.info(f"🔍 檢查Alembic設定檔案...")
            logger.info(f"  - backend_dir: {backend_dir}")
            logger.info(f"  - migrations_dir: {migrations_dir}")
            logger.info(f"  - alembic_ini_path: {alembic_ini_path}")
            
            if not os.path.exists(alembic_ini_path):
                logger.error(f"找不到alembic.ini檔案: {alembic_ini_path}")
                raise FileNotFoundError(f"找不到alembic.ini檔案: {alembic_ini_path}")
            
            if not os.path.exists(migrations_dir):
                logger.error(f"找不到migrations目錄: {migrations_dir}")
                raise FileNotFoundError(f"找不到migrations目錄: {migrations_dir}")
            
            # 建立Alembic配置
            logger.info("🔧 建立Alembic配置...")
            alembic_cfg = Config(alembic_ini_path)
            logger.info(f"📝 設定資料庫URL: {self.database_url}")
            alembic_cfg.set_main_option("sqlalchemy.url", self.database_url)
            
            # 確保資料庫有alembic_version表，如果沒有則建立
            try:
                logger.info("🔍 檢查migration狀態...")
                # 檢查是否需要初始化alembic_version表
                from alembic.migration import MigrationContext
                from alembic.operations import Operations
                
                with self.engine.connect() as connection:
                    logger.info("✅ 資料庫連線成功，建立migration context...")
                    context = MigrationContext.configure(connection)
                    
                    # 檢查是否已有migration記錄
                    current_rev = context.get_current_revision()
                    logger.info(f"📊 目前migration版本: {current_rev}")
                    
                    if current_rev is None:
                        logger.info("�� 初始化Alembic版本控制...")
                        # 標記為已執行最新migration
                        command.stamp(alembic_cfg, "head")
                        logger.info("✅ Alembic版本控制初始化完成")
                    else:
                        logger.info(f"📋 發現現有migration版本: {current_rev}")
                        
                    # 執行migration到最新版本
                    logger.info("⬆️ 執行migration到最新版本...")
                    command.upgrade(alembic_cfg, "head")
                    logger.info("✅ Migration執行完成")
                    
            except Exception as migration_error:
                logger.error(f"❌ Alembic遷移失敗: {migration_error}")
                logger.error(f"❌ 錯誤類型: {type(migration_error).__name__}")
                logger.error(f"❌ 錯誤詳情: {str(migration_error)}")
                import traceback
                logger.error(f"❌ 完整堆疊追蹤:")
                logger.error(traceback.format_exc())
                logger.info("🔄 回退到schema.sql方式...")
                
                # 如果migration失敗，回退到原來的schema.sql方式
                await self._create_tables_from_schema()
                
            logger.info("✅ 資料庫表格建立成功")
            
        except Exception as e:
            logger.error(f"❌ 建立資料庫表格失敗: {e}")
            logger.error(f"❌ 錯誤類型: {type(e).__name__}")
            import traceback
            logger.error(f"❌ 完整堆疊追蹤:")
            logger.error(traceback.format_exc())
            raise

    async def _create_tables_from_schema(self):
        """從schema.sql建立資料庫表格（備用方法）"""
        try:
            logger.info("📋 執行主要資料庫schema...")
            
            # 讀取schema.sql檔案
            schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
            logger.info(f"SQL檔案執行中: {schema_path}")
            
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            
            # 替換CREATE TABLE為CREATE TABLE IF NOT EXISTS
            schema_sql = schema_sql.replace("CREATE TABLE ", "CREATE TABLE IF NOT EXISTS ")
            
            # 執行schema
            async with self.async_engine.begin() as conn:
                # 分割SQL語句並執行
                statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
                
                for statement in statements:
                    if statement:
                        try:
                            await conn.execute(text(statement))
                        except Exception as stmt_error:
                            # 忽略已存在的表格錯誤，但記錄其他錯誤
                            if "already exists" not in str(stmt_error):
                                logger.warning(f"執行SQL語句時發生錯誤: {stmt_error}")
                                logger.debug(f"出錯的SQL語句: {statement}")
                            
            logger.info("✅ Schema.sql執行完成")
            
        except Exception as e:
            logger.error(f"執行schema.sql失敗: {e}")
            raise
    
    async def check_connection(self) -> bool:
        """檢查資料庫連線狀態"""
        try:
            session = self.async_session_maker()
            async with session:
                result = await session.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception as e:
            logger.error(f"資料庫連線檢查失敗: {e}")
            return False
    
    async def get_async_session(self) -> AsyncSession:
        """取得異步資料庫session"""
        if not self.async_session_maker:
            await self.initialize()
        
        return self.async_session_maker()
    
    def get_session(self):
        """取得同步資料庫session"""
        if not self.session_maker:
            raise RuntimeError("資料庫未初始化")
        return self.session_maker()
    
    async def close(self):
        """關閉資料庫連線"""
        if self.async_engine:
            await self.async_engine.dispose()
        if self.engine:
            self.engine.dispose()
        
        logger.info("資料庫連線已關閉")

# 全域資料庫管理器實例
db_manager = DatabaseManager()

async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI依賴注入：取得異步資料庫session"""
    async with db_manager.get_async_session() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"資料庫操作錯誤: {e}")
            raise
        finally:
            await session.close()

def get_db():
    """FastAPI依賴注入：取得同步資料庫session"""
    db = db_manager.get_session()
    try:
        yield db
    except Exception as e:
        db.rollback()
        logger.error(f"資料庫操作錯誤: {e}")
        raise
    finally:
        db.close()

async def init_database():
    """初始化資料庫（用於應用啟動時）"""
    try:
        await db_manager.initialize()
        await db_manager.create_tables()
        
        # 檢查連線
        if await db_manager.check_connection():
            logger.info("資料庫初始化完成並連線成功")
        else:
            raise ConnectionError("資料庫連線失敗")
            
    except Exception as e:
        logger.error(f"資料庫初始化失敗: {e}")
        raise

async def close_database():
    """關閉資料庫連線（用於應用關閉時）"""
    await db_manager.close()

# 用於測試的工具函數
async def reset_database():
    """重設資料庫（僅用於測試）"""
    if not os.getenv("TESTING"):
        raise RuntimeError("只能在測試環境中重設資料庫")
    
    async with db_manager.async_engine.begin() as conn:
        # 刪除所有表格
        await conn.execute(text("""
            DROP SCHEMA public CASCADE;
            CREATE SCHEMA public;
            GRANT ALL ON SCHEMA public TO postgres;
            GRANT ALL ON SCHEMA public TO public;
        """))
    
    # 重新建立表格
    await db_manager.create_tables()
    logger.info("測試資料庫已重設")

if __name__ == "__main__":
    # 測試資料庫連線
    async def test_connection():
        await init_database()
        
        # 測試基本查詢
        async with db_manager.get_async_session() as session:
            result = await session.execute(text("SELECT COUNT(*) FROM papers"))
            count = result.scalar()
            print(f"Papers table count: {count}")
        
        await close_database()
    
    asyncio.run(test_connection()) 