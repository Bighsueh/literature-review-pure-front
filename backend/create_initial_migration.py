#!/usr/bin/env python3
"""
生成基於 ORM 模型的初始遷移
確保資料庫結構與模型完全一致
"""

import os
import sys
from pathlib import Path

# 添加項目路徑
sys.path.append(str(Path(__file__).parent))

from simplified_migration import migration_manager
from core.logging import get_logger

logger = get_logger(__name__)


def create_initial_migration():
    """創建初始遷移"""
    logger.info("🚀 開始創建初始遷移...")
    
    # 創建基於ORM模型的自動遷移
    success = migration_manager.create_migration(
        message="Initial migration based on ORM models",
        autogenerate=True
    )
    
    if success:
        logger.info("✅ 初始遷移創建成功")
        logger.info("📝 請檢查生成的遷移文件，確認內容正確")
        logger.info("📁 遷移文件位置: backend/migrations/versions/")
    else:
        logger.error("❌ 初始遷移創建失敗")
        return False
    
    return True


if __name__ == "__main__":
    success = create_initial_migration()
    sys.exit(0 if success else 1) 