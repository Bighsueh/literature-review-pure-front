import asyncio
import time
from uuid import UUID
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, desc, and_, or_, func, text
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
from ..core.pagination import paginate_query, PaginatedResponse
from ..models.user import User
from ..models.user import Workspace

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
    
    async def create_paper(self, db: AsyncSession, paper_data: PaperCreate, workspace_id: Optional[UUID] = None) -> str:
        """建立新論文記錄"""
        paper_dict = paper_data.dict()
        if workspace_id:
            paper_dict['workspace_id'] = workspace_id
        
        paper = Paper(**paper_dict)
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
        
        for row in result:
            # 正確解包查詢結果
            paper = row[0]
            is_selected = row[1] if len(row) > 1 else None
            section_count = row[2] if len(row) > 2 else 0
            sentence_count = row[3] if len(row) > 3 else 0
            
            paper_dict = {
                "id": str(paper.id),
                "title": paper.original_filename or paper.file_name,
                "file_path": paper.file_name,
                "file_hash": paper.file_hash,
                "upload_time": paper.upload_timestamp.isoformat() if paper.upload_timestamp else datetime.now().isoformat(),
                "upload_timestamp": paper.upload_timestamp,
                "processing_status": paper.processing_status,
                "grobid_processed": paper.grobid_processed,
                "sentences_processed": paper.sentences_processed,
                "od_cd_processed": paper.od_cd_processed,
                "pdf_deleted": paper.pdf_deleted,
                "error_message": paper.error_message,
                "processing_completed_at": paper.processing_completed_at,
                "selected": is_selected if is_selected is not None else False,
                "authors": [],  # Placeholder, to be implemented
                "section_count": section_count or 0,  # 修復：使用真實計數
                "sentence_count": sentence_count or 0,  # 修復：使用真實計數
                
                # Keep original fields for compatibility if needed elsewhere
                "original_filename": paper.original_filename,
                "file_name": paper.file_name,
                "created_at": paper.created_at,
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
            update_result = await db.execute(
                update(Paper).where(Paper.id == paper_id).values(
                    sentences_processed=True, processing_status=status
                )
            )
            logger.info(f"更新論文狀態 - paper_id: {paper_id}, affected_rows: {update_result.rowcount}, sentences_processed: True, status: {status}")
            
            # 4. 關鍵修復：確保提交事務
            await db.commit()
            logger.info(f"章節和句子資料已成功提交到資料庫 - paper_id: {paper_id}")
            
            # 4.5 驗證狀態更新是否成功
            check_result = await db.execute(
                select(Paper.sentences_processed, Paper.processing_status).where(Paper.id == paper_id)
            )
            check_data = check_result.first()
            if check_data:
                logger.info(f"狀態驗證 - paper_id: {paper_id}, sentences_processed: {check_data[0]}, processing_status: {check_data[1]}")
                if not check_data[0]:
                    logger.error(f"Critical Error: sentences_processed 狀態設置失敗！重新嘗試設置...")
                    await db.execute(
                        update(Paper).where(Paper.id == paper_id).values(sentences_processed=True)
                    )
                    await db.commit()
            
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
    
    async def set_paper_selection(self, db: AsyncSession, paper_id: str, is_selected: bool, workspace_id: Optional[UUID] = None) -> bool:
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

            # 如果沒有提供 workspace_id，從論文中獲取
            if workspace_id is None:
                paper_query = select(Paper.workspace_id).where(Paper.id == paper_id)
                result = await db.execute(paper_query)
                paper_workspace = result.scalar_one_or_none()
                if not paper_workspace:
                    logger.error(f"找不到論文或無法獲取工作區ID: {paper_id}")
                    return False
                workspace_id = paper_workspace

            # 使用超時保護包裝資料庫操作
            async def _perform_database_operation():
                # 先嘗試更新現有記錄
                logger.debug(f"嘗試更新現有選取記錄 - paper_id: {paper_id}")
                update_query = (
                    update(PaperSelection)
                    .where(and_(
                        PaperSelection.paper_id == paper_id,
                        PaperSelection.workspace_id == workspace_id
                    ))
                    .values(is_selected=is_selected, selected_timestamp=func.current_timestamp())
                )
                result = await db.execute(update_query)
                
                # 如果沒有更新到任何記錄，表示不存在，需要建立新記錄
                if result.rowcount == 0:
                    logger.debug(f"創建新的選取記錄 - paper_id: {paper_id}, workspace_id: {workspace_id}")
                    selection = PaperSelection(
                        paper_id=paper_id, 
                        workspace_id=workspace_id,
                        is_selected=is_selected
                    )
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
                    logger.info(f"創建新選取記錄成功 - paper_id: {paper_id}, workspace_id: {workspace_id}, is_selected: {is_selected}, 處理時間: {processing_time:.3f}s")
                else:
                    logger.info(f"更新現有選取記錄成功 - paper_id: {paper_id}, workspace_id: {workspace_id}, is_selected: {is_selected}, 處理時間: {processing_time:.3f}s")
                
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
    
    async def mark_paper_selected(self, db: AsyncSession, paper_id: str, workspace_id: Optional[UUID] = None) -> bool:
        """標記論文為已選取"""
        return await self.set_paper_selection(db, paper_id, True, workspace_id)
    
    async def select_all_papers(self, db: AsyncSession) -> bool:
        """全選所有論文"""
        # 取得所有論文ID
        papers_query = select(Paper.id, Paper.workspace_id)
        result = await db.execute(papers_query)
        papers = result.all()
        
        # 為每個論文設定選取狀態
        for paper_id, workspace_id in papers:
            await self.set_paper_selection(db, str(paper_id), True, workspace_id)
        
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

    # ===== 工作區化方法 =====
    
    async def get_paper_by_hash_and_workspace(self, db: AsyncSession, file_hash: str, workspace_id: UUID) -> Optional[Paper]:
        """根據檔案雜湊值和工作區取得論文"""
        query = select(Paper).where(
            and_(Paper.file_hash == file_hash, Paper.workspace_id == workspace_id)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_paper_by_id_and_workspace(self, db: AsyncSession, paper_id: str, workspace_id: UUID) -> Optional[Paper]:
        """根據ID和工作區取得論文"""
        query = select(Paper).where(
            and_(Paper.id == paper_id, Paper.workspace_id == workspace_id)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_papers_by_workspace(
        self, 
        db: AsyncSession, 
        workspace_id: UUID,
        pagination: Optional[Any] = None,  # PaginationParams
        selected_only: bool = False
    ) -> Any:  # PaginatedResponse[PaperResponse]
        """取得工作區內的論文列表，支援分頁"""
        try:
            # 簡化的查詢 - 先只取論文資料
            papers_query = select(Paper).where(Paper.workspace_id == workspace_id).order_by(desc(Paper.created_at))
            
            if pagination:
                # 使用分頁
                items, meta = await paginate_query(db, papers_query, pagination)
                formatted_items = []
                
                for paper in items:
                    # 單獨查詢選取狀態
                    selection_query = select(PaperSelection.is_selected).where(
                        and_(
                            PaperSelection.paper_id == paper.id,
                            PaperSelection.workspace_id == workspace_id
                        )
                    )
                    selection_result = await db.execute(selection_query)
                    is_selected = selection_result.scalar_one_or_none()
                    
                    # 如果只要已選取的檔案且此檔案未選取，跳過
                    if selected_only and not is_selected:
                        continue
                    
                    paper_dict = {
                        "id": str(paper.id),
                        "title": paper.original_filename or paper.file_name,
                        "file_path": paper.file_name,
                        "file_hash": paper.file_hash,
                        "upload_time": paper.upload_timestamp.isoformat() if paper.upload_timestamp else datetime.now().isoformat(),
                        "upload_timestamp": paper.upload_timestamp,
                        "processing_status": paper.processing_status,
                        "grobid_processed": paper.grobid_processed,
                        "sentences_processed": paper.sentences_processed,
                        "od_cd_processed": paper.od_cd_processed,
                        "pdf_deleted": paper.pdf_deleted,
                        "error_message": paper.error_message,
                        "processing_completed_at": paper.processing_completed_at,
                        "selected": is_selected if is_selected is not None else False,
                        "authors": [],
                        "section_count": 0,  # 暫時設為 0
                        "sentence_count": 0,  # 暫時設為 0
                        "original_filename": paper.original_filename,
                        "file_name": paper.file_name,
                        "workspace_id": str(paper.workspace_id) if paper.workspace_id else None,
                        "created_at": paper.created_at,
                    }
                    formatted_items.append(paper_dict)
                
                return PaginatedResponse(
                    items=formatted_items,
                    meta=meta
                )
            else:
                # 不使用分頁
                result = await db.execute(papers_query)
                papers = result.scalars().all()
                formatted_papers = []
                
                for paper in papers:
                    # 單獨查詢選取狀態
                    selection_query = select(PaperSelection.is_selected).where(
                        and_(
                            PaperSelection.paper_id == paper.id,
                            PaperSelection.workspace_id == workspace_id
                        )
                    )
                    selection_result = await db.execute(selection_query)
                    is_selected = selection_result.scalar_one_or_none()
                    
                    # 如果只要已選取的檔案且此檔案未選取，跳過
                    if selected_only and not is_selected:
                        continue
                    
                    paper_dict = {
                        "id": str(paper.id),
                        "title": paper.original_filename or paper.file_name,
                        "file_path": paper.file_name,
                        "file_hash": paper.file_hash,
                        "upload_time": paper.upload_timestamp.isoformat() if paper.upload_timestamp else datetime.now().isoformat(),
                        "upload_timestamp": paper.upload_timestamp,
                        "processing_status": paper.processing_status,
                        "grobid_processed": paper.grobid_processed,
                        "sentences_processed": paper.sentences_processed,
                        "od_cd_processed": paper.od_cd_processed,
                        "pdf_deleted": paper.pdf_deleted,
                        "error_message": paper.error_message,
                        "processing_completed_at": paper.processing_completed_at,
                        "selected": is_selected if is_selected is not None else False,
                        "authors": [],
                        "section_count": 0,  # 暫時設為 0
                        "sentence_count": 0,  # 暫時設為 0
                        "original_filename": paper.original_filename,
                        "file_name": paper.file_name,
                        "workspace_id": str(paper.workspace_id) if paper.workspace_id else None,
                        "created_at": paper.created_at,
                    }
                    formatted_papers.append(paper_dict)
                
                return formatted_papers
                
        except Exception as e:
            logger.error(f"取得工作區論文列表失敗: {str(e)}")
            raise
    
    async def get_selected_papers_by_workspace(self, db: AsyncSession, workspace_id: UUID) -> List[Paper]:
        """取得工作區內已選取的論文"""
        query = (
            select(Paper)
            .join(PaperSelection, Paper.id == PaperSelection.paper_id)
            .where(
                and_(
                    Paper.workspace_id == workspace_id,
                    PaperSelection.is_selected == True
                )
            )
            .order_by(desc(Paper.created_at))
        )
        result = await db.execute(query)
        return result.scalars().all()
    
    async def select_all_papers_in_workspace(self, db: AsyncSession, workspace_id: UUID) -> int:
        """選取工作區內所有論文"""
        # 取得工作區內所有論文的ID
        paper_query = select(Paper.id).where(Paper.workspace_id == workspace_id)
        result = await db.execute(paper_query)
        paper_ids = [str(row[0]) for row in result]
        
        if not paper_ids:
            return 0
        
        # 批次設定選取狀態
        for paper_id in paper_ids:
            await self.set_paper_selection(db, paper_id, True, workspace_id)
        
        return len(paper_ids)
    
    async def deselect_all_papers_in_workspace(self, db: AsyncSession, workspace_id: UUID) -> int:
        """取消選取工作區內所有論文"""
        # 取得工作區內所有論文的ID
        paper_query = select(Paper.id).where(Paper.workspace_id == workspace_id)
        result = await db.execute(paper_query)
        paper_ids = [str(row[0]) for row in result]
        
        if not paper_ids:
            return 0
        
        # 批次設定選取狀態
        for paper_id in paper_ids:
            await self.set_paper_selection(db, paper_id, False, workspace_id)
        
        return len(paper_ids)
    
    async def batch_select_papers_in_workspace(self, db: AsyncSession, file_ids: List[str], workspace_id: UUID) -> int:
        """批次選取工作區內指定論文"""
        # 驗證所有檔案都屬於指定工作區
        query = select(Paper.id).where(
            and_(
                Paper.id.in_(file_ids),
                Paper.workspace_id == workspace_id
            )
        )
        result = await db.execute(query)
        valid_paper_ids = [str(row[0]) for row in result]
        
        # 批次設定選取狀態
        for paper_id in valid_paper_ids:
            await self.set_paper_selection(db, paper_id, True, workspace_id)
        
        return len(valid_paper_ids)
    
    async def get_papers_sections_summary_by_workspace(self, db: AsyncSession, workspace_id: UUID) -> Dict[str, Any]:
        """取得工作區內檔案的章節摘要"""
        query = (
            select(
                Paper.id,
                Paper.original_filename,
                func.count(func.distinct(PaperSection.id)).label('section_count'),
                func.count(func.distinct(Sentence.id)).label('sentence_count')
            )
            .outerjoin(PaperSection, Paper.id == PaperSection.paper_id)
            .outerjoin(Sentence, Paper.id == Sentence.paper_id)
            .where(Paper.workspace_id == workspace_id)
            .group_by(Paper.id, Paper.original_filename)
        )
        
        result = await db.execute(query)
        summaries = []
        
        total_sections = 0
        total_sentences = 0
        
        for paper_id, filename, section_count, sentence_count in result:
            section_count = section_count or 0
            sentence_count = sentence_count or 0
            
            summaries.append({
                "paper_id": str(paper_id),
                "filename": filename,
                "section_count": section_count,
                "sentence_count": sentence_count
            })
            
            total_sections += section_count
            total_sentences += sentence_count
        
        return {
            "workspace_id": str(workspace_id),
            "total_papers": len(summaries),
            "total_sections": total_sections,
            "total_sentences": total_sentences,
            "papers": summaries
        }
    
    async def search_sentences_in_workspace(
        self, 
        db: AsyncSession, 
        workspace_id: UUID,
        defining_types: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """在工作區範圍內搜尋句子"""
        # 首先取得工作區內的所有論文ID
        paper_query = select(Paper.id).where(Paper.workspace_id == workspace_id)
        result = await db.execute(paper_query)
        paper_ids = [str(row[0]) for row in result]
        
        if not paper_ids:
            return []
        
        # 呼叫原有的搜尋方法，但限制在工作區內的論文
        return await self.search_sentences(db, paper_ids, defining_types, keywords)

    async def get_selected_papers_by_workspace(
        self, 
        db: AsyncSession, 
        workspace_id: UUID
    ) -> List[Paper]:
        """
        獲取工作區範圍內的已選取論文 - 嚴格工作區隔離
        """
        try:
            stmt = select(Paper).where(
                and_(
                    Paper.workspace_id == workspace_id,
                    Paper.is_selected == True
                )
            )
            result = await db.execute(stmt)
            papers = result.scalars().all()
            
            logger.info(f"工作區 {workspace_id} 中找到 {len(papers)} 篇已選取論文")
            return papers
            
        except Exception as e:
            logger.error(f"獲取工作區論文失敗: workspace={workspace_id}, error={str(e)}")
            return []

    async def get_papers_with_sections_summary(
        self, 
        db: AsyncSession, 
        paper_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        獲取論文及其章節摘要資訊
        """
        if not paper_ids:
            return []
            
        try:
            papers_summary = []
            
            for paper_id in paper_ids:
                # 獲取論文基本資訊
                stmt = select(Paper).where(Paper.id == paper_id)
                result = await db.execute(stmt)
                paper = result.scalar_one_or_none()
                
                if not paper:
                    continue
                
                # 獲取章節資訊
                sections_stmt = select(PaperSection).where(PaperSection.paper_id == paper_id)
                sections_result = await db.execute(sections_stmt)
                sections = sections_result.scalars().all()
                
                # 構建論文摘要
                paper_summary = {
                    'file_name': paper.file_name,
                    'paper_id': str(paper.id),
                    'title': paper.title or '',
                    'workspace_id': str(paper.workspace_id),
                    'sections': []
                }
                
                for section in sections:
                    # 獲取章節統計資訊
                    sentence_stats = await self._get_section_sentence_stats(db, section.id)
                    
                    section_summary = {
                        'section_type': section.section_type,
                        'page_num': section.page_num or 0,
                        'word_count': len(section.content.split()) if section.content else 0,
                        'brief_content': (section.content or '')[:200] + "...",
                        'od_count': sentence_stats.get('od_count', 0),
                        'cd_count': sentence_stats.get('cd_count', 0),
                        'total_sentences': sentence_stats.get('total_sentences', 0)
                    }
                    paper_summary['sections'].append(section_summary)
                
                papers_summary.append(paper_summary)
            
            logger.info(f"生成了 {len(papers_summary)} 篇論文的摘要")
            return papers_summary
            
        except Exception as e:
            logger.error(f"獲取論文摘要失敗: error={str(e)}")
            return []

    async def search_sentences_in_workspace(
        self,
        db: AsyncSession,
        workspace_id: UUID,
        defining_types: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None,
        section_type: Optional[str] = None,
        paper_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        在工作區範圍內搜尋句子 - 嚴格工作區隔離
        """
        try:
            # 基本查詢：僅限於指定工作區的論文
            query = text("""
                SELECT 
                    s.id as sentence_id,
                    s.content,
                    s.defining_type,
                    s.page_num,
                    s.sentence_order,
                    p.file_name,
                    ps.section_type,
                    p.workspace_id
                FROM sentences s
                JOIN paper_sections ps ON s.section_id = ps.id
                JOIN papers p ON ps.paper_id = p.id
                WHERE p.workspace_id = :workspace_id
            """)
            
            params = {'workspace_id': str(workspace_id)}
            
            # 添加定義類型過濾
            if defining_types:
                type_conditions = " OR ".join([f"s.defining_type = :type_{i}" for i in range(len(defining_types))])
                query = text(str(query) + f" AND ({type_conditions})")
                for i, dtype in enumerate(defining_types):
                    params[f'type_{i}'] = dtype
            
            # 添加論文名稱過濾
            if paper_name:
                query = text(str(query) + " AND p.file_name = :paper_name")
                params['paper_name'] = paper_name
            
            # 添加章節類型過濾
            if section_type:
                query = text(str(query) + " AND ps.section_type = :section_type")
                params['section_type'] = section_type
            
            # 添加關鍵詞過濾
            if keywords:
                keyword_conditions = " OR ".join([f"LOWER(s.content) LIKE :keyword_{i}" for i in range(len(keywords))])
                query = text(str(query) + f" AND ({keyword_conditions})")
                for i, keyword in enumerate(keywords):
                    params[f'keyword_{i}'] = f'%{keyword.lower()}%'
            
            query = text(str(query) + " ORDER BY p.file_name, ps.section_type, s.sentence_order")
            
            result = await db.execute(query, params)
            rows = result.fetchall()
            
            sentences = []
            for row in rows:
                sentences.append({
                    'sentence_id': row.sentence_id,
                    'content': row.content,
                    'defining_type': row.defining_type,
                    'page_num': row.page_num,
                    'sentence_order': row.sentence_order,
                    'file_name': row.file_name,
                    'section_type': row.section_type,
                    'workspace_id': row.workspace_id
                })
            
            logger.info(f"工作區 {workspace_id} 中搜尋到 {len(sentences)} 個句子")
            return sentences
            
        except Exception as e:
            logger.error(f"工作區句子搜尋失敗: workspace={workspace_id}, error={str(e)}")
            return []

    async def get_section_content_by_workspace(
        self,
        db: AsyncSession,
        workspace_id: UUID,
        paper_name: str,
        section_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        獲取工作區範圍內的章節完整內容
        """
        try:
            query = text("""
                SELECT 
                    ps.id as section_id,
                    ps.content,
                    ps.page_num,
                    p.file_name,
                    p.workspace_id
                FROM paper_sections ps
                JOIN papers p ON ps.paper_id = p.id
                WHERE p.workspace_id = :workspace_id 
                  AND p.file_name = :paper_name 
                  AND ps.section_type = :section_type
            """)
            
            result = await db.execute(query, {
                'workspace_id': str(workspace_id),
                'paper_name': paper_name,
                'section_type': section_type
            })
            
            row = result.fetchone()
            if not row:
                return None
            
            return {
                'section_id': row.section_id,
                'content': row.content,
                'page_num': row.page_num,
                'file_name': row.file_name,
                'section_type': section_type,
                'workspace_id': row.workspace_id
            }
            
        except Exception as e:
            logger.error(f"獲取工作區章節內容失敗: workspace={workspace_id}, paper={paper_name}, section={section_type}, error={str(e)}")
            return None

    async def _get_section_sentence_stats(
        self,
        db: AsyncSession,
        section_id: str
    ) -> Dict[str, int]:
        """
        獲取章節的句子統計資訊
        """
        try:
            query = text("""
                SELECT 
                    COUNT(*) as total_sentences,
                    SUM(CASE WHEN defining_type = 'OD' THEN 1 ELSE 0 END) as od_count,
                    SUM(CASE WHEN defining_type = 'CD' THEN 1 ELSE 0 END) as cd_count
                FROM sentences 
                WHERE section_id = :section_id
            """)
            
            result = await db.execute(query, {'section_id': section_id})
            row = result.fetchone()
            
            return {
                'total_sentences': row.total_sentences or 0,
                'od_count': row.od_count or 0,
                'cd_count': row.cd_count or 0
            }
            
        except Exception as e:
            logger.error(f"獲取章節統計失敗: section_id={section_id}, error={str(e)}")
            return {'total_sentences': 0, 'od_count': 0, 'cd_count': 0}

    async def verify_workspace_access(
        self,
        db: AsyncSession,
        user_id: UUID,
        workspace_id: UUID
    ) -> bool:
        """
        驗證用戶對工作區的存取權限
        """
        try:
            # 檢查工作區是否屬於用戶
            stmt = select(Workspace).where(
                and_(
                    Workspace.id == workspace_id,
                    Workspace.user_id == user_id
                )
            )
            result = await db.execute(stmt)
            workspace = result.scalar_one_or_none()
            
            return workspace is not None
            
        except Exception as e:
            logger.error(f"驗證工作區存取權限失敗: user={user_id}, workspace={workspace_id}, error={str(e)}")
            return False

    async def get_workspace_by_id(
        self,
        db: AsyncSession,
        workspace_id: UUID
    ) -> Optional[Workspace]:
        """
        根據ID獲取工作區資訊
        """
        try:
            stmt = select(Workspace).where(Workspace.id == workspace_id)
            result = await db.execute(stmt)
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"獲取工作區失敗: workspace_id={workspace_id}, error={str(e)}")
            return None

# 建立服務實例
db_service = DatabaseService() 