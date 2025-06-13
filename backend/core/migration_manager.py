"""
資料庫遷移管理器
自動檢查和執行 Alembic 遷移
"""

import os
import asyncio
from pathlib import Path
from typing import List, Optional
from sqlalchemy import text, inspect
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from alembic.config import Config
from alembic import command
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory

from .logging import get_logger
from .config import settings

logger = get_logger(__name__)


def get_database_url() -> str:
    """取得資料庫連接字串"""
    return settings.async_database_url


class MigrationManager:
    """資料庫遷移管理器"""
    
    def __init__(self):
        self.backend_dir = Path(__file__).parent.parent
        self.alembic_ini_path = self.backend_dir / "alembic.ini"
        self.migrations_dir = self.backend_dir / "migrations"
        
    def get_alembic_config(self) -> Config:
        """取得 Alembic 設定"""
        if not self.alembic_ini_path.exists():
            raise FileNotFoundError(f"Alembic 設定檔案不存在: {self.alembic_ini_path}")
            
        config = Config(str(self.alembic_ini_path))
        # 使用環境變數或預設的資料庫連接
        db_url = get_database_url().replace("+asyncpg", "")  # Alembic 需要同步連接
        config.set_main_option("sqlalchemy.url", db_url)
        
        # 設定正確的 migrations 目錄路徑
        config.set_main_option("script_location", str(self.migrations_dir))
        
        return config
    
    async def check_database_exists(self) -> bool:
        """檢查資料庫是否存在"""
        try:
            db_url = get_database_url()
            engine = create_async_engine(db_url, echo=False)
            
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
                
            await engine.dispose()
            return True
            
        except Exception as e:
            logger.warning(f"資料庫連接檢查失敗: {e}")
            return False
    
    async def check_tables_exist(self) -> dict:
        """檢查必要的表格是否存在"""
        required_tables = [
            'papers', 'paper_sections', 'sentences', 
            'paper_selections', 'processing_queue', 'system_settings'
        ]
        
        try:
            db_url = get_database_url()
            engine = create_async_engine(db_url, echo=False)
            
            async with engine.begin() as conn:
                # 取得所有表格名稱
                result = await conn.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """))
                existing_tables = {row[0] for row in result.fetchall()}
                
            await engine.dispose()
            
            table_status = {}
            for table in required_tables:
                table_status[table] = table in existing_tables
                
            return table_status
            
        except Exception as e:
            logger.error(f"檢查表格存在性失敗: {e}")
            return {table: False for table in required_tables}
    
    async def check_columns_exist(self) -> dict:
        """檢查關鍵欄位是否存在"""
        try:
            db_url = get_database_url()
            engine = create_async_engine(db_url, echo=False)
            
            column_checks = {}
            
            async with engine.begin() as conn:
                # 檢查 papers.od_cd_processed 欄位
                result = await conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'papers' AND column_name = 'od_cd_processed'
                """))
                rows = result.fetchall()
                column_checks['papers.od_cd_processed'] = len(rows) > 0
                
                # 檢查 sentences 表的擴展欄位
                for column in ['detection_status', 'error_message', 'retry_count', 'explanation']:
                    result = await conn.execute(text(f"""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = 'sentences' AND column_name = '{column}'
                    """))
                    rows = result.fetchall()
                    column_checks[f'sentences.{column}'] = len(rows) > 0
                
            await engine.dispose()
            return column_checks
            
        except Exception as e:
            logger.error(f"檢查欄位存在性失敗: {e}")
            return {}
    
    def get_current_revision(self) -> Optional[str]:
        """取得當前資料庫的遷移版本"""
        try:
            config = self.get_alembic_config()
            
            # 建立同步引擎來檢查遷移版本
            from sqlalchemy import create_engine
            db_url = get_database_url().replace("+asyncpg", "")
            engine = create_engine(db_url)
            
            with engine.connect() as connection:
                context = MigrationContext.configure(connection)
                current_rev = context.get_current_revision()
                
            engine.dispose()
            return current_rev
            
        except Exception as e:
            logger.warning(f"無法取得當前遷移版本: {e}")
            return None
    
    def get_head_revision(self) -> Optional[str]:
        """取得最新的遷移版本"""
        try:
            config = self.get_alembic_config()
            script_dir = ScriptDirectory.from_config(config)
            return script_dir.get_current_head()
            
        except Exception as e:
            logger.error(f"無法取得最新遷移版本: {e}")
            return None
    
    def run_migrations(self) -> bool:
        """執行遷移"""
        try:
            config = self.get_alembic_config()
            
            logger.info("開始執行資料庫遷移...")
            command.upgrade(config, "head")
            logger.info("資料庫遷移完成")
            
            return True
            
        except Exception as e:
            logger.error(f"執行遷移失敗: {e}")
            return False
    
    async def auto_migrate(self) -> bool:
        """自動檢查並執行必要的遷移"""
        logger.info("開始自動遷移檢查...")
        
        # 1. 檢查資料庫連接
        if not await self.check_database_exists():
            logger.error("無法連接到資料庫，跳過遷移")
            return False
        
        # 2. 檢查表格是否存在
        table_status = await self.check_tables_exist()
        missing_tables = [table for table, exists in table_status.items() if not exists]
        
        # 3. 檢查關鍵欄位是否存在
        column_status = await self.check_columns_exist()
        missing_columns = [column for column, exists in column_status.items() if not exists]
        
        # 4. 檢查遷移版本
        current_rev = self.get_current_revision()
        head_rev = self.get_head_revision()
        
        need_migration = (
            missing_tables or 
            missing_columns or 
            current_rev != head_rev or 
            current_rev is None
        )
        
        if need_migration:
            logger.info("檢測到需要遷移:")
            if missing_tables:
                logger.info(f"  缺少表格: {missing_tables}")
            if missing_columns:
                logger.info(f"  缺少欄位: {missing_columns}")
            if current_rev != head_rev:
                logger.info(f"  版本不匹配: current={current_rev}, head={head_rev}")
            
            # 執行遷移
            success = self.run_migrations()
            if success:
                logger.info("自動遷移完成")
                return True
            else:
                logger.error("自動遷移失敗")
                return False
        else:
            logger.info("資料庫結構已是最新，無需遷移")
            return True
    
    async def validate_schema(self) -> bool:
        """驗證資料庫結構完整性"""
        logger.info("驗證資料庫結構...")
        
        # 檢查表格
        table_status = await self.check_tables_exist()
        missing_tables = [table for table, exists in table_status.items() if not exists]
        
        # 檢查欄位
        column_status = await self.check_columns_exist()
        missing_columns = [column for column, exists in column_status.items() if not exists]
        
        if missing_tables or missing_columns:
            logger.error("資料庫結構驗證失敗:")
            if missing_tables:
                logger.error(f"  缺少表格: {missing_tables}")
            if missing_columns:
                logger.error(f"  缺少欄位: {missing_columns}")
            return False
        
        logger.info("資料庫結構驗證通過")
        return True


# 全域遷移管理器實例
migration_manager = MigrationManager()


async def ensure_database_schema():
    """確保資料庫結構完整 - 啟動時調用"""
    try:
        success = await migration_manager.auto_migrate()
        if success:
            # 驗證結構
            await migration_manager.validate_schema()
        return success
    except Exception as e:
        logger.error(f"資料庫結構檢查失敗: {e}")
        return False 