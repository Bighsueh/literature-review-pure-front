from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
from uuid import UUID
from pydantic import BaseModel

from ..core.database import get_db
from ..api.dependencies import get_workspace_for_user, get_current_user
from ..models.user import User, Workspace
from ..services.db_service import db_service
from ..services.unified_query_service import unified_query_processor
from ..core.logging import get_logger
from ..core.pagination import PaginationParams, create_pagination_params
from ..core.error_handling import APIError, ErrorCodes

logger = get_logger("workspace_query")

router = APIRouter(prefix="/api/workspaces/{workspace_id}/query", tags=["workspace-query"])

# ===== 查詢請求模型 =====

class QueryRequest(BaseModel):
    query: str
    defining_types: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    max_results: Optional[int] = 100

class UnifiedQueryRequest(BaseModel):
    query: str
    search_scope: Optional[str] = "selected"  # "selected", "all", "specific"
    specific_paper_ids: Optional[List[str]] = None
    include_sections: Optional[List[str]] = None  # 指定要搜尋的章節類型
    max_results: Optional[int] = 100

# ===== 查詢端點 =====

@router.post("/", response_model=Dict[str, Any])
async def process_workspace_query(
    workspace_id: UUID,
    query_data: QueryRequest,
    workspace: Workspace = Depends(get_workspace_for_user),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    在指定工作區內處理查詢
    """
    try:
        logger.info(f"處理工作區查詢 - workspace_id: {workspace_id}, query: {query_data.query}")
        
        # 取得工作區內已選取的論文
        selected_papers = await db_service.get_selected_papers_by_workspace(db, workspace_id)
        
        if not selected_papers:
            return {
                "success": False,
                "message": "工作區內沒有已選取的論文",
                "query": query_data.query,
                "workspace_id": str(workspace_id),
                "results": []
            }
        
        # 提取論文ID
        paper_ids = [str(paper.id) for paper in selected_papers]
        
        # 在工作區範圍內搜尋句子
        search_results = await db_service.search_sentences_in_workspace(
            db, 
            workspace_id,
            defining_types=query_data.defining_types,
            keywords=query_data.keywords
        )
        
        # 限制結果數量
        if query_data.max_results and len(search_results) > query_data.max_results:
            search_results = search_results[:query_data.max_results]
        
        return {
            "success": True,
            "message": f"在工作區內找到 {len(search_results)} 個相關句子",
            "query": query_data.query,
            "workspace_id": str(workspace_id),
            "paper_count": len(selected_papers),
            "results": search_results
        }
        
    except Exception as e:
        logger.error(f"工作區查詢處理失敗: {str(e)}")
        raise APIError(
            error_code=ErrorCodes.INTERNAL_SERVER_ERROR,
            detail=f"查詢處理失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.post("/unified", response_model=Dict[str, Any])
async def unified_workspace_query(
    workspace_id: UUID,
    query_data: UnifiedQueryRequest,
    workspace: Workspace = Depends(get_workspace_for_user),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    工作區統一查詢 - 支援多種搜尋範圍和參數
    """
    try:
        logger.info(f"統一工作區查詢 - workspace_id: {workspace_id}, query: {query_data.query}")
        
        # 根據搜尋範圍取得論文
        if query_data.search_scope == "selected":
            papers = await db_service.get_selected_papers_by_workspace(db, workspace_id)
        elif query_data.search_scope == "all":
            # 取得工作區所有論文（不分頁）
            papers = await db_service.get_papers_by_workspace(db, workspace_id)
            if isinstance(papers, dict) and 'items' in papers:
                papers = papers['items']
            elif isinstance(papers, list):
                # 轉換為 Paper 物件
                papers = [p for p in papers if hasattr(p, 'id')]
        elif query_data.search_scope == "specific" and query_data.specific_paper_ids:
            # 驗證指定的論文都屬於此工作區
            papers = []
            for paper_id in query_data.specific_paper_ids:
                paper = await db_service.get_paper_by_id_and_workspace(db, paper_id, workspace_id)
                if paper:
                    papers.append(paper)
        else:
            papers = []
        
        if not papers:
            return {
                "success": False,
                "message": f"在搜尋範圍 '{query_data.search_scope}' 內沒有找到論文",
                "query": query_data.query,
                "workspace_id": str(workspace_id),
                "search_scope": query_data.search_scope,
                "results": []
            }
        
        # 提取論文ID
        paper_ids = [str(p.id) if hasattr(p, 'id') else str(p['id']) for p in papers]
        
        # 使用統一查詢服務
        try:
            # 構建查詢參數
            query_params = {
                "query": query_data.query,
                "paper_ids": paper_ids,
                "workspace_id": str(workspace_id),
                "include_sections": query_data.include_sections,
                "max_results": query_data.max_results
            }
            
            # 調用統一查詢服務
            search_results = await unified_query_processor.process_query(db, query_params)
            
            return {
                "success": True,
                "message": f"統一查詢完成，找到 {len(search_results.get('results', []))} 個結果",
                "query": query_data.query,
                "workspace_id": str(workspace_id),
                "search_scope": query_data.search_scope,
                "paper_count": len(papers),
                "results": search_results
            }
            
        except Exception as e:
            logger.error(f"統一查詢服務調用失敗: {str(e)}")
            # 回退到基本搜尋
            search_results = await db_service.search_sentences_in_workspace(
                db, workspace_id, keywords=[query_data.query]
            )
            
            if query_data.max_results and len(search_results) > query_data.max_results:
                search_results = search_results[:query_data.max_results]
            
            return {
                "success": True,
                "message": f"基本查詢完成，找到 {len(search_results)} 個結果",
                "query": query_data.query,
                "workspace_id": str(workspace_id),
                "search_scope": query_data.search_scope,
                "paper_count": len(papers),
                "results": search_results,
                "fallback": True
            }
        
    except Exception as e:
        logger.error(f"統一工作區查詢失敗: {str(e)}")
        raise APIError(
            error_code=ErrorCodes.INTERNAL_SERVER_ERROR,
            detail=f"統一查詢失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.post("/test", response_model=Dict[str, Any])
async def test_workspace_query(
    workspace_id: UUID,
    query_data: UnifiedQueryRequest,
    workspace: Workspace = Depends(get_workspace_for_user),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    測試工作區查詢功能 - 提供詳細的調試資訊
    """
    try:
        logger.info(f"測試工作區查詢 - workspace_id: {workspace_id}")
        
        # 取得工作區基本資訊
        workspace_info = {
            "workspace_id": str(workspace_id),
            "workspace_name": workspace.name if hasattr(workspace, 'name') else "未知工作區"
        }
        
        # 取得工作區論文統計
        all_papers = await db_service.get_papers_by_workspace(db, workspace_id)
        selected_papers = await db_service.get_selected_papers_by_workspace(db, workspace_id)
        
        if isinstance(all_papers, dict) and 'items' in all_papers:
            total_papers = all_papers.get('total', len(all_papers['items']))
            all_papers_list = all_papers['items']
        else:
            total_papers = len(all_papers) if all_papers else 0
            all_papers_list = all_papers or []
        
        statistics = {
            "total_papers": total_papers,
            "selected_papers": len(selected_papers),
            "query_scope": query_data.search_scope
        }
        
        # 取得章節摘要
        sections_summary = await db_service.get_papers_sections_summary_by_workspace(db, workspace_id)
        
        # 執行測試查詢
        test_results = None
        if query_data.query and selected_papers:
            paper_ids = [str(paper.id) for paper in selected_papers]
            test_results = await db_service.search_sentences_in_workspace(
                db, workspace_id, keywords=[query_data.query]
            )
            
            # 限制測試結果數量
            if len(test_results) > 5:
                test_results = test_results[:5]
        
        return {
            "success": True,
            "message": "工作區查詢測試完成",
            "workspace_info": workspace_info,
            "statistics": statistics,
            "sections_summary": sections_summary,
            "test_query": query_data.query,
            "test_results": test_results,
            "test_result_count": len(test_results) if test_results else 0
        }
        
    except Exception as e:
        logger.error(f"測試工作區查詢失敗: {str(e)}")
        raise APIError(
            error_code=ErrorCodes.INTERNAL_SERVER_ERROR,
            detail=f"測試查詢失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# ===== 查詢統計和分析 =====

@router.get("/stats", response_model=Dict[str, Any])
async def get_workspace_query_stats(
    workspace_id: UUID,
    workspace: Workspace = Depends(get_workspace_for_user),
    db: AsyncSession = Depends(get_db)
):
    """
    取得工作區查詢相關統計資訊
    """
    try:
        # 取得工作區檔案統計
        sections_summary = await db_service.get_papers_sections_summary_by_workspace(db, workspace_id)
        
        # 取得選取的論文
        selected_papers = await db_service.get_selected_papers_by_workspace(db, workspace_id)
        
        # 計算可查詢的內容統計
        queryable_stats = {
            "selected_papers": len(selected_papers),
            "total_sections": sections_summary.get("total_sections", 0),
            "total_sentences": sections_summary.get("total_sentences", 0),
            "avg_sections_per_paper": (
                sections_summary.get("total_sections", 0) / max(1, len(selected_papers))
            ),
            "avg_sentences_per_paper": (
                sections_summary.get("total_sentences", 0) / max(1, len(selected_papers))
            )
        }
        
        return {
            "success": True,
            "workspace_id": str(workspace_id),
            "queryable_stats": queryable_stats,
            "sections_summary": sections_summary,
            "query_ready": len(selected_papers) > 0
        }
        
    except Exception as e:
        logger.error(f"取得工作區查詢統計失敗: {str(e)}")
        raise APIError(
            error_code=ErrorCodes.INTERNAL_SERVER_ERROR,
            detail=f"取得查詢統計失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        ) 