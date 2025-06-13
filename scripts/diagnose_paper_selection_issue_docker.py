#!/usr/bin/env python3
"""
論文選取狀態診斷腳本 (Docker 版本)
用於診斷 unified-query 返回"沒有可用的論文資料"問題
"""

import asyncio
import sys
import os
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

async def main():
    """主函數"""
    print("🔧 論文選取狀態診斷開始")
    print(f"⏰ 診斷時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 使用 Docker 環境的資料庫連接
    database_url = "postgresql+asyncpg://postgres:password@paper_analysis_db:5432/paper_analysis"
    
    try:
        engine = create_async_engine(database_url, echo=False)
        session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        print("✅ 資料庫連接初始化成功")
        
        # 執行診斷查詢
        async with session_factory() as session:
            print("\n" + "="*60)
            print("📊 論文與選取狀態一致性檢查")
            print("="*60)
            
            # 檢查論文總數
            total_papers_query = text("SELECT COUNT(*) FROM papers")
            result = await session.execute(total_papers_query)
            total_papers = result.scalar()
            print(f"📄 資料庫中總論文數: {total_papers}")
            
            if total_papers == 0:
                print("❌ 資料庫中沒有論文記錄！")
                print("   請先上傳並處理論文")
                return
            
            # 詳細的診斷查詢
            query = text("""
                SELECT 
                    p.id,
                    p.file_name,
                    p.original_filename,
                    p.processing_status,
                    p.grobid_processed,
                    p.sentences_processed,
                    p.od_cd_processed,
                    ps.is_selected,
                    ps.selected_timestamp,
                    COUNT(DISTINCT sections.id) as section_count,
                    COUNT(DISTINCT sentences.id) as sentence_count,
                    COUNT(DISTINCT CASE WHEN sentences.defining_type = 'OD' THEN sentences.id END) as od_count,
                    COUNT(DISTINCT CASE WHEN sentences.defining_type = 'CD' THEN sentences.id END) as cd_count
                FROM papers p 
                LEFT JOIN paper_selections ps ON p.id = ps.paper_id
                LEFT JOIN paper_sections sections ON p.id = sections.paper_id  
                LEFT JOIN sentences ON p.id = sentences.paper_id
                GROUP BY p.id, p.file_name, p.original_filename, p.processing_status, 
                         p.grobid_processed, p.sentences_processed, p.od_cd_processed,
                         ps.is_selected, ps.selected_timestamp
                ORDER BY p.created_at DESC;
            """)
            
            result = await session.execute(query)
            papers = result.fetchall()
            
            print(f"📋 詳細論文分析:")
            print()
            
            issues = []
            completed_papers = 0
            selected_papers = 0
            
            for paper in papers:
                paper_id = str(paper.id)
                file_name = paper.file_name or paper.original_filename or "未知"
                processing_status = paper.processing_status
                is_selected = paper.is_selected
                section_count = paper.section_count or 0
                sentence_count = paper.sentence_count or 0
                od_count = paper.od_count or 0
                cd_count = paper.cd_count or 0
                
                print(f"📋 論文: {file_name}")
                print(f"   ID: {paper_id}")
                print(f"   處理狀態: {processing_status}")
                print(f"   已選取: {is_selected}")
                print(f"   章節數: {section_count}, 句子數: {sentence_count}")
                print(f"   OD定義數: {od_count}, CD定義數: {cd_count}")
                
                if processing_status == 'completed':
                    completed_papers += 1
                
                if is_selected:
                    selected_papers += 1
                
                # 檢查問題
                paper_issues = []
                
                # 問題1: 已完成處理但未選取
                if processing_status == 'completed' and not is_selected:
                    issue = f"已完成處理但未選取 (paper_id: {paper_id})"
                    paper_issues.append(issue)
                    print(f"   ⚠️  {issue}")
                
                # 問題2: 已完成處理但沒有章節資料
                if processing_status == 'completed' and section_count == 0:
                    issue = f"已完成處理但沒有章節資料 (paper_id: {paper_id})"
                    paper_issues.append(issue)
                    print(f"   ⚠️  {issue}")
                
                # 問題3: 已完成處理但沒有句子資料
                if processing_status == 'completed' and sentence_count == 0:
                    issue = f"已完成處理但沒有句子資料 (paper_id: {paper_id})"
                    paper_issues.append(issue)
                    print(f"   ⚠️  {issue}")
                
                # 問題4: 選取狀態記錄缺失
                if is_selected is None:
                    issue = f"選取狀態記錄缺失 (paper_id: {paper_id})"
                    paper_issues.append(issue)
                    print(f"   ⚠️  {issue}")
                
                if not paper_issues:
                    print(f"   ✅ 狀態正常")
                
                issues.extend(paper_issues)
                print()
            
            # 檢查 get_selected_papers 的模擬查詢
            print("\n" + "="*60)
            print("🔍 get_selected_papers 模擬查詢")
            print("="*60)
            
            selected_query = text("""
                SELECT p.id, p.file_name, p.original_filename, p.processing_status
                FROM papers p
                JOIN paper_selections ps ON p.id = ps.paper_id
                WHERE ps.is_selected = true
                ORDER BY p.created_at DESC;
            """)
            
            result = await session.execute(selected_query)
            selected_papers_detail = result.fetchall()
            
            print(f"📊 get_selected_papers 查詢結果: {len(selected_papers_detail)} 篇論文")
            
            if not selected_papers_detail:
                print("❌ get_selected_papers 返回空列表")
                print("   這是導致 '沒有可用的論文資料' 錯誤的直接原因")
            else:
                print("📋 選取的論文清單:")
                for paper in selected_papers_detail:
                    print(f"   - {paper.original_filename or paper.file_name} (ID: {paper.id})")
                    print(f"     處理狀態: {paper.processing_status}")
            
            # 總結診斷結果
            print("\n" + "="*60)
            print("📋 診斷總結")
            print("="*60)
            
            print(f"📊 統計資訊:")
            print(f"   總論文數: {total_papers}")
            print(f"   已完成處理論文數: {completed_papers}")
            print(f"   已選取論文數: {selected_papers}")
            print(f"   get_selected_papers 查詢結果: {len(selected_papers_detail)}")
            print()
            
            if issues:
                print(f"❌ 發現 {len(issues)} 個問題:")
                for i, issue in enumerate(issues, 1):
                    print(f"   {i}. {issue}")
            else:
                print("✅ 沒有發現資料完整性問題")
            
            if len(selected_papers_detail) == 0:
                print("❌ 關鍵問題: get_selected_papers 返回空列表")
                print("💡 建議解決方案:")
                
                if completed_papers > 0:
                    print("   1. 執行資料修復：為已完成論文建立選取記錄")
                    print("   2. 檢查前端論文選取功能是否正常")
                else:
                    print("   1. 檢查論文處理流程是否完整執行")
                    print("   2. 確認 Grobid 和句子處理服務是否正常")
            
            print(f"\n🔍 診斷完成")
            
        await engine.dispose()
        
    except Exception as e:
        print(f"❌ 診斷過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 