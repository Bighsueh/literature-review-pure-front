"""
驗證解決方案可行性的診斷腳本
"""
import asyncio
import sys
import os
from datetime import datetime

# 添加後端路徑到 Python path
backend_path = os.path.join(os.path.dirname(__file__), '..', 'backend')
sys.path.insert(0, backend_path)

from core.database import AsyncSessionLocal
from sqlalchemy import text
from services.db_service import DatabaseService

class SolutionFeasibilityVerifier:
    
    def __init__(self):
        self.db_service = DatabaseService()
        
    async def run_verification(self):
        """執行完整的可行性驗證"""
        print("🔍 開始驗證解決方案可行性")
        print(f"⏰ 驗證時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # 1. 資料庫結構檢查
        await self.check_database_structure()
        
        # 2. 資料完整性檢查
        await self.check_data_integrity()
        
        # 3. 關鍵方法檢查
        await self.check_critical_methods()
        
        # 4. N8N API 格式檢查
        await self.check_n8n_api_formats()
        
        # 5. 生成可行性報告
        await self.generate_feasibility_report()
        
    async def check_database_structure(self):
        """檢查資料庫結構"""
        print("\n📊 資料庫結構檢查")
        print("-" * 30)
        
        async with AsyncSessionLocal() as session:
            # 檢查所有表是否存在
            tables_to_check = ['papers', 'paper_sections', 'sentences', 'paper_selections']
            
            for table in tables_to_check:
                result = await session.execute(text(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = '{table}'
                    )
                """))
                exists = result.scalar()
                print(f"  ✅ 表 '{table}': {'存在' if exists else '❌ 不存在'}")
            
            # 檢查關鍵欄位
            print("\n  🔍 檢查關鍵欄位:")
            
            # 檢查 sentences 表的關鍵欄位
            result = await session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'sentences' 
                AND column_name IN ('sentence_text', 'defining_type', 'page_num', 'section_id', 'paper_id')
            """))
            sentence_columns = [row[0] for row in result.fetchall()]
            required_columns = ['sentence_text', 'defining_type', 'page_num', 'section_id', 'paper_id']
            
            for col in required_columns:
                exists = col in sentence_columns
                print(f"    sentences.{col}: {'✅' if exists else '❌'}")
                
    async def check_data_integrity(self):
        """檢查資料完整性"""
        print("\n📈 資料完整性檢查")
        print("-" * 30)
        
        async with AsyncSessionLocal() as session:
            # 統計基本資料
            stats = {}
            
            # 論文數量
            result = await session.execute(text("SELECT COUNT(*) FROM papers"))
            stats['total_papers'] = result.scalar()
            
            # 已選取論文數量
            result = await session.execute(text("""
                SELECT COUNT(*) FROM paper_selections 
                WHERE is_selected = true
            """))
            stats['selected_papers'] = result.scalar()
            
            # 章節數量
            result = await session.execute(text("SELECT COUNT(*) FROM paper_sections"))
            stats['total_sections'] = result.scalar()
            
            # 句子數量
            result = await session.execute(text("SELECT COUNT(*) FROM sentences"))
            stats['total_sentences'] = result.scalar()
            
            # OD/CD 句子數量
            result = await session.execute(text("""
                SELECT 
                    COUNT(CASE WHEN defining_type = 'OD' THEN 1 END) as od_count,
                    COUNT(CASE WHEN defining_type = 'CD' THEN 1 END) as cd_count
                FROM sentences
            """))
            od_cd_stats = result.fetchone()
            stats['od_sentences'] = od_cd_stats[0] if od_cd_stats else 0
            stats['cd_sentences'] = od_cd_stats[1] if od_cd_stats else 0
            
            # 顯示統計結果
            print(f"  📄 總論文數: {stats['total_papers']}")
            print(f"  ✅ 已選取論文數: {stats['selected_papers']}")
            print(f"  📑 總章節數: {stats['total_sections']}")
            print(f"  📝 總句子數: {stats['total_sentences']}")
            print(f"  🔵 OD 句子數: {stats['od_sentences']}")
            print(f"  🟣 CD 句子數: {stats['cd_sentences']}")
            
            # 檢查是否有足夠的測試資料
            self.data_sufficient = (
                stats['selected_papers'] > 0 and 
                stats['total_sections'] > 0 and 
                stats['total_sentences'] > 0
            )
            
            print(f"\n  💡 資料充足性: {'✅ 足夠進行測試' if self.data_sufficient else '❌ 缺乏測試資料'}")
            
    async def check_critical_methods(self):
        """檢查關鍵方法是否存在且可用"""
        print("\n🔧 關鍵方法檢查")
        print("-" * 30)
        
        # 檢查 DatabaseService 中的關鍵方法
        methods_to_check = [
            'get_sentences_by_paper_and_section_type',
            'get_selected_papers', 
            'get_sentences_by_section_id',
            'get_papers_with_sections_summary'
        ]
        
        for method_name in methods_to_check:
            has_method = hasattr(self.db_service, method_name)
            print(f"  db_service.{method_name}: {'✅' if has_method else '❌'}")
            
        # 測試關鍵方法是否能正常執行
        if self.data_sufficient:
            print("\n  🧪 實際方法測試:")
            await self.test_critical_methods()
        else:
            print("\n  ⚠️  跳過方法測試（缺乏測試資料）")
            
    async def test_critical_methods(self):
        """實際測試關鍵方法"""
        async with AsyncSessionLocal() as session:
            try:
                # 測試 get_selected_papers
                selected_papers = await self.db_service.get_selected_papers(session)
                print(f"    get_selected_papers: ✅ (返回 {len(selected_papers)} 篇論文)")
                
                if selected_papers:
                    paper = selected_papers[0]
                    paper_name = paper.file_name or paper.original_filename
                    
                    # 測試 get_sentences_by_paper_and_section_type
                    # 先找一個有句子的章節類型
                    result = await session.execute(text("""
                        SELECT DISTINCT ps.section_type 
                        FROM paper_sections ps 
                        JOIN sentences s ON ps.id = s.section_id 
                        WHERE ps.paper_id = :paper_id 
                        LIMIT 1
                    """), {"paper_id": str(paper.id)})
                    
                    section_type_row = result.fetchone()
                    if section_type_row:
                        section_type = section_type_row[0]
                        sentences = await self.db_service.get_sentences_by_paper_and_section_type(
                            session, paper_name, section_type
                        )
                        print(f"    get_sentences_by_paper_and_section_type: ✅ (返回 {len(sentences)} 個句子)")
                    else:
                        print(f"    get_sentences_by_paper_and_section_type: ⚠️ (該論文沒有句子資料)")
                        
            except Exception as e:
                print(f"    方法測試失敗: ❌ {str(e)}")
                
    async def check_n8n_api_formats(self):
        """檢查 N8N API 格式相容性"""
        print("\n🌐 N8N API 格式檢查")
        print("-" * 30)
        
        # 檢查 N8N 服務是否正確匯入
        try:
            from services.n8n_service import n8n_service
            print("  ✅ N8N 服務匯入成功")
            
            # 檢查關鍵方法
            critical_methods = ['extract_keywords', 'intelligent_section_selection', 'unified_content_analysis']
            for method in critical_methods:
                has_method = hasattr(n8n_service, method)
                print(f"    {method}: {'✅' if has_method else '❌'}")
                
        except Exception as e:
            print(f"  ❌ N8N 服務匯入失敗: {str(e)}")
            
    async def generate_feasibility_report(self):
        """生成可行性報告"""
        print("\n📋 可行性報告")
        print("=" * 60)
        
        # 根據檢查結果評估可行性
        issues = []
        recommendations = []
        
        # 評估資料可用性
        if not self.data_sufficient:
            issues.append("缺乏足夠的測試資料")
            recommendations.append("上傳並處理論文以獲得測試資料")
            
        # 評估方法可用性
        if not hasattr(self.db_service, 'get_sentences_by_paper_and_section_type'):
            issues.append("缺少關鍵資料庫方法")
            recommendations.append("實施 get_sentences_by_paper_and_section_type 方法")
            
        # 生成總結
        if not issues:
            print("✅ 解決方案完全可行")
            print("💡 可以直接開始實施修正方案")
        else:
            print("⚠️  發現以下問題:")
            for i, issue in enumerate(issues, 1):
                print(f"   {i}. {issue}")
                
            print("\n🛠️  建議的修正措施:")
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec}")
                
        print(f"\n🔍 驗證完成於: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

async def main():
    """主函數"""
    verifier = SolutionFeasibilityVerifier()
    await verifier.run_verification()

if __name__ == "__main__":
    asyncio.run(main()) 