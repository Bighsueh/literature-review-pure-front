#!/usr/bin/env python3
"""
診斷處理問題的腳本
檢查論文處理過程中的狀態設置問題
"""

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.core.database import AsyncSessionLocal
from backend.models.paper import Paper, PaperSection, Sentence
from sqlalchemy import select, func
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def diagnose_papers():
    """診斷論文處理狀態"""
    async with AsyncSessionLocal() as session:
        try:
            # 1. 檢查最近的論文記錄
            logger.info("=== 檢查最近的論文記錄 ===")
            recent_papers_query = select(Paper).order_by(Paper.created_at.desc()).limit(5)
            result = await session.execute(recent_papers_query)
            papers = result.scalars().all()
            
            for paper in papers:
                logger.info(f"論文 ID: {paper.id}")
                logger.info(f"  檔案名稱: {paper.file_name}")
                logger.info(f"  處理狀態: {paper.processing_status}")
                logger.info(f"  Grobid 處理: {paper.grobid_processed}")
                logger.info(f"  句子處理: {paper.sentences_processed}")
                logger.info(f"  OD/CD 處理: {paper.od_cd_processed}")
                logger.info(f"  錯誤訊息: {paper.error_message}")
                
                # 檢查相關的章節和句子數量
                sections_count = await session.execute(
                    select(func.count(PaperSection.id)).where(PaperSection.paper_id == paper.id)
                )
                sentences_count = await session.execute(
                    select(func.count(Sentence.id)).where(Sentence.paper_id == paper.id)
                )
                
                logger.info(f"  章節數量: {sections_count.scalar()}")
                logger.info(f"  句子數量: {sentences_count.scalar()}")
                logger.info("  " + "="*50)
            
            # 2. 檢查有問題的論文
            logger.info("=== 檢查有問題的論文 ===")
            problem_papers_query = select(Paper).where(
                (Paper.processing_status == 'error') | 
                ((Paper.grobid_processed == True) & (Paper.sentences_processed == False))
            )
            result = await session.execute(problem_papers_query)
            problem_papers = result.scalars().all()
            
            for paper in problem_papers:
                logger.warning(f"問題論文 ID: {paper.id}")
                logger.warning(f"  狀態: {paper.processing_status}")
                logger.warning(f"  處理標記: grobid={paper.grobid_processed}, sentences={paper.sentences_processed}, od_cd={paper.od_cd_processed}")
                logger.warning(f"  錯誤: {paper.error_message}")
                
                # 檢查是否有相關資料
                sections_count = await session.execute(
                    select(func.count(PaperSection.id)).where(PaperSection.paper_id == paper.id)
                )
                sentences_count = await session.execute(
                    select(func.count(Sentence.id)).where(Sentence.paper_id == paper.id)
                )
                
                logger.warning(f"  實際資料: 章節={sections_count.scalar()}, 句子={sentences_count.scalar()}")
                
                # 如果有資料但是狀態不對，嘗試修正
                if sentences_count.scalar() > 0 and not paper.sentences_processed:
                    logger.info(f"  -> 發現狀態不一致，嘗試修正...")
                    from sqlalchemy import update
                    await session.execute(
                        update(Paper).where(Paper.id == paper.id).values(
                            sentences_processed=True,
                            processing_status='processing' if paper.processing_status == 'error' else paper.processing_status
                        )
                    )
                    await session.commit()
                    logger.info(f"  -> 已修正論文 {paper.id} 的狀態")
            
            logger.info("=== 診斷完成 ===")
            
        except Exception as e:
            logger.error(f"診斷過程發生錯誤: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(diagnose_papers()) 