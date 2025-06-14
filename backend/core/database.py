from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from typing import AsyncGenerator, List
import os
import logging
from .config import settings

logger = logging.getLogger(__name__)

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

async def execute_sql_file(file_path: str):
    """安全地執行SQL檔案，分割多個語句逐一執行"""
    if not os.path.exists(file_path):
        logger.warning(f"SQL檔案不存在: {file_path}")
        return
    
    logger.info(f"SQL檔案執行中: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()

        # 分割SQL語句，正確處理 $$ 包圍的函數
        statements = _split_sql_statements(sql_content)
        
        async with async_engine.begin() as conn:
            for i, statement in enumerate(statements):
                if statement.strip():  # 跳過空語句
                    try:
                        await conn.execute(text(statement))
                        logger.debug(f"執行語句 {i+1}/{len(statements)}: {statement[:50]}...")
                    except Exception as stmt_error:
                        logger.error(f"執行語句失敗 ({i+1}/{len(statements)}): {stmt_error}")
                        logger.debug(f"失敗的語句: {statement}")
                        # 繼續執行其他語句，不中斷整個過程
        
        logger.info(f"SQL檔案執行完成: {file_path}")

    except Exception as e:
        logger.error(f"執行SQL檔案時出錯 ({file_path}): {e}", exc_info=True)
        raise  # 重新拋出異常，使應用程式啟動失敗

def _split_sql_statements(sql_content: str) -> List[str]:
    """分割SQL內容為獨立的語句，正確處理 $$ 包圍的函數"""
    statements = []
    current_statement = ""
    in_dollar_quote = False
    dollar_tag = ""
    
    lines = sql_content.split('\n')
    
    for line in lines:
        stripped_line = line.strip()
        
        # 跳過註解和空行
        if not stripped_line or stripped_line.startswith('--'):
            current_statement += line + '\n'
            continue
        
        # 檢查 dollar quote 的開始或結束
        if '$$' in line:
            if not in_dollar_quote:
                # 開始 dollar quote
                dollar_start = line.find('$$')
                if dollar_start >= 0:
                    # 提取可能的標籤 (例如 $function$ 或 $$)
                    before_dollar = line[:dollar_start]
                    after_first_dollar = line[dollar_start+2:]
                    next_dollar = after_first_dollar.find('$$')
                    
                    if next_dollar >= 0:
                        # 同一行有開始和結束標籤
                        dollar_tag = after_first_dollar[:next_dollar]
                    else:
                        # 只有開始標籤
                        dollar_tag = ""
                        in_dollar_quote = True
            else:
                # 檢查是否為結束標籤
                expected_end = f"{dollar_tag}$$"
                if expected_end in line:
                    in_dollar_quote = False
                    dollar_tag = ""
        
        current_statement += line + '\n'
        
        # 如果不在 dollar quote 中，檢查語句結束
        if not in_dollar_quote and line.strip().endswith(';'):
            statements.append(current_statement.strip())
            current_statement = ""
    
    # 加入最後一個語句（如果有的話）
    if current_statement.strip():
        statements.append(current_statement.strip())
    
    return statements

async def check_table_structure():
    """檢查關鍵表格結構"""
    try:
        async with async_engine.begin() as conn:
            # 檢查sentences表是否有新欄位
            result = await conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'sentences' 
                AND table_schema = 'public'
                AND column_name IN ('detection_status', 'error_message', 'retry_count', 'explanation')
                ORDER BY column_name;
            """))
            
            existing_columns = [row[0] for row in result.fetchall()]
            required_columns = ['detection_status', 'error_message', 'retry_count', 'explanation']
            missing_columns = [col for col in required_columns if col not in existing_columns]
            
            if missing_columns:
                logger.warning(f"sentences表缺少欄位: {missing_columns}")
                return False
            else:
                logger.info("✅ sentences表結構檢查通過")
                return True
                
    except Exception as e:
        logger.error(f"檢查表格結構失敗: {e}")
        return False

async def init_database():
    """初始化資料庫（用於應用啟動時）"""
    try:
        logger.info("🚀 開始初始化資料庫...")
        
        # 1. 測試連線
        async with async_engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            logger.info("✅ 資料庫連線測試成功")
        
        # 2. 確保UUID擴展存在
        async with async_engine.begin() as conn:
            await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'))
            logger.info("✅ UUID擴展已啟用")
        
        # 3. 使用Alembic Migration初始化資料庫
        logger.info("📋 執行Alembic遷移...")
        
        try:
            # 使用Alembic配置執行遷移
            from alembic.config import Config
            from alembic import command
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
            
            # 從環境變數取得資料庫URL
            host = os.getenv("POSTGRES_HOST", "localhost")
            port = os.getenv("POSTGRES_PORT", "5432")
            database = os.getenv("POSTGRES_DB", "paper_analysis")
            username = os.getenv("POSTGRES_USER", "postgres")
            password = os.getenv("POSTGRES_PASSWORD", "password")
            database_url = f"postgresql://{username}:{password}@{host}:{port}/{database}"
            
            logger.info(f"📝 設定資料庫URL: {database_url}")
            alembic_cfg.set_main_option("sqlalchemy.url", database_url)
            
            # 設定正確的script_location路徑
            logger.info(f"📝 設定migrations路徑: {migrations_dir}")
            alembic_cfg.set_main_option("script_location", migrations_dir)
            
            # 檢查migration狀態
            logger.info("🔍 檢查migration狀態...")
            from alembic.migration import MigrationContext
            from sqlalchemy import create_engine
            
            # 建立同步引擎用於Alembic
            sync_engine = create_engine(database_url)
            
            with sync_engine.connect() as connection:
                logger.info("✅ 資料庫連線成功，建立migration context...")
                context = MigrationContext.configure(connection)
                
                # 檢查是否已有migration記錄
                current_rev = context.get_current_revision()
                logger.info(f"📊 目前migration版本: {current_rev}")
                
                if current_rev is None:
                    logger.info("🚀 初始化Alembic版本控制...")
                    # 標記為已執行最新migration
                    command.stamp(alembic_cfg, "head")
                    logger.info("✅ Alembic版本控制初始化完成")
                else:
                    logger.info(f"📋 發現現有migration版本: {current_rev}")
                    
                # 執行migration到最新版本
                logger.info("⬆️ 執行migration到最新版本...")
                command.upgrade(alembic_cfg, "head")
                logger.info("✅ Migration執行完成")
            
            # 同步引擎用完即關閉
            sync_engine.dispose()
                    
        except Exception as migration_error:
            logger.error(f"❌ Alembic遷移失敗: {migration_error}")
            logger.error(f"❌ 錯誤類型: {type(migration_error).__name__}")
            logger.error(f"❌ 錯誤詳情: {str(migration_error)}")
            import traceback
            logger.error(f"❌ 完整堆疊追蹤:")
            logger.error(traceback.format_exc())
            logger.info("🔄 回退到schema.sql方式...")
            
            # 如果migration失敗，回退到原來的schema.sql方式
            await _fallback_to_schema_sql()
        
        # 4. 驗證核心表格是否存在
        async with async_engine.begin() as conn:
            tables_to_check = ['papers', 'paper_sections', 'sentences', 'paper_selections', 'processing_queue']
            all_tables_exist = True
            
            for table in tables_to_check:
                result = await conn.execute(text(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = '{table}'
                    );
                """))
                exists = result.scalar()
                if exists:
                    logger.info(f"✅ 表格 {table} 存在")
                else:
                    logger.error(f"❌ 表格 {table} 不存在")
                    all_tables_exist = False
        
        # 5. 檢查表格結構
        structure_ok = await check_table_structure()
        
        if all_tables_exist and structure_ok:
            logger.info("🎉 資料庫初始化完成！所有表格和結構都正確")
        else:
            logger.warning("⚠️ 資料庫初始化完成，但有部分問題需要注意")
        
    except Exception as e:
        logger.error(f"❌ 資料庫初始化失敗: {e}")
        raise

async def _fallback_to_schema_sql():
    """回退到schema.sql方式建立表格"""
    # 3. 執行主要schema
    schema_path = os.path.join(os.path.dirname(__file__), "../database/schema.sql")
    if os.path.exists(schema_path):
        logger.info("📋 執行主要資料庫schema...")
        await execute_sql_file(schema_path)
    else:
        logger.warning(f"⚠️ 找不到schema檔案: {schema_path}")
    
    # 4. 執行升級腳本
    upgrade_path = os.path.join(os.path.dirname(__file__), "../database/upgrade_sentences_table.sql")
    if os.path.exists(upgrade_path):
        logger.info("⬆️ 執行資料庫升級腳本...")
        await execute_sql_file(upgrade_path)
    else:
        logger.warning(f"⚠️ 找不到升級腳本: {upgrade_path}")

async def close_database():
    """關閉資料庫連線"""
    try:
        await async_engine.dispose()
        logger.info("👋 資料庫連線已關閉")
    except Exception as e:
        logger.error(f"關閉資料庫連線時發生錯誤: {e}") 