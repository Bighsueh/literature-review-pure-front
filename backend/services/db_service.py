import asyncio
import time
from uuid import UUID
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, desc, and_, or_, func
from sqlalchemy.dialects.postgresql import insert as pg_insert

from ..models.paper import (
    Paper, PaperSection, Sentence, PaperSelection, ProcessingQueue,
    PaperCreate, PaperUpdate, PaperResponse,
    SectionCreate, SectionResponse,
    SentenceCreate, SentenceResponse,
    ProcessingQueueCreate, ProcessingQueueResponse,
    PaperSectionSummary, SectionSummary
)
from ..core.logging import get_logger

logger = get_logger(__name__)

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
        """取得所有論文，包含選取狀態和正確的統計數據"""
        query = (
            select(
                Paper, 
                PaperSelection.is_selected,
                func.count(func.distinct(PaperSection.id)).label('section_count'),
                func.count(func.distinct(Sentence.id)).label('sentence_count')
            )
            .outerjoin(PaperSelection, Paper.id == PaperSelection.paper_id)
            .outerjoin(PaperSection, Paper.id == PaperSection.paper_id)
            .outerjoin(Sentence, Paper.id == Sentence.paper_id)
            .group_by(Paper.id, PaperSelection.is_selected)
            .order_by(desc(Paper.created_at))
        )
        result = await db.execute(query)
        papers = []
        
        for paper, is_selected, section_count, sentence_count in result:
            paper_dict = {
                "id": str(paper.id),
                "title": paper.original_filename or paper.file_name,
                "file_path": paper.file_name,
                "file_hash": paper.file_hash,
                "upload_time": paper.upload_timestamp.isoformat() if paper.upload_timestamp else datetime.now().isoformat(),
                "processing_status": paper.processing_status,
                "selected": is_selected if is_selected is not None else False,
                "authors": [],  # Placeholder, to be implemented
                "section_count": section_count or 0,  # 修復：使用真實計數
                "sentence_count": sentence_count or 0,  # 修復：使用真實計數
                
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
        logger.info(f"開始儲存章節和句子資料 - paper_id: {paper_id}, sections: {len(sections_analysis)}, sentences: {len(sentences_data)}")
        
        try:
            # 1. 批次插入章節
            sections_to_insert = []
            for s in sections_analysis:
                if not s.get("section_id") or not s.get("content"):
                    logger.warning(f"跳過無效章節資料: {s}")
                    continue
                    
                sections_to_insert.append({
                    "id": s["section_id"], 
                    "paper_id": paper_id, 
                    "section_type": s["section_type"],
                    "content": s["content"], 
                    "section_order": s.get("order"), 
                    "word_count": s.get("word_count")
                })
            
            if sections_to_insert:
                logger.info(f"準備插入 {len(sections_to_insert)} 個章節")
                stmt = pg_insert(PaperSection).values(sections_to_insert)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['id'],
                    set_={k: getattr(stmt.excluded, k) for k in sections_to_insert[0] if k != 'id'}
                )
                result = await db.execute(stmt)
                logger.info(f"章節插入完成，affected rows: {result.rowcount}")
            else:
                logger.error("沒有有效的章節資料可插入")
                raise ValueError("章節資料為空或無效")

            # 2. 批次插入句子
            sentences_to_insert = []
            for s in sentences_data:
                if not s.get("sentence_id") or not s.get("text"):
                    logger.warning(f"跳過無效句子資料: {s}")
                    continue
                    
                sentences_to_insert.append({
                    "id": s["sentence_id"], 
                    "paper_id": paper_id, 
                    "section_id": s["section_id"],
                    "content": s["text"], 
                    "word_count": s.get("word_count"),
                    "sentence_order": s.get("order", 0),
                    "detection_status": "unknown",
                    "retry_count": 0
                })
            
            if sentences_to_insert:
                logger.info(f"準備插入 {len(sentences_to_insert)} 個句子")
                stmt = pg_insert(Sentence).values(sentences_to_insert)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['id'],
                    set_={k: getattr(stmt.excluded, k) for k in sentences_to_insert[0] if k != 'id'}
                )
                result = await db.execute(stmt)
                logger.info(f"句子插入完成，affected rows: {result.rowcount}")
            else:
                logger.error("沒有有效的句子資料可插入")
                raise ValueError("句子資料為空或無效")

            # 3. 更新論文狀態
            await db.execute(
                update(Paper).where(Paper.id == paper_id).values(
                    sentences_processed=True, processing_status=status
                )
            )
            
            # 4. 關鍵修復：確保提交事務
            await db.commit()
            logger.info(f"章節和句子資料已成功提交到資料庫 - paper_id: {paper_id}")
            
            # 5. 驗證資料是否真的插入成功
            sections_count = await db.execute(
                select(func.count(PaperSection.id)).where(PaperSection.paper_id == paper_id)
            )
            sentences_count = await db.execute(
                select(func.count(Sentence.id)).where(Sentence.paper_id == paper_id)
            )
            
            actual_sections = sections_count.scalar()
            actual_sentences = sentences_count.scalar()
            
            logger.info(f"驗證結果 - paper_id: {paper_id}, 實際章節數: {actual_sections}, 實際句子數: {actual_sentences}")
            
            if actual_sections == 0 or actual_sentences == 0:
                raise ValueError(f"資料驗證失敗 - sections: {actual_sections}, sentences: {actual_sentences}")
                
        except Exception as e:
            logger.error(f"儲存章節和句子資料失敗 - paper_id: {paper_id}, 錯誤: {str(e)}", exc_info=True)
            await db.rollback()
            # 更新論文狀態為錯誤
            await db.execute(
                update(Paper).where(Paper.id == paper_id).values(
                    processing_status="error", 
                    error_message=f"章節和句子資料儲存失敗: {str(e)}"
                )
            )
            await db.commit()
            raise

    async def get_sentences_for_paper(self, db: AsyncSession, paper_id: str) -> List[Dict[str, Any]]:
        """獲取論文的所有句子以進行 OD/CD 分析"""
        query = select(Sentence).where(Sentence.paper_id == paper_id)
        result = await db.execute(query)
        return [
            {
                "id": str(s.id), "text": s.content, "section_id": str(s.section_id)
            } for s in result.scalars().all()
        ]

    async def save_od_cd_results(self, db: AsyncSession, paper_id: str, od_cd_results: List[Dict[str, Any]], status: str = "processing"):
        """增量更新句子的檢測分析結果"""
        update_statements = [
            update(Sentence).where(Sentence.id == result['id']).values(
                has_objective=result.get("has_objective", None),
                has_dataset=result.get("has_dataset", None),
                has_contribution=result.get("has_contribution", None),
                explanation=result.get("explanation", ""),
                detection_status=result.get("detection_status", "success")
            ) for result in od_cd_results
        ]
        if update_statements:
            for stmt in update_statements:
                await db.execute(stmt)

        # 更新論文主記錄狀態
        await db.execute(
            update(Paper).where(Paper.id == paper_id).values(
                od_cd_processed=True, 
                sentences_processed=True,  # 添加這個標記
                processing_status=status
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
                Sentence.content,
                Sentence.detection_status,
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
                Sentence.content.ilike(f"%{keyword}%") for keyword in keywords
            ]
            query = query.where(or_(*keyword_conditions))
        
        result = await db.execute(query)
        return [
            {
                "content": row.content,
                "detection_status": row.detection_status,
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
                "text": sentence.content,
                "detection_status": sentence.detection_status,
                "has_objective": sentence.has_objective,
                "has_dataset": sentence.has_dataset,
                "has_contribution": sentence.has_contribution
            }
            for sentence in sentences
        ]
    
    async def search_sentences_by_keywords(self, db: AsyncSession, section_id: str, 
                                         keywords: List[str]) -> List[Dict[str, Any]]:
        """根據關鍵詞搜尋句子"""
        keyword_conditions = [
            Sentence.content.ilike(f"%{keyword}%") for keyword in keywords
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
                "text": sentence.content,
                "detection_status": sentence.detection_status,
                "has_objective": sentence.has_objective,
                "has_dataset": sentence.has_dataset,
                "has_contribution": sentence.has_contribution
            }
            for sentence in sentences
        ]

    async def get_sentences_by_section_id(self, db: AsyncSession, section_id: str) -> List[Dict[str, Any]]:
        """取得章節的所有句子"""
        query = (
            select(Sentence)
            .where(Sentence.section_id == section_id)
            .order_by(Sentence.sentence_order)
        )
        result = await db.execute(query)
        sentences = result.scalars().all()
        
        return [
            {
                "text": sentence.content,
                "sentence_order": sentence.sentence_order,
                "id": str(sentence.id),
                "detection_status": sentence.detection_status,
                "has_objective": sentence.has_objective,
                "has_dataset": sentence.has_dataset,
                "has_contribution": sentence.has_contribution
            }
            for sentence in sentences
        ]
    
    # ===== Paper Selection Management =====
    
    async def get_selected_papers(self, db: AsyncSession) -> List[PaperResponse]:
        """取得已選取的論文"""
        try:
            logger.info("開始查詢已選取的論文")
            
            query = (
                select(Paper)
                .join(PaperSelection, Paper.id == PaperSelection.paper_id)
                .where(PaperSelection.is_selected == True)
                .order_by(desc(Paper.created_at))
            )
            result = await db.execute(query)
            papers = result.scalars().all()
            
            logger.info(f"查詢到 {len(papers)} 篇已選取的論文")
            
            # 手動建立 PaperResponse，確保 UUID 正確轉換為字串
            return [
                PaperResponse(
                    id=str(paper.id),
                    file_name=paper.file_name,
                    original_filename=paper.original_filename,
                    file_size=paper.file_size,
                    upload_timestamp=paper.upload_timestamp,
                    processing_status=paper.processing_status,
                    grobid_processed=paper.grobid_processed,
                    sentences_processed=paper.sentences_processed,
                    od_cd_processed=paper.od_cd_processed,
                    pdf_deleted=paper.pdf_deleted,
                    error_message=paper.error_message,
                    processing_completed_at=paper.processing_completed_at,
                    created_at=paper.created_at,
                    is_selected=True
                )
                for paper in papers
            ]
             
        except Exception as e:
            logger.error(f"取得已選取論文失敗: {e}", exc_info=True)
            # 返回空列表而不是拋出異常，確保系統穩定性
            return []
    
    async def get_sentences_by_paper_and_section_type(
        self, 
        db: AsyncSession, 
        paper_name: str, 
        section_type: str
    ) -> List[Dict[str, Any]]:
        """根據論文名稱和章節類型獲取句子（新增方法，避免依賴section_id）"""
        try:
            # 首先找到對應的論文
            paper_query = (
                select(Paper)
                .where(
                    or_(
                        Paper.file_name == paper_name,
                        Paper.original_filename == paper_name
                    )
                )
            )
            paper_result = await db.execute(paper_query)
            paper = paper_result.scalar_one_or_none()
            
            if not paper:
                logger.warning(f"找不到論文: {paper_name}")
                return []
            
            # 改為不區分大小寫比對 section_type
            from sqlalchemy import func

            query = (
                select(Sentence, PaperSection)
                .join(PaperSection, Sentence.section_id == PaperSection.id)
                .where(
                    and_(
                        Sentence.paper_id == paper.id,
                        func.lower(PaperSection.section_type) == section_type.lower()
                    )
                )
                .order_by(Sentence.sentence_order)
            )
            result = await db.execute(query)
            sentence_section_pairs = result.all()
            
            sentences = []
            for sentence, section in sentence_section_pairs:
                sentences.append({
                    "text": sentence.content,
                    "sentence_order": sentence.sentence_order,
                    "id": str(sentence.id),
                    "section_id": str(sentence.section_id),
                    "detection_status": sentence.detection_status,
                    "has_objective": sentence.has_objective,
                    "has_dataset": sentence.has_dataset,
                    "has_contribution": sentence.has_contribution,
                    "explanation": sentence.explanation,
                    "page_num": section.page_num  # 添加頁碼資訊
                })
            
            logger.info(f"找到 {len(sentences)} 個句子 for paper: {paper_name}, section: {section_type}")
            return sentences
            
        except Exception as e:
            logger.error(f"根據論文名稱和章節類型查詢句子失敗: {e}")
            return []
    
    async def set_paper_selection(self, db: AsyncSession, paper_id: str, is_selected: bool) -> bool:
        """設定論文選取狀態"""
        start_time = time.time()
        logger.info(f"開始設定論文選取狀態 - paper_id: {paper_id}, is_selected: {is_selected}")
        
        try:
            # 驗證 paper_id 格式
            try:
                UUID(paper_id)
            except ValueError:
                logger.error(f"無效的論文ID格式: {paper_id}")
                return False
            
            # 使用超時保護包裝資料庫操作
            async def _perform_database_operation():
                # 先嘗試更新現有記錄
                logger.debug(f"嘗試更新現有選取記錄 - paper_id: {paper_id}")
                update_query = (
                    update(PaperSelection)
                    .where(PaperSelection.paper_id == paper_id)
                    .values(is_selected=is_selected, selected_timestamp=func.current_timestamp())
                )
                result = await db.execute(update_query)
                
                # 如果沒有更新到任何記錄，表示不存在，需要建立新記錄
                if result.rowcount == 0:
                    logger.debug(f"創建新的選取記錄 - paper_id: {paper_id}")
                    selection = PaperSelection(paper_id=paper_id, is_selected=is_selected)
                    db.add(selection)
                
                # 提交事務
                logger.debug(f"提交資料庫事務 - paper_id: {paper_id}")
                await db.commit()
                return result.rowcount
            
            # 設定5秒超時
            try:
                updated_rows = await asyncio.wait_for(_perform_database_operation(), timeout=5.0)
                processing_time = time.time() - start_time
                
                if updated_rows == 0:
                    logger.info(f"創建新選取記錄成功 - paper_id: {paper_id}, is_selected: {is_selected}, 處理時間: {processing_time:.3f}s")
                else:
                    logger.info(f"更新現有選取記錄成功 - paper_id: {paper_id}, is_selected: {is_selected}, 處理時間: {processing_time:.3f}s")
                
                return True
                
            except asyncio.TimeoutError:
                processing_time = time.time() - start_time
                logger.error(f"資料庫操作超時 - paper_id: {paper_id}, 超時時間: 5秒, 實際處理時間: {processing_time:.3f}s")
                
                # 嘗試回滾事務
                try:
                    await db.rollback()
                    logger.debug(f"事務回滾成功 - paper_id: {paper_id}")
                except Exception as rollback_error:
                    logger.error(f"事務回滾失敗 - paper_id: {paper_id}, 錯誤: {rollback_error}")
                
                return False
                
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"設定論文選取狀態發生錯誤 - paper_id: {paper_id}, 錯誤: {str(e)}, 類型: {type(e).__name__}, 處理時間: {processing_time:.3f}s", exc_info=True)
            
            # 嘗試回滾事務
            try:
                await db.rollback()
                logger.debug(f"錯誤後事務回滾成功 - paper_id: {paper_id}")
            except Exception as rollback_error:
                logger.error(f"錯誤後事務回滾失敗 - paper_id: {paper_id}, 回滾錯誤: {rollback_error}")
            
            return False
    
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

    async def get_sections_for_paper(self, db: AsyncSession, paper_id: str) -> List[PaperSection]:
        """獲取論文的所有章節"""
        query = (
            select(PaperSection)
            .where(PaperSection.paper_id == paper_id)
            .order_by(PaperSection.section_order)
        )
        result = await db.execute(query)
        return result.scalars().all()
    
    async def update_section_page_number(self, db: AsyncSession, section_id: str, page_num: int) -> bool:
        """更新章節的頁碼"""
        query = (
            update(PaperSection)
            .where(PaperSection.id == section_id)
            .values(page_num=page_num)
        )
        result = await db.execute(query)
        return result.rowcount > 0

# 建立服務實例
db_service = DatabaseService() 