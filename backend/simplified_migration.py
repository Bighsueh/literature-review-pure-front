#!/usr/bin/env python3
"""
簡化的遷移管理系統
只使用 Alembic，確保與 ORM 模型完全一致
"""

import os
import asyncio
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from sqlalchemy import text, create_engine
from sqlalchemy.ext.asyncio import create_async_engine
from alembic.config import Config
from alembic import command
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory

# 添加項目路徑
sys.path.append(str(Path(__file__).parent))

from core.config import settings
from core.logging import get_logger
from models.paper import Base  # 導入所有ORM模型

logger = get_logger(__name__)


class SimplifiedMigrationManager:
    """簡化的遷移管理器 - 只使用Alembic"""
    
    def __init__(self):
        self.backend_dir = Path(__file__).parent
        self.alembic_ini_path = self.backend_dir / "alembic.ini"
        self.migrations_dir = self.backend_dir / "migrations"
        
    def get_alembic_config(self) -> Config:
        """取得 Alembic 設定"""
        if not self.alembic_ini_path.exists():
            raise FileNotFoundError(f"Alembic 設定檔案不存在: {self.alembic_ini_path}")
            
        config = Config(str(self.alembic_ini_path))
        
        # 使用同步URL給Alembic
        db_url = settings.database_url
        config.set_main_option("sqlalchemy.url", db_url)
        config.set_main_option("script_location", str(self.migrations_dir))
        
        return config
    
    async def check_database_connection(self) -> bool:
        """檢查資料庫連接"""
        try:
            engine = create_async_engine(settings.async_database_url, echo=False)
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            await engine.dispose()
            logger.info("✅ 資料庫連接正常")
            return True
        except Exception as e:
            logger.error(f"❌ 資料庫連接失敗: {e}")
            return False
    
    def get_current_revision(self) -> Optional[str]:
        """取得當前資料庫的遷移版本"""
        try:
            config = self.get_alembic_config()
            engine = create_engine(settings.database_url)
            
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
    
    def create_migration(self, message: str, autogenerate: bool = True) -> bool:
        """創建新的遷移"""
        try:
            config = self.get_alembic_config()
            
            if autogenerate:
                logger.info(f"自動生成遷移: {message}")
                command.revision(config, autogenerate=True, message=message)
            else:
                logger.info(f"創建空白遷移: {message}")
                command.revision(config, message=message)
                
            logger.info("✅ 遷移創建成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ 創建遷移失敗: {e}")
            return False
    
    def run_migrations(self) -> bool:
        """執行遷移"""
        try:
            config = self.get_alembic_config()
            
            logger.info("開始執行資料庫遷移...")
            command.upgrade(config, "head")
            logger.info("✅ 資料庫遷移完成")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 執行遷移失敗: {e}")
            return False
    
    def show_history(self) -> bool:
        """顯示遷移歷史"""
        try:
            config = self.get_alembic_config()
            command.history(config)
            return True
        except Exception as e:
            logger.error(f"❌ 顯示歷史失敗: {e}")
            return False
    
    def show_current(self) -> bool:
        """顯示當前版本"""
        try:
            config = self.get_alembic_config()
            command.current(config)
            return True
        except Exception as e:
            logger.error(f"❌ 顯示當前版本失敗: {e}")
            return False
    
    def stamp_head(self) -> bool:
        """標記當前資料庫為最新版本（用於初始化）"""
        try:
            config = self.get_alembic_config()
            command.stamp(config, "head")
            logger.info("✅ 資料庫已標記為最新版本")
            return True
        except Exception as e:
            logger.error(f"❌ 標記失敗: {e}")
            return False
    
    async def auto_migrate(self) -> bool:
        """自動檢查並執行遷移"""
        logger.info("🔍 開始自動遷移檢查...")
        
        # 1. 檢查資料庫連接
        if not await self.check_database_connection():
            return False
        
        # 2. 檢查遷移版本
        current_rev = self.get_current_revision()
        head_rev = self.get_head_revision()
        
        logger.info(f"📊 當前版本: {current_rev}")
        logger.info(f"📊 最新版本: {head_rev}")
        
        # 3. 如果沒有版本記錄，可能是全新資料庫
        if current_rev is None:
            logger.info("🚀 檢測到全新資料庫，初始化版本控制...")
            if not self.stamp_head():
                logger.error("❌ 初始化版本控制失敗")
                return False
        # 4. 如果版本不一致，執行遷移
        elif current_rev != head_rev:
            logger.info("⬆️ 檢測到待執行的遷移，開始執行...")
            if not self.run_migrations():
                logger.error("❌ 執行遷移失敗")
                return False
        else:
            logger.info("✅ 資料庫已是最新版本")
        
        return True
    
    async def get_migration_status(self) -> Dict[str, Any]:
        """取得遷移狀態"""
        current_rev = self.get_current_revision()
        head_rev = self.get_head_revision()
        
        return {
            "current_revision": current_rev,
            "head_revision": head_rev,
            "needs_migration": current_rev != head_rev,
            "database_connected": await self.check_database_connection(),
            "status": "up_to_date" if current_rev == head_rev else "pending_migration"
        }


# 全域實例
migration_manager = SimplifiedMigrationManager()


async def ensure_database_schema() -> bool:
    """確保資料庫結構完整 - 啟動時調用"""
    try:
        return await migration_manager.auto_migrate()
    except Exception as e:
        logger.error(f"資料庫結構檢查失敗: {e}")
        return False


def main():
    """命令行工具"""
    import argparse
    
    parser = argparse.ArgumentParser(description="簡化的資料庫遷移工具")
    parser.add_argument("command", choices=[
        "status", "migrate", "create", "history", "current", "stamp"
    ], help="執行的命令")
    parser.add_argument("-m", "--message", help="遷移描述（用於create命令）")
    parser.add_argument("--no-autogenerate", action="store_true", 
                       help="不自動生成遷移內容（用於create命令）")
    
    args = parser.parse_args()
    
    async def run_command():
        if args.command == "status":
            status = await migration_manager.get_migration_status()
            print("遷移狀態:")
            for key, value in status.items():
                print(f"  {key}: {value}")
                
        elif args.command == "migrate":
            success = await migration_manager.auto_migrate()
            sys.exit(0 if success else 1)
            
        elif args.command == "create":
            if not args.message:
                print("錯誤: 創建遷移需要提供 -m 描述")
                sys.exit(1)
            success = migration_manager.create_migration(
                args.message, 
                autogenerate=not args.no_autogenerate
            )
            sys.exit(0 if success else 1)
            
        elif args.command == "history":
            success = migration_manager.show_history()
            sys.exit(0 if success else 1)
            
        elif args.command == "current":
            success = migration_manager.show_current()
            sys.exit(0 if success else 1)
            
        elif args.command == "stamp":
            success = migration_manager.stamp_head()
            sys.exit(0 if success else 1)
    
    asyncio.run(run_command())


if __name__ == "__main__":
    main() 