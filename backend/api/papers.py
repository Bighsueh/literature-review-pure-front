from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from datetime import datetime
import time
from dataclasses import asdict

from ..core.database import get_db
from ..services.db_service import db_service
from ..services.queue_service import queue_service
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

@router.get("/selected", response_model=List[PaperResponse])
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
    request: Request,
    selection_data: PaperSelectionUpdate,
    db: AsyncSession = Depends(get_db)
):
    """切換論文選取狀態"""
    start_time = time.time()
    
    # 記錄原始請求體
    try:
        body = await request.body()
        logger.info(f"原始請求體 - paper_id: {paper_id}, body: {body.decode('utf-8', errors='ignore')}")
        logger.info(f"請求標頭 - Content-Type: {request.headers.get('content-type')}, Content-Length: {request.headers.get('content-length')}")
    except Exception as body_error:
        logger.error(f"無法讀取請求體 - paper_id: {paper_id}, 錯誤: {body_error}")
    
    # 記錄請求開始
    logger.info(f"開始處理論文選取請求 - paper_id: {paper_id}, is_selected: {selection_data.is_selected}")
    
    try:
        # 驗證 paper_id 格式
        try:
            from uuid import UUID
            UUID(paper_id)
        except ValueError:
            logger.warning(f"無效的論文ID格式: {paper_id}")
            raise handle_validation_error(ValidationException("無效的論文ID格式"))
        
        # 驗證請求資料
        if selection_data.is_selected is None:
            logger.warning(f"缺少必要欄位 is_selected")
            raise handle_validation_error(ValidationException("缺少必要欄位: is_selected"))
        
        if not isinstance(selection_data.is_selected, bool):
            logger.warning(f"is_selected 必須是布林值，收到: {type(selection_data.is_selected)}")
            raise handle_validation_error(ValidationException("is_selected 必須是布林值"))
        
        # 檢查論文是否存在
        logger.debug(f"檢查論文是否存在: {paper_id}")
        paper = await db_service.get_paper_by_id(db, paper_id)
        if not paper:
            logger.warning(f"論文不存在: {paper_id}")
            raise handle_not_found_error("論文不存在")
        
        # 執行選取狀態更新
        logger.debug(f"更新論文選取狀態: {paper_id} -> {selection_data.is_selected}")
        success = await db_service.set_paper_selection(
            db, paper_id, selection_data.is_selected
        )
        
        # 記錄處理時間
        processing_time = time.time() - start_time
        
        if success:
            status_text = '已選取' if selection_data.is_selected else '未選取'
            logger.info(f"論文選取狀態更新成功 - paper_id: {paper_id}, 狀態: {status_text}, 處理時間: {processing_time:.3f}s")
            return {
                "success": True,
                "message": f"論文選取狀態已更新為: {status_text}",
                "paper_id": paper_id,
                "is_selected": selection_data.is_selected,
                "processing_time_ms": round(processing_time * 1000, 2)
            }
        else:
            logger.error(f"更新選取狀態失敗 - paper_id: {paper_id}, 處理時間: {processing_time:.3f}s")
            raise handle_internal_error("更新選取狀態失敗")
            
    except HTTPException:
        # HTTP異常直接重新拋出，但記錄處理時間
        processing_time = time.time() - start_time
        logger.warning(f"HTTP異常 - paper_id: {paper_id}, 處理時間: {processing_time:.3f}s")
        raise
    except Exception as e:
        # 其他異常的詳細記錄
        processing_time = time.time() - start_time
        logger.error(f"切換選取狀態發生未預期錯誤 - paper_id: {paper_id}, 錯誤: {str(e)}, 類型: {type(e).__name__}, 處理時間: {processing_time:.3f}s", exc_info=True)
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
    start_time = time.time()
    
    # 記錄請求開始
    logger.info(f"開始處理批次選取請求 - 資料: {request_data}")
    
    try:
        # 驗證請求資料
        if not isinstance(request_data, dict):
            logger.warning(f"請求資料格式無效，期望dict，收到: {type(request_data)}")
            raise ValidationException("請求資料必須是字典格式")
            
        if "paper_ids" not in request_data:
            logger.warning("缺少必要欄位: paper_ids")
            raise ValidationException("缺少必要欄位: paper_ids")
        
        if "selected" not in request_data:
            logger.warning("缺少必要欄位: selected")
            raise ValidationException("缺少必要欄位: selected")
        
        paper_ids = request_data["paper_ids"]
        selected = request_data["selected"]
        
        # 驗證資料類型
        if not isinstance(paper_ids, list):
            logger.warning(f"paper_ids 必須是陣列，收到: {type(paper_ids)}")
            raise ValidationException("paper_ids 必須是陣列")
        
        if not isinstance(selected, bool):
            logger.warning(f"selected 必須是布林值，收到: {type(selected)}")
            raise ValidationException("selected 必須是布林值")
        
        # 驗證 paper_ids 內容
        if len(paper_ids) == 0:
            logger.warning("paper_ids 陣列不能為空")
            raise ValidationException("paper_ids 陣列不能為空")
        
        # 驗證每個 paper_id 格式
        from uuid import UUID
        for paper_id in paper_ids:
            try:
                UUID(paper_id)
            except (ValueError, TypeError):
                logger.warning(f"無效的論文ID格式: {paper_id}")
                raise ValidationException(f"無效的論文ID格式: {paper_id}")
        
        logger.debug(f"批次更新 {len(paper_ids)} 篇論文選取狀態為: {selected}")
        
        # 執行批次選取
        success_count = 0
        failed_papers = []
        
        for paper_id in paper_ids:
            try:
                success = await db_service.set_paper_selection(db, paper_id, selected)
                if success:
                    success_count += 1
                else:
                    failed_papers.append(paper_id)
                    logger.warning(f"設置論文 {paper_id} 選取狀態失敗: 資料庫操作返回失敗")
            except Exception as e:
                failed_papers.append(paper_id)
                logger.warning(f"設置論文 {paper_id} 選取狀態失敗: {e}")
        
        # 記錄處理時間
        processing_time = time.time() - start_time
        status_text = '已選取' if selected else '未選取'
        
        logger.info(f"批次選取完成 - 成功: {success_count}/{len(paper_ids)}, 狀態: {status_text}, 處理時間: {processing_time:.3f}s")
        
        response = {
            "success": True,
            "message": f"成功更新 {success_count}/{len(paper_ids)} 篇論文的選取狀態為{status_text}",
            "updated_count": success_count,
            "total_count": len(paper_ids),
            "selected": selected,
            "processing_time_ms": round(processing_time * 1000, 2)
        }
        
        # 如果有失敗的論文，也在回應中包含
        if failed_papers:
            response["failed_papers"] = failed_papers
            response["warning"] = f"有 {len(failed_papers)} 篇論文更新失敗"
        
        return response
        
    except ValidationException as e:
        processing_time = time.time() - start_time
        logger.warning(f"批次選取驗證失敗 - 錯誤: {str(e)}, 處理時間: {processing_time:.3f}s")
        raise handle_validation_error(e)
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"批次選取發生未預期錯誤 - 錯誤: {str(e)}, 類型: {type(e).__name__}, 處理時間: {processing_time:.3f}s", exc_info=True)
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
                "progress": asdict(active_task.progress) if active_task.progress else None,
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
        papers_summary = await unified_query_processor._generate_papers_summary(papers_data, db)
        
        # 處理查詢 - 執行完整的 flowchart
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
                    "content": sentence.content,
                    "detection_status": sentence.detection_status,
                    "has_objective": sentence.has_objective,
                    "has_dataset": sentence.has_dataset,
                    "has_contribution": sentence.has_contribution,
                    "explanation": sentence.explanation or "",
                    "fileName": paper.original_filename or paper.file_name,
                    "fileId": paper_id,
                    "sentenceOrder": sentence.sentence_order,
                    "sectionId": str(sentence.section_id) if sentence.section_id else None,
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
                    "content": sentence.content,
                    "detection_status": sentence.detection_status,
                    "has_objective": sentence.has_objective,
                    "has_dataset": sentence.has_dataset,
                    "has_contribution": sentence.has_contribution,
                    "explanation": sentence.explanation or "",
                    "fileName": paper.original_filename or paper.file_name,
                    "fileId": str(paper.id),
                    "sentenceOrder": sentence.sentence_order,
                    "sectionId": str(sentence.section_id) if sentence.section_id else None,
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

@router.post("/test-unified-query")
async def test_unified_query(
    request: UnifiedQueryRequest,
    db: AsyncSession = Depends(get_db)
):
    """測試版本的 unified-query，用於驗證修復"""
    try:
        logger.info(f"測試統一查詢請求: {request.query}")
        
        # 1. 檢查是否有選取的論文
        selected_papers = await db_service.get_selected_papers(db)
        
        if not selected_papers:
            return {
                "success": True,
                "query": request.query,
                "response": "沒有可用的論文資料",
                "message": "診斷：沒有找到選取的論文",
                "debug_info": {
                    "selected_papers_count": 0,
                    "papers_summary_generated": False
                }
            }
        
        logger.info(f"找到 {len(selected_papers)} 篇選取的論文")
        
        # 2. 生成論文資料
        papers_data = []
        for paper in selected_papers:
            papers_data.append({
                'id': str(paper.id),
                'filename': paper.original_filename or paper.file_name,
                'title': paper.original_filename or paper.file_name
            })
        
        # 3. 生成論文摘要 (簡化版本)
        from ..services.unified_query_service import unified_query_processor
        papers_summary = await unified_query_processor._generate_papers_summary(papers_data, db)
        
        return {
            "success": True,
            "query": request.query,
            "response": f"成功處理！找到 {len(selected_papers)} 篇論文，生成了 {len(papers_summary)} 篇論文摘要",
            "message": "修復成功：論文摘要生成正常",
            "debug_info": {
                "selected_papers_count": len(selected_papers),
                "papers_summary_generated": True,
                "papers_summary_count": len(papers_summary),
                "papers_details": [
                    {
                        "file_name": paper.get('file_name', ''),
                        "sections_count": len(paper.get('sections', []))
                    }
                    for paper in papers_summary
                ]
            }
        }
        
    except Exception as e:
        logger.error(f"測試統一查詢處理錯誤: {str(e)}", exc_info=True)
        return {
            "success": False,
            "query": request.query,
            "response": f"測試失敗: {str(e)}",
            "message": "仍有問題需要修復",
            "debug_info": {
                "error": str(e),
                "error_type": type(e).__name__
            }
        } 