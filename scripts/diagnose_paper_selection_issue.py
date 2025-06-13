#!/usr/bin/env python3
"""
論文選取狀態診斷腳本
用於診斷 unified-query 返回"沒有可用的論文資料"問題
"""

import asyncio
import sys
import os
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# 添加專案根目錄到路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.database import get_database_url
from backend.services.db_service import db_service
from backend.core.logging import get_logger

logger = get_logger(__name__)

class PaperSelectionDiagnostic:
    """論文選取狀態診斷器"""
    
    def __init__(self):
        self.engine = None
        self.session_factory = None
    
    async def initialize(self):
        """初始化資料庫連接"""
        try:
            database_url = get_database_url()
            self.engine = create_async_engine(database_url, echo=False)
            self.session_factory = sessionmaker(
                self.engine, class_=AsyncSession, expire_on_commit=False
            )
            logger.info("資料庫連接初始化成功")
        except Exception as e:
            logger.error(f"資料庫連接初始化失敗: {e}")
            raise
    
    async def check_papers_and_selections(self):
        """檢查論文與選取狀態的一致性"""
        print("\n" + "="*60)
        print("📊 論文與選取狀態一致性檢查")
        print("="*60)
        
        async with self.session_factory() as session:
            # 執行詳細的診斷查詢
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
            
            if not papers:
                print("❌ 沒有找到任何論文記錄")
                return []
            
            print(f"📄 找到 {len(papers)} 篇論文")
            print()
            
            issues = []
            
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
            
            return issues
    
    async def check_selected_papers_api(self):
        """檢查 get_selected_papers API 的實際返回結果"""
        print("\n" + "="*60)
        print("🔍 get_selected_papers API 檢查")
        print("="*60)
        
        async with self.session_factory() as session:
            try:
                selected_papers = await db_service.get_selected_papers(session)
                
                print(f"📊 API 返回選取論文數量: {len(selected_papers)}")
                
                if not selected_papers:
                    print("❌ get_selected_papers 返回空列表")
                    print("   這是導致 '沒有可用的論文資料' 錯誤的直接原因")
                    return []
                
                print("📋 選取的論文清單:")
                for paper in selected_papers:
                    print(f"   - {paper.original_filename or paper.file_name} (ID: {paper.id})")
                    print(f"     處理狀態: {paper.processing_status}")
                
                return selected_papers
                
            except Exception as e:
                print(f"❌ get_selected_papers API 呼叫失敗: {e}")
                return []
    
    async def check_papers_summary_generation(self):
        """檢查論文摘要生成過程"""
        print("\n" + "="*60)
        print("📝 論文摘要生成檢查")
        print("="*60)
        
        # 首先檢查選取的論文
        async with self.session_factory() as session:
            selected_papers = await db_service.get_selected_papers(session)
            
            if not selected_papers:
                print("❌ 沒有選取的論文，無法生成摘要")
                return
            
            # 模擬 unified_query_processor._generate_papers_summary 的邏輯
            from backend.services.unified_query_service import unified_query_processor
            
            papers_data = []
            for paper in selected_papers:
                papers_data.append({
                    'id': str(paper.id),
                    'filename': paper.original_filename or paper.file_name,
                    'title': paper.original_filename or paper.file_name
                })
            
            print(f"📊 嘗試生成 {len(papers_data)} 篇論文的摘要")
            
            try:
                # 呼叫實際的摘要生成方法
                papers_summary = await unified_query_processor._generate_papers_summary(papers_data)
                
                print(f"📄 成功生成摘要，包含 {len(papers_summary)} 篇論文")
                
                if not papers_summary:
                    print("❌ 摘要生成返回空列表")
                    print("   這是導致 '沒有可用的論文資料' 錯誤的根本原因")
                
                for summary in papers_summary:
                    file_name = summary.get('file_name', '未知')
                    sections_count = len(summary.get('sections', []))
                    print(f"   - {file_name}: {sections_count} 個章節")
                
                return papers_summary
                
            except Exception as e:
                print(f"❌ 論文摘要生成失敗: {e}")
                logger.error(f"論文摘要生成失敗: {e}", exc_info=True)
                return []
    
    async def run_full_diagnosis(self):
        """執行完整診斷"""
        print("🔧 論文選取狀態診斷開始")
        print(f"⏰ 診斷時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        await self.initialize()
        
        # 步驟1: 檢查資料完整性
        issues = await self.check_papers_and_selections()
        
        # 步驟2: 檢查 API 呼叫
        selected_papers = await self.check_selected_papers_api()
        
        # 步驟3: 檢查摘要生成
        papers_summary = await self.check_papers_summary_generation()
        
        # 總結診斷結果
        print("\n" + "="*60)
        print("📋 診斷總結")
        print("="*60)
        
        if issues:
            print(f"❌ 發現 {len(issues)} 個問題:")
            for i, issue in enumerate(issues, 1):
                print(f"   {i}. {issue}")
        else:
            print("✅ 沒有發現資料完整性問題")
        
        if not selected_papers:
            print("❌ 關鍵問題: get_selected_papers 返回空列表")
        
        if not papers_summary:
            print("❌ 關鍵問題: 論文摘要生成失敗")
        
        print(f"\n🔍 診斷完成")
        
        await self.engine.dispose()
        
        return {
            'issues': issues,
            'selected_papers_count': len(selected_papers),
            'papers_summary_count': len(papers_summary) if papers_summary else 0
        }

async def main():
    """主函數"""
    diagnostic = PaperSelectionDiagnostic()
    result = await diagnostic.run_full_diagnosis()
    
    # 返回診斷結果給呼叫者
    return result

if __name__ == "__main__":
    asyncio.run(main()) 