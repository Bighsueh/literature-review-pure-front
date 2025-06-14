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
        
        success_count = 0
        error_count = 0
        
        async with async_engine.begin() as conn:
            for i, statement in enumerate(statements):
                if statement.strip():  # 跳過空語句
                    try:
                        await conn.execute(text(statement))
                        success_count += 1
                        logger.debug(f"執行語句 {i+1}/{len(statements)}: {statement[:50]}...")
                    except Exception as stmt_error:
                        error_count += 1
                        error_msg = str(stmt_error).lower()
                        
                        # 這些錯誤是可忽略的，因為它們通常表示資源已存在
                        ignorable_errors = [
                            'already exists',
                            'duplicate',
                            'current transaction is aborted',
                            'already exists',
                            'relation already exists'
                        ]
                        
                        if any(ignorable in error_msg for ignorable in ignorable_errors):
                            logger.debug(f"忽略預期錯誤 ({i+1}/{len(statements)}): {stmt_error}")
                        else:
                            logger.error(f"執行語句失敗 ({i+1}/{len(statements)}): {stmt_error}")
                            logger.debug(f"失敗的語句: {statement}")
                        
                        # 繼續執行其他語句，不中斷整個過程
        
        logger.info(f"SQL檔案執行完成: {file_path} (成功: {success_count}, 錯誤: {error_count})")
        
        if error_count == 0:
            logger.info("✅ 所有語句執行成功")
        elif success_count > 0:
            logger.warning(f"⚠️ 部分語句執行失敗，但有 {success_count} 個語句成功執行")
        else:
            logger.error("❌ 所有語句執行失敗")

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
        
        # 3. 檢查是否已有表格存在
        async with async_engine.begin() as conn:
            result = await conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'papers'
                );
            """))
            papers_table_exists = result.scalar()
            logger.info(f"📊 papers 表格存在狀態: {papers_table_exists}")
        
        # 4. 如果沒有表格，直接使用 schema.sql 初始化
        if not papers_table_exists:
            logger.info("📋 檢測到空資料庫，直接使用 schema.sql 初始化...")
            await _fallback_to_schema_sql()
        else:
            # 5. 如果有表格，嘗試使用 Alembic Migration
            logger.info("📋 檢測到現有資料庫，嘗試執行 Alembic 遷移...")
            
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
                    logger.warning(f"找不到alembic.ini檔案: {alembic_ini_path}，跳過 Alembic 遷移")
                    raise FileNotFoundError("alembic.ini not found")
                
                if not os.path.exists(migrations_dir):
                    logger.warning(f"找不到migrations目錄: {migrations_dir}，跳過 Alembic 遷移")
                    raise FileNotFoundError("migrations directory not found")
                
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
        
        # 6. 驗證核心表格是否存在
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
        
        # 7. 檢查表格結構
        structure_ok = await check_table_structure()
        
        if all_tables_exist and structure_ok:
            logger.info("🎉 資料庫初始化完成！所有表格和結構都正確")
        elif all_tables_exist:
            logger.warning("⚠️ 資料庫初始化完成，表格存在但結構可能有問題")
        else:
            logger.error("❌ 資料庫初始化失敗，部分表格不存在")
            # 最後嘗試：強制執行 schema
            logger.info("🔄 最後嘗試：強制執行完整 schema...")
            await _force_create_schema()
        
    except Exception as e:
        logger.error(f"❌ 資料庫初始化失敗: {e}")
        import traceback
        logger.error(traceback.format_exc())
        # 不要拋出異常，讓應用程式繼續啟動
        logger.warning("⚠️ 資料庫初始化失敗，但應用程式將繼續啟動")

async def _fallback_to_schema_sql():
    """回退到schema.sql方式建立表格"""
    logger.info("🔄 開始使用 schema.sql 方式初始化資料庫...")
    
    try:
        # 1. 首先執行修復腳本，確保缺失的欄位被添加
        fix_script_path = os.path.join(os.path.dirname(__file__), "../database/fix_missing_columns.sql")
        if os.path.exists(fix_script_path):
            logger.info("🔧 執行欄位修復腳本...")
            await execute_sql_file(fix_script_path)
        else:
            logger.warning(f"⚠️ 找不到修復腳本: {fix_script_path}")
        
        # 2. 執行主要schema
        schema_path = os.path.join(os.path.dirname(__file__), "../database/schema.sql")
        if os.path.exists(schema_path):
            logger.info("📋 執行主要資料庫schema...")
            await execute_sql_file(schema_path)
        else:
            logger.warning(f"⚠️ 找不到schema檔案: {schema_path}")
        
        # 3. 執行升級腳本
        upgrade_path = os.path.join(os.path.dirname(__file__), "../database/upgrade_sentences_table.sql")
        if os.path.exists(upgrade_path):
            logger.info("⬆️ 執行資料庫升級腳本...")
            await execute_sql_file(upgrade_path)
        else:
            logger.warning(f"⚠️ 找不到升級腳本: {upgrade_path}")
            
        logger.info("✅ Schema.sql 方式初始化完成")
        
    except Exception as e:
        logger.error(f"❌ Schema.sql 初始化失敗: {e}")
        raise

async def _force_create_schema():
    """強制創建完整的資料庫 schema"""
    logger.info("🔧 強制創建完整的資料庫 schema...")
    
    schema_sql = """
-- 論文分析系統資料庫 Schema
-- PostgreSQL 14+

-- 建立UUID擴展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 論文管理表 (加入TEI XML儲存，簡化使用者管理)
CREATE TABLE IF NOT EXISTS papers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    file_name VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255),
    upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processing_status VARCHAR(50) DEFAULT 'uploading',
    file_size BIGINT,
    file_hash VARCHAR(64) UNIQUE, -- 用於檔案去重
    grobid_processed BOOLEAN DEFAULT FALSE,
    sentences_processed BOOLEAN DEFAULT FALSE,
    od_cd_processed BOOLEAN DEFAULT FALSE, -- 新增缺失的欄位
    pdf_deleted BOOLEAN DEFAULT FALSE, -- 標記PDF是否已刪除
    error_message TEXT,
    -- TEI XML 儲存 (新增)
    tei_xml TEXT, -- 儲存完整的Grobid TEI XML
    tei_metadata JSONB, -- 儲存解析後的metadata (作者、標題等)
    processing_completed_at TIMESTAMP, -- 處理完成時間
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 論文章節表 (從TEI XML解析)
CREATE TABLE IF NOT EXISTS paper_sections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    paper_id UUID NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    section_type VARCHAR(50) NOT NULL, -- abstract, introduction, methodology, results, conclusion, references
    page_num INTEGER,
    content TEXT NOT NULL,
    section_order INTEGER, -- 章節順序
    tei_coordinates JSONB, -- TEI中的座標資訊
    word_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 句子表 (從章節內容切分)
CREATE TABLE IF NOT EXISTS sentences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    paper_id UUID NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    section_id UUID REFERENCES paper_sections(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    sentence_order INTEGER, -- 在該章節中的順序
    word_count INTEGER,
    char_count INTEGER,
    -- 檢測結果欄位
    has_objective BOOLEAN DEFAULT NULL,
    has_dataset BOOLEAN DEFAULT NULL,
    has_contribution BOOLEAN DEFAULT NULL,
    detection_status VARCHAR(20) DEFAULT 'unknown', -- pending, completed, failed, unknown
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    explanation TEXT, -- 檢測結果的解釋
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 論文選取狀態表 (用於標記哪些論文被選中進行分析)
CREATE TABLE IF NOT EXISTS paper_selections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    paper_id UUID NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    is_selected BOOLEAN DEFAULT FALSE,
    selected_at TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(paper_id) -- 每篇論文只能有一個選取狀態
);

-- 處理佇列表 (用於管理檔案處理任務)
CREATE TABLE IF NOT EXISTS processing_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    paper_id UUID NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    task_type VARCHAR(50) NOT NULL, -- grobid_processing, sentence_extraction, od_cd_detection
    status VARCHAR(20) DEFAULT 'pending', -- pending, processing, completed, failed
    priority INTEGER DEFAULT 0,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    error_message TEXT,
    task_data JSONB, -- 任務相關的額外資料
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- 建立索引以提升查詢效能
CREATE INDEX IF NOT EXISTS idx_papers_status ON papers(processing_status);
CREATE INDEX IF NOT EXISTS idx_papers_hash ON papers(file_hash);
CREATE INDEX IF NOT EXISTS idx_papers_created ON papers(created_at);
CREATE INDEX IF NOT EXISTS idx_sections_paper ON paper_sections(paper_id);
CREATE INDEX IF NOT EXISTS idx_sections_type ON paper_sections(section_type);
CREATE INDEX IF NOT EXISTS idx_sentences_paper ON sentences(paper_id);
CREATE INDEX IF NOT EXISTS idx_sentences_section ON sentences(section_id);
CREATE INDEX IF NOT EXISTS idx_sentences_detection ON sentences(has_objective, has_dataset, has_contribution);
CREATE INDEX IF NOT EXISTS idx_sentences_status ON sentences(detection_status);
CREATE INDEX IF NOT EXISTS idx_selections_paper ON paper_selections(paper_id);
CREATE INDEX IF NOT EXISTS idx_selections_selected ON paper_selections(is_selected);
CREATE INDEX IF NOT EXISTS idx_queue_status ON processing_queue(status);
CREATE INDEX IF NOT EXISTS idx_queue_type ON processing_queue(task_type);
CREATE INDEX IF NOT EXISTS idx_queue_priority ON processing_queue(priority DESC, created_at);
"""
    
    try:
        async with async_engine.begin() as conn:
            await conn.execute(text(schema_sql))
            logger.info("✅ 強制 schema 創建完成")
            
        # 創建觸發器
        trigger_sql = """
-- 建立觸發器以自動更新 updated_at 欄位
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 為 sentences 表建立觸發器
DROP TRIGGER IF EXISTS update_sentences_updated_at ON sentences;
CREATE TRIGGER update_sentences_updated_at
    BEFORE UPDATE ON sentences
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
"""
        
        async with async_engine.begin() as conn:
            await conn.execute(text(trigger_sql))
            logger.info("✅ 觸發器創建完成")
            
    except Exception as e:
        logger.error(f"❌ 強制 schema 創建失敗: {e}")
        raise

async def close_database():
    """關閉資料庫連線"""
    try:
        await async_engine.dispose()
        logger.info("👋 資料庫連線已關閉")
    except Exception as e:
        logger.error(f"關閉資料庫連線時發生錯誤: {e}") 