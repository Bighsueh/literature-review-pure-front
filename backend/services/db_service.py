from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy import select, update, delete, and_, or_, func, desc
from sqlalchemy.exc import IntegrityError
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from ..models.paper import (
    Paper, PaperSection, Sentence, PaperSelection, ProcessingQueue, SystemSettings,
    PaperCreate, PaperUpdate, SectionCreate, SentenceCreate, 
    ProcessingQueueCreate, ProcessingQueueUpdate, PaperSelectionUpdate,
    PaperResponse, SectionResponse, SentenceResponse, ProcessingQueueResponse,
    SectionSummary, PaperSectionSummary
)

class DatabaseService:
    """資料庫服務類，處理所有資料庫操作"""
    
    async def init_database(self):
        """初始化資料庫"""
        # 這個方法主要是為了相容性，實際初始化在 database.py 中
        pass
    
    async def get_connection(self):
        """獲取資料庫連接 - 相容性方法"""
        # 這是為了相容佇列服務的期望接口
        # 實際的連接管理在 FastAPI 的依賴注入系統中
        return None
    
    # ===== Paper Management =====
    
    async def create_paper(self, db: AsyncSession, paper_data: PaperCreate) -> str:
        """建立新論文記錄"""
        paper = Paper(**paper_data.dict())
        db.add(paper)
        await db.commit()
        await db.refresh(paper)
        return str(paper.id)
    
    async def get_paper_by_id(self, db: AsyncSession, paper_id: str) -> Optional[Paper]:
        """根據ID取得論文"""
        query = select(Paper).where(Paper.id == paper_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_paper_by_hash(self, db: AsyncSession, file_hash: str) -> Optional[Paper]:
        """根據檔案雜湊值取得論文"""
        query = select(Paper).where(Paper.file_hash == file_hash)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_all_papers(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """取得所有論文，包含選取狀態"""
        query = (
            select(Paper, PaperSelection.is_selected)
            .outerjoin(PaperSelection, Paper.id == PaperSelection.paper_id)
            .order_by(desc(Paper.created_at))
        )
        result = await db.execute(query)
        papers = []
        
        for paper, is_selected in result:
            paper_dict = {
                "id": str(paper.id),
                "title": paper.original_filename or paper.file_name,
                "file_path": paper.file_name,
                "file_hash": paper.file_hash,
                "upload_time": paper.upload_timestamp.isoformat() if paper.upload_timestamp else datetime.now().isoformat(),
                "processing_status": paper.processing_status,
                "selected": is_selected if is_selected is not None else False,
                "authors": [],  # Placeholder, to be implemented
                "section_count": 0,  # Placeholder, to be implemented
                "sentence_count": 0,  # Placeholder, to be implemented
                
                # Keep original fields for compatibility if needed elsewhere
                "original_filename": paper.original_filename,
                "file_name": paper.file_name,
                "upload_timestamp": paper.upload_timestamp.isoformat() if paper.upload_timestamp else datetime.now().isoformat(),
                "is_selected": is_selected if is_selected is not None else False,
                "created_at": paper.created_at.isoformat() if paper.created_at else datetime.now().isoformat(),
            }
            papers.append(paper_dict)
        
        return papers
    
    async def update_paper(self, db: AsyncSession, paper_id: str, updates: PaperUpdate) -> bool:
        """更新論文資訊"""
        query = (
            update(Paper)
            .where(Paper.id == paper_id)
            .values(**updates.dict(exclude_unset=True))
        )
        result = await db.execute(query)
        await db.commit()
        return result.rowcount > 0
    
    async def update_paper_status(self, db: AsyncSession, paper_id: str, status: str, error_message: Optional[str] = None) -> bool:
        """更新論文處理狀態"""
        update_data = {"processing_status": status}
        if error_message:
            update_data["error_message"] = error_message
        
        query = update(Paper).where(Paper.id == paper_id).values(**update_data)
        result = await db.execute(query)
        await db.commit()
        return result.rowcount > 0
    
    async def update_paper_grobid_results(self, db: AsyncSession, paper_id: str, grobid_result: Dict[str, Any], status: str = "processing"):
        """保存 Grobid 處理結果並更新狀態"""
        update_data = {
            "processing_status": status,
            "grobid_processed": True,
            "tei_xml": grobid_result.get("tei_xml"),
            "tei_metadata": {
                "title": grobid_result.get("title"),
                "authors": grobid_result.get("authors", []),
                "abstract": grobid_result.get("abstract"),
            },
        }
        await db.execute(
            update(Paper).where(Paper.id == paper_id).values(**update_data)
        )
        # No commit here, part of a larger transaction

    async def get_paper_tei_xml(self, db: AsyncSession, paper_id: str) -> Optional[str]:
        """從資料庫獲取 TEI XML"""
        query = select(Paper.tei_xml).where(Paper.id == paper_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def save_sections_and_sentences(self, db: AsyncSession, paper_id: str, sections_analysis: List[Dict[str, Any]], sentences_data: List[Dict[str, Any]], status: str = "processing"):
        """保存章節和句子資料"""
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        # 1. 批次插入章節
        sections_to_insert = [
            {
                "id": s["section_id"], "paper_id": paper_id, "section_type": s["section_type"],
                "content": s["content"], "section_order": s.get("order"), "word_count": s.get("word_count")
            } for s in sections_analysis
        ]
        if sections_to_insert:
            stmt = pg_insert(PaperSection).values(sections_to_insert)
            stmt = stmt.on_conflict_do_update(
                index_elements=['id'],
                set_={k: getattr(stmt.excluded, k) for k in sections_to_insert[0] if k != 'id'}
            )
            await db.execute(stmt)

        # 2. 批次插入句子
        sentences_to_insert = [
            {
                "id": s["sentence_id"], "paper_id": paper_id, "section_id": s["section_id"],
                "sentence_text": s["text"], "word_count": s.get("word_count")
            } for s in sentences_data
        ]
        if sentences_to_insert:
            stmt = pg_insert(Sentence).values(sentences_to_insert)
            stmt = stmt.on_conflict_do_update(
                index_elements=['id'],
                set_={k: getattr(stmt.excluded, k) for k in sentences_to_insert[0] if k != 'id'}
            )
            await db.execute(stmt)

        # 3. 更新論文狀態
        await db.execute(
            update(Paper).where(Paper.id == paper_id).values(
                sentences_processed=True, processing_status=status
            )
        )
        # No commit here

    async def get_sentences_for_paper(self, db: AsyncSession, paper_id: str) -> List[Dict[str, Any]]:
        """獲取論文的所有句子以進行 OD/CD 分析"""
        query = select(Sentence).where(Sentence.paper_id == paper_id)
        result = await db.execute(query)
        return [
            {
                "id": str(s.id), "text": s.sentence_text, "section_id": str(s.section_id)
            } for s in result.scalars().all()
        ]

    async def save_od_cd_results(self, db: AsyncSession, paper_id: str, od_cd_results: List[Dict[str, Any]], status: str = "processing"):
        """增量更新句子的 OD/CD 分析結果"""
        update_statements = [
            update(Sentence).where(Sentence.id == result['id']).values(
                defining_type=result.get("od_cd_type", "UNKNOWN"),
                analysis_reason=result.get("explanation", ""),
                confidence_score=result.get("confidence", 0.0),
                detection_status=result.get("detection_status", "success")
            ) for result in od_cd_results
        ]
        if update_statements:
            for stmt in update_statements:
                await db.execute(stmt)

        # 更新論文主記錄狀態
        await db.execute(
            update(Paper).where(Paper.id == paper_id).values(
                od_cd_processed=True, processing_status=status
            )
        )
        # No commit here

    async def delete_paper(self, db: AsyncSession, paper_id: str) -> bool:
        """刪除論文及其所有相關資料"""
        try:
            # 依賴順序刪除，確保外鍵約束不會出錯
            await db.execute(delete(Sentence).where(Sentence.paper_id == paper_id))
            await db.execute(delete(PaperSection).where(PaperSection.paper_id == paper_id))
            await db.execute(delete(PaperSelection).where(PaperSelection.paper_id == paper_id))
            await db.execute(delete(ProcessingQueue).where(ProcessingQueue.paper_id == paper_id))
            
            # 最後刪除論文主記錄
            result = await db.execute(delete(Paper).where(Paper.id == paper_id))
            
            await db.commit()
            return result.rowcount > 0
        except Exception as e:
            await db.rollback()
            # 可以在這裡記錄錯誤
            # logger.error(f"刪除論文 {paper_id} 失敗: {e}")
            return False
    
    # ===== Paper Section Management =====
    
    async def create_paper_section(self, db: AsyncSession, section_data: SectionCreate) -> str:
        """建立論文章節"""
        section = PaperSection(**section_data.dict())
        db.add(section)
        await db.commit()
        await db.refresh(section)
        return str(section.id)
    
    async def get_sections_by_paper_id(self, db: AsyncSession, paper_id: str) -> List[SectionResponse]:
        """取得論文的所有章節"""
        query = (
            select(PaperSection)
            .where(PaperSection.paper_id == paper_id)
            .order_by(PaperSection.section_order)
        )
        result = await db.execute(query)
        sections = result.scalars().all()
        return [SectionResponse.from_orm(section) for section in sections]
    
    async def get_section_content(self, db: AsyncSession, section_id: str) -> Optional[str]:
        """取得章節內容"""
        query = select(PaperSection.content).where(PaperSection.id == section_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    # ===== Sentence Management =====
    
    async def create_sentence(self, db: AsyncSession, sentence_data: SentenceCreate) -> str:
        """建立句子記錄"""
        sentence = Sentence(**sentence_data.dict())
        db.add(sentence)
        await db.commit()
        await db.refresh(sentence)
        return str(sentence.id)
    
    async def get_sentences_by_paper_id(self, db: AsyncSession, paper_id: str) -> List[SentenceResponse]:
        """取得論文的所有句子"""
        query = (
            select(Sentence)
            .where(Sentence.paper_id == paper_id)
            .order_by(Sentence.section_id, Sentence.sentence_order)
        )
        result = await db.execute(query)
        sentences = result.scalars().all()
        return [SentenceResponse.from_orm(sentence) for sentence in sentences]
    
    async def search_sentences(self, db: AsyncSession, paper_ids: List[str], 
                             defining_types: Optional[List[str]] = None,
                             keywords: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """搜尋句子"""
        query = (
            select(
                Sentence.sentence_text,
                Sentence.defining_type,
                Sentence.page_num,
                PaperSection.section_type,
                Paper.file_name,
                Paper.id.label('paper_id')
            )
            .join(PaperSection, Sentence.section_id == PaperSection.id)
            .join(Paper, Sentence.paper_id == Paper.id)
            .where(Paper.id.in_(paper_ids))
        )
        
        if defining_types:
            query = query.where(Sentence.defining_type.in_(defining_types))
        
        if keywords:
            keyword_conditions = [
                Sentence.sentence_text.ilike(f"%{keyword}%") for keyword in keywords
            ]
            query = query.where(or_(*keyword_conditions))
        
        result = await db.execute(query)
        return [
            {
                "sentence_text": row.sentence_text,
                "defining_type": row.defining_type,
                "page_num": row.page_num,
                "section_type": row.section_type,
                "file_name": row.file_name,
                "paper_id": str(row.paper_id)
            }
            for row in result
        ]
    
    async def get_definition_sentences(self, db: AsyncSession, paper_id: str, 
                                     section_id: str, types: List[str]) -> List[Dict[str, Any]]:
        """取得定義句子"""
        query = (
            select(Sentence)
            .where(
                and_(
                    Sentence.paper_id == paper_id,
                    Sentence.section_id == section_id,
                    Sentence.defining_type.in_(types)
                )
            )
            .order_by(Sentence.sentence_order)
        )
        result = await db.execute(query)
        sentences = result.scalars().all()
        
        return [
            {
                "text": sentence.sentence_text,
                "type": sentence.defining_type,
                "page_num": sentence.page_num
            }
            for sentence in sentences
        ]
    
    async def search_sentences_by_keywords(self, db: AsyncSession, section_id: str, 
                                         keywords: List[str]) -> List[Dict[str, Any]]:
        """根據關鍵詞搜尋句子"""
        keyword_conditions = [
            Sentence.sentence_text.ilike(f"%{keyword}%") for keyword in keywords
        ]
        
        query = (
            select(Sentence)
            .where(
                and_(
                    Sentence.section_id == section_id,
                    or_(*keyword_conditions)
                )
            )
            .order_by(Sentence.sentence_order)
        )
        result = await db.execute(query)
        sentences = result.scalars().all()
        
        return [
            {
                "text": sentence.sentence_text,
                "page_num": sentence.page_num,
                "defining_type": sentence.defining_type
            }
            for sentence in sentences
        ]
    
    # ===== Paper Selection Management =====
    
    async def get_selected_papers(self, db: AsyncSession) -> List[PaperResponse]:
        """取得已選取的論文"""
        query = (
            select(Paper)
            .join(PaperSelection, Paper.id == PaperSelection.paper_id)
            .where(PaperSelection.is_selected == True)
            .order_by(desc(Paper.created_at))
        )
        result = await db.execute(query)
        papers = result.scalars().all()
        
        return [
            PaperResponse(
                **{
                    "id": str(paper.id),
                    "file_name": paper.file_name,
                    "original_filename": paper.original_filename,
                    "file_size": paper.file_size,
                    "upload_timestamp": paper.upload_timestamp,
                    "processing_status": paper.processing_status,
                    "grobid_processed": paper.grobid_processed,
                    "sentences_processed": paper.sentences_processed,
                    "pdf_deleted": paper.pdf_deleted,
                    "error_message": paper.error_message,
                    "processing_completed_at": paper.processing_completed_at,
                    "created_at": paper.created_at,
                    "is_selected": True
                }
            )
            for paper in papers
        ]
    
    async def set_paper_selection(self, db: AsyncSession, paper_id: str, is_selected: bool) -> bool:
        """設定論文選取狀態"""
        # 先嘗試更新
        update_query = (
            update(PaperSelection)
            .where(PaperSelection.paper_id == paper_id)
            .values(is_selected=is_selected, selected_timestamp=func.current_timestamp())
        )
        result = await db.execute(update_query)
        
        # 如果沒有更新到任何記錄，表示不存在，需要建立新記錄
        if result.rowcount == 0:
            selection = PaperSelection(paper_id=paper_id, is_selected=is_selected)
            db.add(selection)
        
        await db.commit()
        return True
    
    async def mark_paper_selected(self, db: AsyncSession, paper_id: str) -> bool:
        """標記論文為已選取"""
        return await self.set_paper_selection(db, paper_id, True)
    
    async def select_all_papers(self, db: AsyncSession) -> bool:
        """全選所有論文"""
        # 取得所有論文ID
        papers_query = select(Paper.id)
        result = await db.execute(papers_query)
        paper_ids = [str(row[0]) for row in result]
        
        # 為每個論文設定選取狀態
        for paper_id in paper_ids:
            await self.set_paper_selection(db, paper_id, True)
        
        return True
    
    async def deselect_all_papers(self, db: AsyncSession) -> bool:
        """取消全選"""
        query = update(PaperSelection).values(is_selected=False)
        await db.execute(query)
        await db.commit()
        return True
    
    # ===== Processing Queue Management =====
    
    async def add_to_queue(self, db: AsyncSession, queue_data: ProcessingQueueCreate) -> str:
        """加入處理佇列"""
        queue_item = ProcessingQueue(**queue_data.dict())
        db.add(queue_item)
        await db.commit()
        await db.refresh(queue_item)
        return str(queue_item.id)
    
    async def update_queue_status(self, db: AsyncSession, paper_id: str, processing_stage: str, 
                                status: str, error_message: Optional[str] = None) -> bool:
        """更新佇列狀態"""
        update_data = {"status": status}
        if error_message:
            update_data["error_message"] = error_message
        if status == "processing":
            update_data["started_at"] = func.current_timestamp()
        elif status in ["completed", "failed"]:
            update_data["completed_at"] = func.current_timestamp()
        
        query = (
            update(ProcessingQueue)
            .where(
                and_(
                    ProcessingQueue.paper_id == paper_id,
                    ProcessingQueue.processing_stage == processing_stage
                )
            )
            .values(**update_data)
        )
        result = await db.execute(query)
        await db.commit()
        return result.rowcount > 0
    
    async def get_processing_queue_info(self, db: AsyncSession, paper_id: str) -> Optional[Dict[str, Any]]:
        """取得處理佇列資訊"""
        query = (
            select(ProcessingQueue)
            .where(ProcessingQueue.paper_id == paper_id)
            .order_by(desc(ProcessingQueue.created_at))
        )
        result = await db.execute(query)
        queue_item = result.scalar_one_or_none()
        
        if queue_item:
            return {
                "stage": queue_item.processing_stage,
                "status": queue_item.status,
                "progress": queue_item.processing_details.get("progress", 0) if queue_item.processing_details else 0,
                "error_message": queue_item.error_message
            }
        return None
    
    async def update_processing_details(self, db: AsyncSession, paper_id: str, details: Dict[str, Any]) -> bool:
        """更新處理詳細資訊"""
        query = (
            update(ProcessingQueue)
            .where(ProcessingQueue.paper_id == paper_id)
            .values(processing_details=details)
        )
        result = await db.execute(query)
        await db.commit()
        return result.rowcount > 0
    
    async def mark_completed(self, db: AsyncSession, paper_id: str) -> bool:
        """標記處理完成"""
        query = (
            update(ProcessingQueue)
            .where(ProcessingQueue.paper_id == paper_id)
            .values(
                status="completed",
                completed_at=func.current_timestamp()
            )
        )
        result = await db.execute(query)
        await db.commit()
        return result.rowcount > 0
    
    async def mark_failed(self, db: AsyncSession, paper_id: str, error_message: str) -> bool:
        """標記處理失敗"""
        query = (
            update(ProcessingQueue)
            .where(ProcessingQueue.paper_id == paper_id)
            .values(
                status="failed",
                error_message=error_message,
                completed_at=func.current_timestamp()
            )
        )
        result = await db.execute(query)
        await db.commit()
        return result.rowcount > 0
    
    async def reset_paper_for_retry(self, db: AsyncSession, paper_id: str) -> bool:
        """重設論文狀態以進行重試"""
        # 重設論文狀態
        paper_update = (
            update(Paper)
            .where(Paper.id == paper_id)
            .values(processing_status="processing", error_message=None)
        )
        await db.execute(paper_update)
        
        # 重設佇列狀態
        queue_update = (
            update(ProcessingQueue)
            .where(ProcessingQueue.paper_id == paper_id)
            .values(
                status="pending",
                error_message=None,
                retry_count=ProcessingQueue.retry_count + 1,
                started_at=None,
                completed_at=None
            )
        )
        await db.execute(queue_update)
        
        await db.commit()
        return True
    
    # ===== Papers with Sections Summary =====
    
    async def get_papers_with_sections_summary(self, db: AsyncSession, paper_ids: List[str]) -> List[PaperSectionSummary]:
        """取得論文的section摘要資訊"""
        query = (
            select(Paper, PaperSection, func.count(Sentence.id).label('total_sentences'))
            .outerjoin(PaperSection, Paper.id == PaperSection.paper_id)
            .outerjoin(Sentence, PaperSection.id == Sentence.section_id)
            .where(Paper.id.in_(paper_ids))
            .group_by(Paper.id, PaperSection.id)
            .order_by(Paper.file_name, PaperSection.section_order)
        )
        result = await db.execute(query)
        
        # 組織數據
        papers_dict = {}
        for paper, section, total_sentences in result:
            paper_id = str(paper.id)
            if paper_id not in papers_dict:
                papers_dict[paper_id] = {
                    "file_name": paper.file_name,
                    "sections": []
                }
            
            if section:
                # 取得該section的OD/CD統計
                od_count_query = (
                    select(func.count(Sentence.id))
                    .where(
                        and_(
                            Sentence.section_id == section.id,
                            Sentence.defining_type == 'OD'
                        )
                    )
                )
                od_result = await db.execute(od_count_query)
                od_count = od_result.scalar() or 0
                
                cd_count_query = (
                    select(func.count(Sentence.id))
                    .where(
                        and_(
                            Sentence.section_id == section.id,
                            Sentence.defining_type == 'CD'
                        )
                    )
                )
                cd_result = await db.execute(cd_count_query)
                cd_count = cd_result.scalar() or 0
                
                section_summary = SectionSummary(
                    section_type=section.section_type,
                    page_num=section.page_num,
                    word_count=section.word_count or 0,
                    brief_content=section.content[:100] + "..." if len(section.content) > 100 else section.content,
                    od_count=od_count,
                    cd_count=cd_count,
                    total_sentences=total_sentences or 0
                )
                papers_dict[paper_id]["sections"].append(section_summary)
        
        return [
            PaperSectionSummary(**paper_data) 
            for paper_data in papers_dict.values()
        ]

# 建立服務實例
db_service = DatabaseService() 