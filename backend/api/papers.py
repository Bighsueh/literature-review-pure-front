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

@router.get("/{paper_id}/status")
async def get_processing_status(
    paper_id: str,
    db: AsyncSession = Depends(get_db)
):
    """取得論文處理狀態"""
    try:
        paper = await db_service.get_paper_by_id(db, paper_id)
        if not paper:
            raise handle_not_found_error("論文不存在")
        
        return {
            "success": True,
            "status": paper.processing_status,
            "message": paper.error_message if paper.error_message else "處理中..."
        }
    except HTTPException:
        raise
    except Exception as e:
        raise handle_internal_error(f"取得處理狀態失敗: {str(e)}")

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