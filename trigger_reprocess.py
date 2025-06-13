#!/usr/bin/env python3
"""
直接觸發論文重新處理的腳本
"""
import asyncio
import sys
import os
sys.path.append('/Users/hsueh/Code/Python/master_thesis/pure_front')

from backend.services.processing_service import processing_service
from backend.core.database import AsyncSessionLocal

PAPER_ID = "7bd19181-b596-4cd1-891a-4a8d50b852f9"

async def trigger_reprocess():
    print("🔄 直接觸發論文重新處理")
    print("=" * 50)
    
    try:
        # 直接調用處理服務
        result = await processing_service.process_file(
            file_id=PAPER_ID,
            options={
                "detect_od_cd": True,
                "force_reprocess": True
            }
        )
        
        print(f"✅ 處理完成: {result}")
        return True
        
    except Exception as e:
        print(f"❌ 處理失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(trigger_reprocess()) 