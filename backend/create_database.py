#!/usr/bin/env python3
"""
建立PostgreSQL資料庫腳本
"""

import asyncio
import asyncpg
import os

async def create_database():
    """建立paper_analysis資料庫"""
    
    # 連線參數
    host = os.getenv('POSTGRES_HOST', 'localhost')
    port = int(os.getenv('POSTGRES_PORT', '5432'))
    user = os.getenv('POSTGRES_USER', 'postgres')
    password = os.getenv('POSTGRES_PASSWORD', 'password')
    
    try:
        # 連線到預設的postgres資料庫
        conn = await asyncpg.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database='postgres'  # 使用預設資料庫
        )
        
        print("✅ 連線到PostgreSQL成功")
        
        # 檢查資料庫是否已存在
        db_exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = 'paper_analysis'"
        )
        
        if db_exists:
            print("⚠️  資料庫 'paper_analysis' 已存在")
        else:
            # 建立資料庫
            await conn.execute('CREATE DATABASE paper_analysis')
            print("✅ 資料庫 'paper_analysis' 建立成功")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 建立資料庫失敗: {e}")
        return False

if __name__ == "__main__":
    print("🚀 開始建立資料庫...")
    success = asyncio.run(create_database())
    
    if success:
        print("✅ 資料庫建立完成!")
    else:
        print("❌ 資料庫建立失敗") 