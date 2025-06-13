#!/usr/bin/env python3
"""
調試 _generate_papers_summary 方法
"""

import asyncio
import sys
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

async def debug_papers_summary():
    """調試論文摘要生成過程"""
    print("🔧 _generate_papers_summary 調試開始")
    print(f"⏰ 調試時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    database_url = "postgresql+asyncpg://postgres:password@paper_analysis_db:5432/paper_analysis"
    
    try:
        engine = create_async_engine(database_url, echo=False)
        session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        print("✅ 資料庫連接初始化成功")
        
        async with session_factory() as session:
            # 模擬 unified_query_processor 的步驟
            print("\n" + "="*60)
            print("🔍 步驟1: 檢查 get_selected_papers")
            print("="*60)
            
            # 模擬 get_selected_papers 查詢
            selected_query = text("""
                SELECT id, file_name, original_filename, processing_status
                FROM papers p
                JOIN paper_selections ps ON p.id = ps.paper_id
                WHERE ps.is_selected = true
                ORDER BY p.created_at DESC;
            """)
            
            result = await session.execute(selected_query)
            selected_papers = result.fetchall()
            
            print(f"📊 get_selected_papers 結果: {len(selected_papers)} 篇論文")
            
            if not selected_papers:
                print("❌ get_selected_papers 返回空列表")
                return
            
            # 模擬 papers_data 生成
            papers_data = []
            for paper in selected_papers:
                paper_data = {
                    'id': str(paper.id),
                    'filename': paper.original_filename or paper.file_name,
                    'title': paper.original_filename or paper.file_name
                }
                papers_data.append(paper_data)
                print(f"   - {paper_data['filename']} (ID: {paper_data['id']})")
            
            print(f"\n" + "="*60)
            print("🔍 步驟2: 模擬 _generate_papers_summary")
            print("="*60)
            
            # 模擬 _generate_papers_summary 的邏輯
            available_papers = []
            
            for paper in papers_data:
                print(f"\n📋 處理論文: {paper['filename']}")
                
                try:
                    # 獲取論文的章節資訊 (模擬 db_service.get_paper_sections)
                    sections_query = text("""
                        SELECT id, section_type, page_num, content
                        FROM paper_sections
                        WHERE paper_id = :paper_id
                        ORDER BY section_order;
                    """)
                    
                    result = await session.execute(sections_query, {"paper_id": paper['id']})
                    sections = result.fetchall()
                    
                    print(f"   📄 找到 {len(sections)} 個章節")
                    
                    if not sections:
                        print("   ⚠️  沒有章節資料，跳過此論文")
                        continue
                    
                    paper_summary = {
                        'file_name': paper['filename'],
                        'paper_id': paper['id'],
                        'title': paper.get('title', ''),
                        'sections': []
                    }
                    
                    for section in sections:
                        print(f"   📑 處理章節: {section.section_type}")
                        
                        # 獲取章節句子 (模擬 db_service.get_section_sentences)
                        sentences_query = text("""
                            SELECT id, sentence_text, defining_type
                            FROM sentences
                            WHERE section_id = :section_id;
                        """)
                        
                        result = await session.execute(sentences_query, {"section_id": str(section.id)})
                        sentences = result.fetchall()
                        
                        print(f"      🔤 找到 {len(sentences)} 個句子")
                        
                        # 計算OD/CD統計
                        od_count = len([s for s in sentences if s.defining_type == 'OD'])
                        cd_count = len([s for s in sentences if s.defining_type == 'CD'])
                        
                        section_summary = {
                            'section_id': str(section.id),
                            'section_type': section.section_type,
                            'page_num': section.page_num or 0,
                            'word_count': len(section.content.split()) if section.content else 0,
                            'brief_content': (section.content or '')[:200] + "...",
                            'od_count': od_count,
                            'cd_count': cd_count,
                            'total_sentences': len(sentences)
                        }
                        
                        print(f"      📊 OD: {od_count}, CD: {cd_count}, 總句子: {len(sentences)}")
                        
                        paper_summary['sections'].append(section_summary)
                    
                    available_papers.append(paper_summary)
                    print(f"   ✅ 論文摘要生成成功，包含 {len(paper_summary['sections'])} 個章節")
                    
                except Exception as e:
                    print(f"   ❌ 處理論文 {paper['filename']} 時出錯: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            print(f"\n" + "="*60)
            print("📋 摘要生成結果")
            print("="*60)
            
            print(f"📊 生成了 {len(available_papers)} 篇論文的摘要")
            
            if not available_papers:
                print("❌ 摘要生成返回空列表")
                print("   這是導致 '沒有可用的論文資料' 錯誤的根本原因")
            else:
                for summary in available_papers:
                    file_name = summary.get('file_name', '未知')
                    sections_count = len(summary.get('sections', []))
                    print(f"   - {file_name}: {sections_count} 個章節")
            
            print(f"\n🔍 調試完成")
            
        await engine.dispose()
        
    except Exception as e:
        print(f"❌ 調試過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_papers_summary()) 