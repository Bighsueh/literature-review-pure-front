#!/usr/bin/env python3
"""
快速系統檢查腳本
驗證修正後的系統是否正常工作
"""

import asyncio
import sys
import traceback
from typing import Dict, Any

# 添加專案根目錄到Python路徑
sys.path.insert(0, '/Users/hsueh/Code/Python/master_thesis/pure_front')

async def check_imports():
    """檢查關鍵模組的導入"""
    print("🔍 檢查關鍵模組導入...")
    
    try:
        # 檢查後端核心模組
        from backend.services.unified_query_service import unified_query_processor
        from backend.services.n8n_service import N8NService
        from backend.api.workspace_query import router
        print("✅ 後端核心模組導入成功")
        return True
    except Exception as e:
        print(f"❌ 模組導入失敗: {e}")
        traceback.print_exc()
        return False

async def check_n8n_service_methods():
    """檢查N8N服務方法"""
    print("\n🔍 檢查N8N服務方法...")
    
    try:
        from backend.services.n8n_service import N8NService
        n8n_service = N8NService()
        
        # 檢查關鍵方法存在
        assert hasattr(n8n_service, 'extract_keywords'), "extract_keywords方法不存在"
        assert hasattr(n8n_service, 'intelligent_section_selection'), "intelligent_section_selection方法不存在"
        assert hasattr(n8n_service, 'unified_content_analysis'), "unified_content_analysis方法不存在"
        
        print("✅ N8N服務方法檢查通過")
        return True
    except Exception as e:
        print(f"❌ N8N服務方法檢查失敗: {e}")
        return False

async def check_unified_query_service():
    """檢查統一查詢服務"""
    print("\n🔍 檢查統一查詢服務...")
    
    try:
        from backend.services.unified_query_service import unified_query_processor
        
        # 檢查關鍵方法
        assert hasattr(unified_query_processor, 'process_query'), "process_query方法不存在"
        assert hasattr(unified_query_processor, '_extract_workspace_content'), "_extract_workspace_content方法不存在"
        assert hasattr(unified_query_processor, '_unified_content_analysis'), "_unified_content_analysis方法不存在"
        
        print("✅ 統一查詢服務檢查通過")
        return True
    except Exception as e:
        print(f"❌ 統一查詢服務檢查失敗: {e}")
        return False

async def check_api_router():
    """檢查API路由器"""
    print("\n🔍 檢查API路由器...")
    
    try:
        from backend.api.workspace_query import router
        
        # 檢查路由配置
        routes = [route for route in router.routes]
        unified_route = None
        
        for route in routes:
            if hasattr(route, 'path') and '/unified' in route.path:
                unified_route = route
                break
        
        assert unified_route is not None, "/unified路由不存在"
        print(f"✅ API路由器檢查通過，找到路由: {unified_route.path}")
        return True
    except Exception as e:
        print(f"❌ API路由器檢查失敗: {e}")
        return False

async def test_mock_query_flow():
    """測試模擬查詢流程"""
    print("\n🔍 測試模擬查詢流程...")
    
    try:
        from backend.services.unified_query_service import UnifiedQueryProcessor
        
        # 創建處理器實例
        processor = UnifiedQueryProcessor()
        
        # 模擬查詢參數（不實際連接資料庫）
        mock_query_params = {
            'query': 'Compare definitions of adaptive expertise',
            'workspace_id': 'test-workspace-id',
            'paper_ids': ['test-paper-1', 'test-paper-2']
        }
        
        # 檢查處理器統計
        stats = processor.get_processing_stats()
        assert isinstance(stats, dict), "統計資料格式錯誤"
        
        print("✅ 模擬查詢流程檢查通過")
        return True
    except Exception as e:
        print(f"❌ 模擬查詢流程檢查失敗: {e}")
        return False

async def check_method_name_consistency():
    """檢查方法名稱一致性"""
    print("\n🔍 檢查方法名稱一致性...")
    
    try:
        # 讀取統一查詢服務檔案
        with open('/Users/hsueh/Code/Python/master_thesis/pure_front/backend/services/unified_query_service.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 檢查是否還有舊的方法名稱
        if 'query_keyword_extraction' in content:
            print("❌ 發現舊的方法名稱 'query_keyword_extraction'")
            return False
        
        # 檢查是否使用了正確的方法名稱
        if 'extract_keywords' not in content:
            print("❌ 未找到正確的方法名稱 'extract_keywords'")
            return False
        
        print("✅ 方法名稱一致性檢查通過")
        return True
    except Exception as e:
        print(f"❌ 方法名稱一致性檢查失敗: {e}")
        return False

async def main():
    """主檢查函數"""
    print("🚀 開始系統快速檢查...")
    print("=" * 50)
    
    checks = [
        ("模組導入", check_imports),
        ("N8N服務方法", check_n8n_service_methods),
        ("統一查詢服務", check_unified_query_service),
        ("API路由器", check_api_router),
        ("方法名稱一致性", check_method_name_consistency),
        ("模擬查詢流程", test_mock_query_flow),
    ]
    
    results = []
    
    for name, check_func in checks:
        try:
            result = await check_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ 檢查 '{name}' 時發生錯誤: {e}")
            results.append((name, False))
    
    # 總結報告
    print("\n" + "=" * 50)
    print("📊 檢查結果總結:")
    
    passed = 0
    total = len(results)
    
    for name, result in results:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"  {name}: {status}")
        if result:
            passed += 1
    
    print(f"\n總結: {passed}/{total} 檢查通過")
    
    if passed == total:
        print("🎉 所有檢查都通過！系統修正成功！")
        return True
    else:
        print("⚠️ 部分檢查失敗，需要進一步修正")
        return False

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1) 