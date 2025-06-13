#!/usr/bin/env python3
"""
資料庫遷移管理工具
提供命令行介面來管理資料庫遷移
"""

import asyncio
import argparse
import sys
from pathlib import Path

# 添加後端目錄到 Python 路徑
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from core.migration_manager import migration_manager, ensure_database_schema
from core.logging import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


async def check_status():
    """檢查資料庫和遷移狀態"""
    print("=== 資料庫遷移狀態檢查 ===")
    
    # 檢查資料庫連接
    db_exists = await migration_manager.check_database_exists()
    print(f"資料庫連接: {'✓' if db_exists else '✗'}")
    
    if not db_exists:
        return
    
    # 檢查表格
    table_status = await migration_manager.check_tables_exist()
    print("\n表格狀態:")
    for table, exists in table_status.items():
        print(f"  {table}: {'✓' if exists else '✗'}")
    
    # 檢查欄位
    column_status = await migration_manager.check_columns_exist()
    print("\n關鍵欄位狀態:")
    for column, exists in column_status.items():
        print(f"  {column}: {'✓' if exists else '✗'}")
    
    # 檢查遷移版本
    current_rev = migration_manager.get_current_revision()
    head_rev = migration_manager.get_head_revision()
    
    print(f"\n遷移版本:")
    print(f"  當前版本: {current_rev or '無'}")
    print(f"  最新版本: {head_rev or '無'}")
    print(f"  狀態: {'✓ 最新' if current_rev == head_rev else '⚠ 需要更新'}")


async def run_migrations():
    """執行遷移"""
    print("=== 執行資料庫遷移 ===")
    
    success = await ensure_database_schema()
    if success:
        print("✓ 遷移執行完成")
    else:
        print("✗ 遷移執行失敗")
        return 1
    
    return 0


async def validate_schema():
    """驗證資料庫結構"""
    print("=== 驗證資料庫結構 ===")
    
    success = await migration_manager.validate_schema()
    if success:
        print("✓ 資料庫結構驗證通過")
    else:
        print("✗ 資料庫結構驗證失敗")
        return 1
    
    return 0


def create_migration():
    """創建新的遷移腳本"""
    print("=== 創建新遷移 ===")
    
    message = input("請輸入遷移描述: ").strip()
    if not message:
        print("錯誤: 遷移描述不能為空")
        return 1
    
    try:
        from alembic import command
        config = migration_manager.get_alembic_config()
        
        # 創建自動遷移
        command.revision(config, autogenerate=True, message=message)
        print(f"✓ 已創建遷移: {message}")
        
    except Exception as e:
        print(f"✗ 創建遷移失敗: {e}")
        return 1
    
    return 0


def show_history():
    """顯示遷移歷史"""
    print("=== 遷移歷史 ===")
    
    try:
        from alembic import command
        config = migration_manager.get_alembic_config()
        
        command.history(config, verbose=True)
        
    except Exception as e:
        print(f"✗ 顯示歷史失敗: {e}")
        return 1
    
    return 0


async def reset_database():
    """重置資料庫 (危險操作)"""
    print("=== 重置資料庫 ===")
    print("⚠️  警告: 此操作將刪除所有資料!")
    
    confirm = input("請輸入 'RESET' 來確認: ").strip()
    if confirm != 'RESET':
        print("操作已取消")
        return 0
    
    try:
        from alembic import command
        config = migration_manager.get_alembic_config()
        
        # 回退到初始狀態
        command.downgrade(config, "base")
        print("✓ 資料庫已重置到初始狀態")
        
        # 重新應用遷移
        success = await run_migrations()
        return success
        
    except Exception as e:
        print(f"✗ 重置失敗: {e}")
        return 1


async def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="資料庫遷移管理工具")
    parser.add_argument(
        "command",
        choices=["status", "migrate", "validate", "create", "history", "reset"],
        help="要執行的命令"
    )
    
    args = parser.parse_args()
    
    try:
        if args.command == "status":
            await check_status()
            return 0
        elif args.command == "migrate":
            return await run_migrations()
        elif args.command == "validate":
            return await validate_schema()
        elif args.command == "create":
            return create_migration()
        elif args.command == "history":
            return show_history()
        elif args.command == "reset":
            return await reset_database()
        else:
            print(f"未知命令: {args.command}")
            return 1
            
    except KeyboardInterrupt:
        print("\n操作已中斷")
        return 1
    except Exception as e:
        logger.error(f"執行失敗: {e}")
        print(f"✗ 執行失敗: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main()) 