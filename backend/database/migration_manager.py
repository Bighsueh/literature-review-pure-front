"""
資料庫遷移管理系統
提供版本化的 Schema 管理和自動遷移功能
"""

import os
import re
import asyncio
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from datetime import datetime
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .connection import db_manager
from ..core.logging import get_logger

logger = get_logger(__name__)

class MigrationError(Exception):
    """遷移執行錯誤"""
    pass

class Migration:
    """單一遷移文件的表示"""
    
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.filename = file_path.name
        self.version = self._extract_version()
        self.description = self._extract_description()
        
    def _extract_version(self) -> str:
        """從檔名提取版本號"""
        match = re.match(r'^(\d{3})_', self.filename)
        if not match:
            raise ValueError(f"無效的遷移檔名格式: {self.filename}")
        return match.group(1)
    
    def _extract_description(self) -> str:
        """從檔名提取描述"""
        match = re.match(r'^\d{3}_(.+)\.sql$', self.filename)
        if not match:
            return "未知遷移"
        return match.group(1).replace('_', ' ').title()
    
    def get_content(self) -> str:
        """讀取遷移文件內容"""
        with open(self.file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def __str__(self):
        return f"Migration {self.version}: {self.description}"
    
    def __repr__(self):
        return f"Migration(version='{self.version}', description='{self.description}')"

class MigrationManager:
    """遷移管理器"""
    
    def __init__(self):
        self.migrations_dir = Path(__file__).parent / "migrations"
        self.ensure_migrations_table_exists = True
        
    async def initialize(self):
        """初始化遷移系統"""
        # 確保遷移目錄存在
        self.migrations_dir.mkdir(exist_ok=True)
        
        # 創建遷移記錄表
        if self.ensure_migrations_table_exists:
            await self._create_migration_table()
    
    async def _create_migration_table(self):
        """創建遷移記錄表"""
        session = await db_manager.get_async_session()
        try:
            # 創建遷移記錄表
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    id SERIAL PRIMARY KEY,
                    version VARCHAR(10) NOT NULL UNIQUE,
                    description TEXT,
                    applied_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    checksum VARCHAR(64),
                    execution_time_ms INTEGER,
                    success BOOLEAN DEFAULT TRUE
                )
            """))
            
            # 創建索引
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_schema_migrations_version 
                ON schema_migrations(version)
            """))
            await session.commit()
            logger.info("遷移記錄表已準備就緒")
        except Exception as e:
            await session.rollback()
            logger.error(f"創建遷移記錄表失敗: {e}")
            raise
        finally:
            await session.close()
    
    def discover_migrations(self) -> List[Migration]:
        """發現所有遷移文件"""
        if not self.migrations_dir.exists():
            return []
        
        migrations = []
        for file_path in self.migrations_dir.glob("*.sql"):
            try:
                migration = Migration(file_path)
                migrations.append(migration)
            except ValueError as e:
                logger.warning(f"跳過無效的遷移文件: {e}")
        
        # 按版本號排序
        migrations.sort(key=lambda m: m.version)
        return migrations
    
    async def get_applied_migrations(self) -> List[str]:
        """取得已應用的遷移版本"""
        session = await db_manager.get_async_session()
        try:
            result = await session.execute(text("""
                SELECT version FROM schema_migrations 
                WHERE success = TRUE 
                ORDER BY version
            """))
            return [row[0] for row in result.fetchall()]
        except Exception as e:
            logger.error(f"取得已應用遷移失敗: {e}")
            return []
        finally:
            await session.close()
    
    async def get_pending_migrations(self) -> List[Migration]:
        """取得待應用的遷移"""
        all_migrations = self.discover_migrations()
        applied_versions = await self.get_applied_migrations()
        
        pending = [m for m in all_migrations if m.version not in applied_versions]
        return pending
    
    async def apply_migration(self, migration: Migration) -> bool:
        """應用單一遷移"""
        logger.info(f"開始應用遷移: {migration}")
        start_time = datetime.now()
        
        session = await db_manager.get_async_session()
        try:
            # 執行遷移 SQL
            sql_content = migration.get_content()
            await session.execute(text(sql_content))
            
            # 計算執行時間
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # 記錄遷移應用
            await session.execute(text("""
                INSERT INTO schema_migrations (version, description, execution_time_ms, success)
                VALUES (:version, :description, :execution_time, TRUE)
            """), {
                "version": migration.version,
                "description": migration.description,
                "execution_time": execution_time
            })
            
            await session.commit()
            logger.info(f"遷移 {migration.version} 應用成功 (耗時: {execution_time}ms)")
            return True
            
        except Exception as e:
            await session.rollback()
            
            # 記錄失敗的遷移
            try:
                await session.execute(text("""
                    INSERT INTO schema_migrations (version, description, success)
                    VALUES (:version, :description, FALSE)
                """), {
                    "version": migration.version,
                    "description": f"FAILED: {migration.description}"
                })
                await session.commit()
            except:
                pass  # 忽略記錄失敗的錯誤
            
            logger.error(f"遷移 {migration.version} 應用失敗: {e}")
            raise MigrationError(f"遷移失敗: {e}")
        finally:
            await session.close()
    
    async def migrate(self, target_version: Optional[str] = None) -> Dict[str, any]:
        """執行遷移到指定版本"""
        await self.initialize()
        
        pending_migrations = await self.get_pending_migrations()
        
        if target_version:
            # 過濾到指定版本
            pending_migrations = [m for m in pending_migrations if m.version <= target_version]
        
        if not pending_migrations:
            logger.info("沒有待應用的遷移")
            return {
                "applied_count": 0,
                "migrations": [],
                "status": "up_to_date"
            }
        
        applied_migrations = []
        failed_migrations = []
        
        for migration in pending_migrations:
            try:
                await self.apply_migration(migration)
                applied_migrations.append(migration.version)
            except MigrationError as e:
                failed_migrations.append({
                    "version": migration.version,
                    "error": str(e)
                })
                logger.error(f"遷移中斷於版本 {migration.version}: {e}")
                break
        
        return {
            "applied_count": len(applied_migrations),
            "applied_migrations": applied_migrations,
            "failed_migrations": failed_migrations,
            "status": "completed" if not failed_migrations else "failed"
        }
    
    async def get_migration_status(self) -> Dict[str, any]:
        """取得遷移狀態摘要"""
        await self.initialize()
        
        all_migrations = self.discover_migrations()
        applied_versions = await self.get_applied_migrations()
        pending_migrations = await self.get_pending_migrations()
        
        return {
            "total_migrations": len(all_migrations),
            "applied_count": len(applied_versions),
            "pending_count": len(pending_migrations),
            "current_version": applied_versions[-1] if applied_versions else None,
            "pending_versions": [m.version for m in pending_migrations],
            "status": "up_to_date" if not pending_migrations else "pending_migrations"
        }

# 全域遷移管理器實例
migration_manager = MigrationManager()

async def auto_migrate():
    """自動遷移函數，用於應用程式啟動時"""
    try:
        logger.info("開始自動資料庫遷移...")
        result = await migration_manager.migrate()
        
        if result["status"] == "up_to_date":
            logger.info("資料庫 Schema 已是最新版本")
        elif result["status"] == "completed":
            logger.info(f"成功應用 {result['applied_count']} 個遷移")
        else:
            logger.error(f"遷移失敗: {result['failed_migrations']}")
            raise Exception("資料庫遷移失敗")
            
    except Exception as e:
        logger.error(f"自動遷移失敗: {e}")
        raise

if __name__ == "__main__":
    # 命令行工具
    import sys
    
    async def cli_main():
        if len(sys.argv) < 2:
            print("用法: python migration_manager.py [status|migrate|pending]")
            return
        
        command = sys.argv[1]
        
        if command == "status":
            status = await migration_manager.get_migration_status()
            print(f"遷移狀態: {status}")
        elif command == "migrate":
            result = await migration_manager.migrate()
            print(f"遷移結果: {result}")
        elif command == "pending":
            pending = await migration_manager.get_pending_migrations()
            print(f"待應用遷移: {[str(m) for m in pending]}")
        else:
            print(f"未知命令: {command}")
    
    asyncio.run(cli_main()) 