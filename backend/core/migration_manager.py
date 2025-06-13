"""
資料庫遷移管理器
自動檢查和執行 Alembic 遷移
"""

import os
import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Tuple, Any
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
        
        # 預期的完整schema定義
        self.expected_schema = {
            'papers': {
                'required_columns': [
                    'id', 'file_name', 'original_filename', 'upload_timestamp',
                    'processing_status', 'file_size', 'file_hash', 'grobid_processed',
                    'sentences_processed', 'od_cd_processed', 'pdf_deleted', 
                    'error_message', 'tei_xml', 'tei_metadata', 'processing_completed_at',
                    'created_at'
                ],
                'critical_columns': ['od_cd_processed']  # 這些欄位缺失會導致嚴重錯誤
            },
            'paper_sections': {
                'required_columns': [
                    'id', 'paper_id', 'section_type', 'page_num', 'content',
                    'section_order', 'tei_coordinates', 'word_count', 'created_at'
                ],
                'critical_columns': []
            },
            'sentences': {
                'required_columns': [
                    'id', 'paper_id', 'section_id', 'sentence_text', 'page_num',
                    'sentence_order', 'defining_type', 'analysis_reason', 'word_count',
                    'confidence_score', 'processed_timestamp', 'detection_status',
                    'error_message', 'retry_count', 'explanation'
                ],
                'critical_columns': ['detection_status']
            }
        }
        
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

    async def get_actual_schema(self) -> Dict[str, List[str]]:
        """取得實際資料庫的schema結構"""
        try:
            db_url = get_database_url()
            engine = create_async_engine(db_url, echo=False)
            
            schema_info = {}
            
            async with engine.begin() as conn:
                # 取得所有表格及其欄位
                for table_name in self.expected_schema.keys():
                    result = await conn.execute(text(f"""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = '{table_name}' AND table_schema = 'public'
                        ORDER BY ordinal_position
                    """))
                    columns = [row[0] for row in result.fetchall()]
                    schema_info[table_name] = columns
                
            await engine.dispose()
            return schema_info
            
        except Exception as e:
            logger.error(f"取得schema結構失敗: {e}")
            return {}

    async def detect_schema_drift(self) -> Tuple[bool, Dict[str, Any]]:
        """檢測schema drift（結構漂移）"""
        try:
            actual_schema = await self.get_actual_schema()
            drift_report = {
                'has_drift': False,
                'missing_tables': [],
                'missing_columns': {},
                'critical_issues': [],
                'warnings': []
            }
            
            # 檢查缺失的表格
            for table_name in self.expected_schema.keys():
                if table_name not in actual_schema:
                    drift_report['missing_tables'].append(table_name)
                    drift_report['has_drift'] = True
                    drift_report['critical_issues'].append(f"表格 '{table_name}' 不存在")
            
            # 檢查缺失的欄位
            for table_name, table_def in self.expected_schema.items():
                if table_name in actual_schema:
                    actual_columns = set(actual_schema[table_name])
                    required_columns = set(table_def['required_columns'])
                    missing_columns = required_columns - actual_columns
                    
                    if missing_columns:
                        drift_report['missing_columns'][table_name] = list(missing_columns)
                        drift_report['has_drift'] = True
                        
                        # 檢查是否為關鍵欄位
                        critical_missing = set(missing_columns) & set(table_def['critical_columns'])
                        if critical_missing:
                            for col in critical_missing:
                                drift_report['critical_issues'].append(
                                    f"關鍵欄位 '{table_name}.{col}' 缺失"
                                )
                        else:
                            drift_report['warnings'].append(
                                f"表格 '{table_name}' 缺少欄位: {list(missing_columns)}"
                            )
            
            return drift_report['has_drift'], drift_report
            
        except Exception as e:
            logger.error(f"Schema drift 檢測失敗: {e}")
            return True, {'error': str(e)}

    async def check_tables_exist(self) -> dict:
        """檢查必要的表格是否存在"""
        required_tables = list(self.expected_schema.keys()) + [
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
                # 檢查所有關鍵欄位
                for table_name, table_def in self.expected_schema.items():
                    for column in table_def['critical_columns']:
                        result = await conn.execute(text(f"""
                            SELECT column_name 
                            FROM information_schema.columns 
                            WHERE table_name = '{table_name}' AND column_name = '{column}'
                        """))
                        rows = result.fetchall()
                        column_checks[f'{table_name}.{column}'] = len(rows) > 0
                
                # 檢查其他重要欄位
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

    async def auto_fix_critical_issues(self) -> bool:
        """自動修復關鍵問題"""
        try:
            has_drift, drift_report = await self.detect_schema_drift()
            
            if not has_drift:
                logger.info("未檢測到schema drift，無需修復")
                return True
            
            critical_issues = drift_report.get('critical_issues', [])
            if not critical_issues:
                logger.info("無關鍵問題需要修復")
                return True
            
            logger.warning(f"檢測到 {len(critical_issues)} 個關鍵問題，嘗試自動修復...")
            
            db_url = get_database_url()
            engine = create_async_engine(db_url, echo=False)
            
            async with engine.begin() as conn:
                # 修復缺失的關鍵欄位
                if 'papers.od_cd_processed' in [issue for issue in critical_issues if 'od_cd_processed' in issue]:
                    logger.info("修復 papers.od_cd_processed 欄位...")
                    await conn.execute(text(
                        "ALTER TABLE papers ADD COLUMN IF NOT EXISTS od_cd_processed BOOLEAN DEFAULT FALSE"
                    ))
                    logger.info("已修復 papers.od_cd_processed 欄位")
                
                # 可以在這裡添加更多自動修復邏輯
                
            await engine.dispose()
            
            # 再次檢查是否修復成功
            has_drift_after, _ = await self.detect_schema_drift()
            if not has_drift_after:
                logger.info("所有關鍵問題已自動修復")
                return True
            else:
                logger.warning("部分問題可能需要手動修復")
                return False
                
        except Exception as e:
            logger.error(f"自動修復失敗: {e}")
            return False
    
    async def auto_migrate(self) -> bool:
        """自動檢查並執行必要的遷移"""
        logger.info("開始自動遷移檢查...")
        
        # 1. 檢查資料庫連接
        if not await self.check_database_exists():
            logger.error("無法連接到資料庫，跳過遷移")
            return False
        
        # 2. 檢測schema drift
        has_drift, drift_report = await self.detect_schema_drift()
        
        if has_drift:
            logger.warning("檢測到 schema drift:")
            
            # 打印詳細報告
            if drift_report.get('critical_issues'):
                for issue in drift_report['critical_issues']:
                    logger.error(f"  關鍵問題: {issue}")
            
            if drift_report.get('warnings'):
                for warning in drift_report['warnings']:
                    logger.warning(f"  警告: {warning}")
            
            # 嘗試自動修復關鍵問題
            if drift_report.get('critical_issues'):
                logger.info("嘗試自動修復關鍵問題...")
                fix_success = await self.auto_fix_critical_issues()
                if not fix_success:
                    logger.error("自動修復失敗，請手動檢查")
                    return False
        
        # 3. 檢查表格是否存在
        table_status = await self.check_tables_exist()
        missing_tables = [table for table, exists in table_status.items() if not exists]
        
        # 4. 檢查關鍵欄位是否存在
        column_status = await self.check_columns_exist()
        missing_columns = [column for column, exists in column_status.items() if not exists]
        
        # 5. 檢查遷移版本
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
                # 最終驗證
                return await self.validate_schema()
            else:
                logger.error("自動遷移失敗")
                return False
        else:
            logger.info("資料庫結構已是最新，無需遷移")
            return True
    
    async def validate_schema(self) -> bool:
        """驗證資料庫結構完整性"""
        logger.info("驗證資料庫結構...")
        
        # 使用新的schema drift檢測
        has_drift, drift_report = await self.detect_schema_drift()
        
        if has_drift:
            logger.error("資料庫結構驗證失敗:")
            
            if drift_report.get('critical_issues'):
                for issue in drift_report['critical_issues']:
                    logger.error(f"  關鍵問題: {issue}")
            
            if drift_report.get('warnings'):
                for warning in drift_report['warnings']:
                    logger.warning(f"  警告: {warning}")
            
            return len(drift_report.get('critical_issues', [])) == 0  # 只要沒有關鍵問題就算通過
        
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