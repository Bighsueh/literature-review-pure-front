from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..core.database import get_db
from ..services.db_service import db_service
from ..core.logging import get_logger
from ..models.paper import (
    PaperResponse, PaperSelectionUpdate, QueryRequest, QueryResult,
    PaperSectionSummary, ProcessingQueueResponse, UnifiedQueryRequest
)
from ..core.exceptions import (
    ValidationException, handle_validation_error,
    handle_not_found_error, handle_internal_error
)

logger = get_logger(__name__)

router = APIRouter(prefix="/papers", tags=["papers"])

# ===== 論文基本管理 =====

@router.get("/", response_model=List[Dict[str, Any]])
async def get_papers(db: AsyncSession = Depends(get_db)):
    """取得所有論文清單"""
    try:
        papers = await db_service.get_all_papers(db)
        return papers
    except Exception as e:
        raise handle_internal_error(f"取得論文清單失敗: {str(e)}")

@router.get("/selected", response_model=List[Dict[str, Any]])
async def get_selected_papers(db: AsyncSession = Depends(get_db)):
    """取得已選取的論文清單"""
    try:
        papers = await db_service.get_selected_papers(db)
        return papers
    except Exception as e:
        raise handle_internal_error(f"取得選取論文失敗: {str(e)}")

@router.get("/sections_summary", response_model=Dict[str, List[PaperSectionSummary]])
async def get_papers_sections_summary(db: AsyncSession = Depends(get_db)):
    """取得所有選中論文的section摘要資訊"""
    try:
        selected_papers = await db_service.get_selected_papers(db)
        
        if not selected_papers:
            return {"papers": []}
        
        paper_ids = [paper.id for paper in selected_papers]
        papers_with_sections = await db_service.get_papers_with_sections_summary(
            db, paper_ids
        )
        
        return {"papers": papers_with_sections}
    except Exception as e:
        raise handle_internal_error(f"取得section摘要失敗: {str(e)}")

# ===== 論文選取管理 =====

@router.post("/{paper_id}/select")
async def toggle_paper_selection(
    paper_id: str,
    selection_data: PaperSelectionUpdate,
    db: AsyncSession = Depends(get_db)
):
    """切換論文選取狀態"""
    try:
        # 檢查論文是否存在
        paper = await db_service.get_paper_by_id(db, paper_id)
        if not paper:
            raise handle_not_found_error("論文不存在")
        
        success = await db_service.set_paper_selection(
            db, paper_id, selection_data.is_selected
        )
        
        if success:
            return {
                "success": True,
                "message": f"論文選取狀態已更新為: {'已選取' if selection_data.is_selected else '未選取'}"
            }
        else:
            raise handle_internal_error("更新選取狀態失敗")
    except HTTPException:
        raise
    except Exception as e:
        raise handle_internal_error(f"切換選取狀態失敗: {str(e)}")

@router.post("/select_all")
async def select_all_papers(db: AsyncSession = Depends(get_db)):
    """全選所有論文"""
    try:
        success = await db_service.select_all_papers(db)
        if success:
            return {"success": True, "message": "已全選所有論文"}
        else:
            raise handle_internal_error("全選失敗")
    except HTTPException:
        raise
    except Exception as e:
        raise handle_internal_error(f"全選論文失敗: {str(e)}")

@router.post("/deselect_all")
async def deselect_all_papers(db: AsyncSession = Depends(get_db)):
    """取消全選"""
    try:
        success = await db_service.deselect_all_papers(db)
        if success:
            return {"success": True, "message": "已取消全選"}
        else:
            raise handle_internal_error("取消全選失敗")
    except HTTPException:
        raise
    except Exception as e:
        raise handle_internal_error(f"取消全選失敗: {str(e)}")

@router.post("/batch-select")
async def batch_select_papers(
    request_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """批次選取論文"""
    try:
        # 驗證請求資料
        if "paper_ids" not in request_data:
            raise ValidationException("缺少必要欄位: paper_ids")
        
        if "selected" not in request_data:
            raise ValidationException("缺少必要欄位: selected")
        
        paper_ids = request_data["paper_ids"]
        selected = request_data["selected"]
        
        if not isinstance(paper_ids, list):
            raise ValidationException("paper_ids 必須是陣列")
        
        if not isinstance(selected, bool):
            raise ValidationException("selected 必須是布林值")
        
        # 執行批次選取
        success_count = 0
        for paper_id in paper_ids:
            try:
                success = await db_service.set_paper_selection(db, paper_id, selected)
                if success:
                    success_count += 1
            except Exception as e:
                logger.warning(f"設置論文 {paper_id} 選取狀態失敗: {e}")
        
        return {
            "success": True,
            "message": f"成功更新 {success_count}/{len(paper_ids)} 篇論文的選取狀態",
            "updated_count": success_count,
            "total_count": len(paper_ids)
        }
        
    except ValidationException as e:
        raise handle_validation_error(e)
    except Exception as e:
        raise handle_internal_error(f"批次選取失敗: {str(e)}")

# ===== 處理狀態管理 =====

@router.get(
    "/{paper_id}/status",
    summary="獲取論文處理狀態",
    description="根據論文ID獲取其最新的處理狀態，取代舊的 task-based API"
)
async def get_paper_status(paper_id: str, db: AsyncSession = Depends(get_db)):
    """
    獲取論文處理的詳細狀態。
    這是新的、可靠的狀態查詢端點。
    """
    # 1. 直接從資料庫這個"單一事實來源"查詢
    paper = await db_service.get_paper_by_id(db, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="論文不存在")

    # 2. 如果仍在處理中，嘗試從 queue_service 獲取更詳細的即時進度
    if paper.processing_status == "processing":
        active_task = await queue_service.find_task_by_file_id(paper_id)
        if active_task:
            return {
                "status": "processing",
                "paper_id": str(paper.id),
                "progress": active_task.progress.to_dict() if active_task.progress else None,
                "task_id": active_task.task_id
            }

    # 3. 對於所有最終狀態（完成、錯誤）或其他狀態，直接返回資料庫中的權威狀態
    return {
        "status": paper.processing_status,
        "paper_id": str(paper.id),
        "progress": {
            "percentage": 100.0,
            "step_name": "完成" if paper.processing_status == "completed" else "失敗"
        },
        "error_message": paper.error_message
    }

@router.post("/{paper_id}/retry")
async def retry_processing(
    paper_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """重試論文處理"""
    try:
        paper = await db_service.get_paper_by_id(db, paper_id)
        if not paper:
            raise handle_not_found_error("論文不存在")
        
        # 更新處理狀態
        await db_service.update_paper_status(
            db,
            paper_id,
            "PENDING",
            "準備重新處理..."
        )
        
        # 加入背景任務
        from .upload import process_paper_pipeline
        background_tasks.add_task(
            process_paper_pipeline,
            paper_id
        )
        
        return {
            "success": True,
            "message": "已加入重試佇列"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise handle_internal_error(f"重試處理失敗: {str(e)}")

@router.post("/query/process", response_model=QueryResult)
async def process_query(
    query_data: QueryRequest,
    db: AsyncSession = Depends(get_db)
):
    """處理查詢請求"""
    try:
        result = await db_service.process_query(db, query_data)
        return result
    except Exception as e:
        raise handle_internal_error(f"查詢處理失敗: {str(e)}")

@router.get("/sections-summary")
async def get_papers_sections_summary_new(
    paper_ids: Optional[str] = Query(None, description="逗號分隔的論文ID列表，留空表示所有選中的論文"),
    db: AsyncSession = Depends(get_db)
):
    """取得論文段落摘要（新版）"""
    try:
        if paper_ids:
            paper_id_list = paper_ids.split(",")
        else:
            selected_papers = await db_service.get_selected_papers(db)
            paper_id_list = [paper.id for paper in selected_papers]
        
        if not paper_id_list:
            return {"papers": []}
        
        papers_with_sections = await db_service.get_papers_with_sections_summary(
            db, paper_id_list
        )
        
        return {"papers": papers_with_sections}
    except Exception as e:
        raise handle_internal_error(f"取得section摘要失敗: {str(e)}")

@router.post("/unified-query")
async def process_unified_query(
    request: UnifiedQueryRequest,
    db: AsyncSession = Depends(get_db)
):
    """處理統一查詢請求"""
    try:
        # 驗證請求參數
        if not request.query or not request.query.strip():
            raise ValidationException("查詢內容不能為空")
        
        # 檢查是否有選取的論文
        selected_papers = await db_service.get_selected_papers(db)
        if not selected_papers:
            raise ValidationException("請先選取要查詢的論文")
        
        # 導入統一查詢處理器
        from ..services.unified_query_service import unified_query_processor
        
        # 獲取論文資料
        papers_data = []
        for paper in selected_papers:
            papers_data.append({
                'id': str(paper.id),
                'filename': paper.original_filename or paper.file_name,
                'title': paper.original_filename or paper.file_name
            })
        
        # 生成論文摘要
        papers_summary = await unified_query_processor._generate_papers_summary(papers_data)
        
        # 處理查詢
        result = await unified_query_processor.process_query(
            query=request.query,
            papers_summary=papers_summary
        )
        
        return {
            "success": True,
            "query": request.query,
            "response": result.get('response', ''),
            "references": result.get('references', []),
            "source_summary": result.get('source_summary', {}),
            "processing_time": result.get('processing_time', 0),
            "papers_analyzed": result.get('papers_analyzed', 0),
            "timestamp": result.get('timestamp', '')
        }
    except ValidationException as e:
        raise handle_validation_error(e)
    except Exception as e:
        logger.error(f"統一查詢處理錯誤: {str(e)}", exc_info=True)
        raise handle_internal_error(f"統一查詢失敗: {str(e)}")

@router.get("/processing-stats")
async def get_processing_stats():
    """取得處理統計資訊"""
    try:
        stats = await db_service.get_processing_stats()
        return stats
    except Exception as e:
        raise handle_internal_error(f"取得統計資訊失敗: {str(e)}")

@router.get("/{paper_id}", response_model=PaperResponse)
async def get_paper_by_id(
    paper_id: str,
    db: AsyncSession = Depends(get_db)
):
    """根據ID取得論文"""
    try:
        paper = await db_service.get_paper_by_id(db, paper_id)
        if not paper:
            raise handle_not_found_error("論文不存在")
        return paper
    except HTTPException:
        raise
    except Exception as e:
        raise handle_internal_error(f"取得論文失敗: {str(e)}")

@router.get("/{paper_id}/sentences")
async def get_paper_sentences(
    paper_id: str,
    db: AsyncSession = Depends(get_db)
):
    """獲取論文的所有已處理句子"""
    try:
        # 驗證論文是否存在
        paper = await db_service.get_paper_by_id(db, paper_id)
        if not paper:
            raise handle_not_found_error("論文不存在")
        
        # 直接從資料庫獲取句子資料，不使用 Pydantic 模型
        from sqlalchemy import select
        from ..models.paper import Sentence
        
        query = (
            select(Sentence)
            .where(Sentence.paper_id == paper_id)
            .order_by(Sentence.section_id, Sentence.sentence_order)
        )
        result = await db.execute(query)
        sentences = result.scalars().all()
        
        return {
            "paper_id": paper_id,
            "sentences": [
                {
                    "id": str(sentence.id),
                    "content": sentence.sentence_text,
                    "type": "UNKNOWN" if sentence.defining_type in [None, "", "NONE"] else sentence.defining_type,
                    "reason": sentence.analysis_reason or sentence.explanation or "",
                    "pageNumber": sentence.page_num,
                    "fileName": paper.original_filename or paper.file_name,
                    "fileId": paper_id,
                    "sentenceOrder": sentence.sentence_order,
                    "sectionId": str(sentence.section_id) if sentence.section_id else None,
                    "confidence": float(sentence.confidence_score) if sentence.confidence_score else None,
                    "wordCount": sentence.word_count
                }
                for sentence in sentences
            ],
            "total_count": len(sentences),
            "processing_status": paper.processing_status
        }
    except HTTPException:
        raise
    except Exception as e:
        raise handle_internal_error(f"獲取論文句子失敗: {str(e)}")

@router.get("/sentences/all")
async def get_all_selected_papers_sentences(db: AsyncSession = Depends(get_db)):
    """獲取所有已選取論文的句子資料"""
    try:
        # 直接從資料庫獲取所有已選取的論文，避免 Pydantic 模型問題
        from sqlalchemy import select
        from ..models.paper import Paper, PaperSelection
        
        query = (
            select(Paper)
            .join(PaperSelection, Paper.id == PaperSelection.paper_id)
            .where(PaperSelection.is_selected == True)
            .order_by(Paper.created_at.desc())
        )
        result = await db.execute(query)
        selected_papers = result.scalars().all()
        
        if not selected_papers:
            return {
                "papers": [],
                "total_sentences": 0,
                "total_papers": 0
            }
        
        all_sentences = []
        
        # 直接從資料庫獲取所有選取論文的句子
        from ..models.paper import Sentence
        
        for paper in selected_papers:
            query = (
                select(Sentence)
                .where(Sentence.paper_id == str(paper.id))
                .order_by(Sentence.section_id, Sentence.sentence_order)
            )
            result = await db.execute(query)
            sentences = result.scalars().all()
            
            for sentence in sentences:
                all_sentences.append({
                    "id": str(sentence.id),
                    "content": sentence.sentence_text,
                    "type": "UNKNOWN" if sentence.defining_type in [None, "", "NONE"] else sentence.defining_type,
                    "reason": sentence.analysis_reason or sentence.explanation or "",
                    "pageNumber": sentence.page_num,
                    "fileName": paper.original_filename or paper.file_name,
                    "fileId": str(paper.id),
                    "sentenceOrder": sentence.sentence_order,
                    "sectionId": str(sentence.section_id) if sentence.section_id else None,
                    "confidence": float(sentence.confidence_score) if sentence.confidence_score else None,
                    "wordCount": sentence.word_count
                })
        
        return {
            "sentences": all_sentences,
            "total_sentences": len(all_sentences),
            "total_papers": len(selected_papers),
            "papers": [
                {
                    "id": str(paper.id),
                    "fileName": paper.original_filename or paper.file_name,
                    "processing_status": paper.processing_status
                }
                for paper in selected_papers
            ]
        }
    except Exception as e:
        raise handle_internal_error(f"獲取所有句子失敗: {str(e)}")

@router.delete("/{paper_id}")
async def delete_paper(
    paper_id: str,
    db: AsyncSession = Depends(get_db)
):
    """刪除論文"""
    try:
        # 檢查論文是否存在
        paper = await db_service.get_paper_by_id(db, paper_id)
        if not paper:
            raise handle_not_found_error("論文不存在")
        
        # 執行刪除
        success = await db_service.delete_paper(db, paper_id)
        
        if success:
            return {
                "success": True,
                "message": "論文已刪除"
            }
        else:
            raise handle_internal_error("刪除失敗")
    except HTTPException:
        raise
    except Exception as e:
        raise handle_internal_error(f"刪除論文失敗: {str(e)}") 