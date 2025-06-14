import asyncio
from core.database import AsyncSessionLocal
from models.paper import Paper, PaperSection, Sentence
from sqlalchemy import select, func, update

async def diagnose():
    async with AsyncSessionLocal() as session:
        # 檢查最近的論文
        result = await session.execute(select(Paper).order_by(Paper.created_at.desc()).limit(3))
        papers = result.scalars().all()
        
        for paper in papers:
            print(f'論文 ID: {paper.id}')
            print(f'  檔案: {paper.file_name}')
            print(f'  狀態: {paper.processing_status}')
            print(f'  grobid_processed: {paper.grobid_processed}')
            print(f'  sentences_processed: {paper.sentences_processed}')
            print(f'  od_cd_processed: {paper.od_cd_processed}')
            print(f'  錯誤: {paper.error_message}')
            
            # 檢查章節和句子數量
            sections_count = await session.execute(select(func.count(PaperSection.id)).where(PaperSection.paper_id == paper.id))
            sentences_count = await session.execute(select(func.count(Sentence.id)).where(Sentence.paper_id == paper.id))
            
            print(f'  章節數: {sections_count.scalar()}')
            print(f'  句子數: {sentences_count.scalar()}')
            
            # 如果有句子但是狀態為False，修正它
            if sentences_count.scalar() > 0 and not paper.sentences_processed:
                print(f'  -> 修正狀態不一致問題')
                await session.execute(
                    update(Paper).where(Paper.id == paper.id).values(sentences_processed=True)
                )
                await session.commit()
                print(f'  -> 已修正')
            print('-' * 50)

if __name__ == "__main__":
    asyncio.run(diagnose()) 