"""
遺留資料存取 API - 重構版本
負責處理遺留資料的安全存取，確保嚴格的工作區隔離
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime

from backend.core.database import get_db
from backend.core.security import get_current_user
from backend.core.logging import get_logger
from backend.api.dependencies import get_workspace_access_dependency
from backend.services.db_service import db_service
from backend.models.user import User
from backend.models.paper import Paper
from backend.models.user import Workspace

router = APIRouter(prefix="/legacy", tags=["legacy"])
logger = get_logger(__name__)

# 工作區權限依賴
WorkspaceAccessDep = get_workspace_access_dependency()

@router.get("/papers")
async def get_legacy_papers(
    workspace_id: str = Query(..., description="工作區ID"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _workspace_access: dict = Depends(WorkspaceAccessDep)
):
    """
    獲取工作區範圍內的遺留論文資料 - 嚴格工作區隔離
    """
    try:
        workspace_uuid = uuid.UUID(workspace_id)
        
        # 驗證工作區存取權限
        has_access = await db_service.verify_workspace_access(db, current_user.id, workspace_uuid)
        if not has_access:
            raise HTTPException(
                status_code=403, 
                detail=f"用戶無權存取工作區 {workspace_id}"
            )
        
        # 獲取工作區論文，限制查詢範圍
        papers = await db_service.get_papers_by_workspace(
            db, workspace_uuid, limit=limit, offset=offset
        )
        
        # 格式化回應
        formatted_papers = []
        for paper in papers:
            formatted_papers.append({
                'id': str(paper.id),
                'file_name': paper.file_name,
                'original_filename': paper.original_filename,
                'title': paper.original_filename or paper.file_name or '',
                'upload_time': getattr(paper, 'upload_time', paper.upload_timestamp).isoformat() if getattr(paper, 'upload_time', paper.upload_timestamp) else None,
                'processing_status': paper.processing_status,
                'is_selected': getattr(paper, 'is_selected', False),
                'workspace_id': str(paper.workspace_id),
                'file_size': paper.file_size,
                'file_type': getattr(paper, 'file_type', 'pdf')
            })
        
        logger.info(f"用戶 {current_user.id} 存取工作區 {workspace_id} 的 {len(formatted_papers)} 篇論文")
        
        return {
            'success': True,
            'data': formatted_papers,
            'total': len(formatted_papers),
            'workspace_id': workspace_id,
            'access_timestamp': datetime.now().isoformat()
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="無效的工作區ID格式")
    except Exception as e:
        logger.error(f"獲取遺留論文失敗: user={current_user.id}, workspace={workspace_id}, error={str(e)}")
        raise HTTPException(status_code=500, detail="內部伺服器錯誤")

@router.get("/papers/{paper_id}")
async def get_legacy_paper_detail(
    paper_id: str,
    workspace_id: str = Query(..., description="工作區ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _workspace_access: dict = Depends(WorkspaceAccessDep)
):
    """
    獲取特定論文的詳細資訊 - 嚴格工作區隔離
    """
    try:
        workspace_uuid = uuid.UUID(workspace_id)
        paper_uuid = uuid.UUID(paper_id)
        
        # 驗證工作區存取權限
        has_access = await db_service.verify_workspace_access(db, current_user.id, workspace_uuid)
        if not has_access:
            raise HTTPException(
                status_code=403,
                detail=f"用戶無權存取工作區 {workspace_id}"
            )
        
        # 獲取論文並驗證歸屬
        paper = await db_service.get_paper_by_id(db, paper_uuid)
        if not paper:
            raise HTTPException(status_code=404, detail="論文不存在")
        
        # 確保論文屬於指定工作區
        if str(paper.workspace_id) != workspace_id:
            raise HTTPException(
                status_code=403,
                detail="論文不屬於指定工作區"
            )
        
        # 獲取論文章節資訊
        sections = await db_service.get_sections_by_paper_id(db, paper_uuid)
        
        # 格式化回應
        formatted_sections = []
        for section in sections:
            formatted_sections.append({
                'id': str(section.id),
                'section_type': section.section_type,
                'page_num': section.page_num,
                'content_preview': (section.content or '')[:200] + "..." if section.content else "",
                'word_count': len(section.content.split()) if section.content else 0
            })
        
        paper_detail = {
            'id': str(paper.id),
            'file_name': paper.file_name,
            'original_filename': paper.original_filename,
            'title': paper.original_filename or paper.file_name or '',
            'upload_time': getattr(paper, 'upload_time', paper.upload_timestamp).isoformat() if getattr(paper, 'upload_time', paper.upload_timestamp) else None,
            'processing_status': paper.processing_status,
            'is_selected': getattr(paper, 'is_selected', False),
            'workspace_id': str(paper.workspace_id),
            'file_size': paper.file_size,
            'file_type': getattr(paper, 'file_type', 'pdf'),
            'sections': formatted_sections,
            'section_count': len(formatted_sections)
        }
        
        logger.info(f"用戶 {current_user.id} 存取論文 {paper_id} 詳細資訊")
        
        return {
            'success': True,
            'data': paper_detail,
            'workspace_id': workspace_id,
            'access_timestamp': datetime.now().isoformat()
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="無效的ID格式")
    except Exception as e:
        logger.error(f"獲取論文詳細資訊失敗: user={current_user.id}, paper={paper_id}, error={str(e)}")
        raise HTTPException(status_code=500, detail="內部伺服器錯誤")

@router.get("/sentences")
async def get_legacy_sentences(
    workspace_id: str = Query(..., description="工作區ID"),
    paper_id: Optional[str] = Query(None, description="論文ID"),
    section_type: Optional[str] = Query(None, description="章節類型"),
    defining_type: Optional[str] = Query(None, description="定義類型 (OD/CD)"),
    keyword: Optional[str] = Query(None, description="關鍵詞搜尋"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _workspace_access: dict = Depends(WorkspaceAccessDep)
):
    """
    獲取工作區範圍內的句子資料 - 嚴格工作區隔離
    """
    try:
        workspace_uuid = uuid.UUID(workspace_id)
        
        # 驗證工作區存取權限
        has_access = await db_service.verify_workspace_access(db, current_user.id, workspace_uuid)
        if not has_access:
            raise HTTPException(
                status_code=403,
                detail=f"用戶無權存取工作區 {workspace_id}"
            )
        
        # 構建搜尋參數
        search_params = {
            'workspace_id': workspace_uuid,
            'limit': limit,
            'offset': offset
        }
        
        if paper_id:
            try:
                paper_uuid = uuid.UUID(paper_id)
                # 驗證論文屬於工作區
                paper = await db_service.get_paper_by_id(db, paper_uuid)
                if not paper or str(paper.workspace_id) != workspace_id:
                    raise HTTPException(
                        status_code=403,
                        detail="論文不屬於指定工作區"
                    )
                search_params['paper_name'] = paper.file_name
            except ValueError:
                raise HTTPException(status_code=400, detail="無效的論文ID格式")
        
        if section_type:
            search_params['section_type'] = section_type
        
        if defining_type:
            search_params['defining_types'] = [defining_type]
        
        if keyword:
            search_params['keywords'] = [keyword]
        
        # 在工作區範圍內搜尋句子
        sentences = await db_service.search_sentences_in_workspace(db, **search_params)
        
        # 格式化回應
        formatted_sentences = []
        for sentence in sentences:
            formatted_sentences.append({
                'id': sentence.get('sentence_id'),
                'content': sentence.get('content'),
                'defining_type': sentence.get('defining_type'),
                'page_num': sentence.get('page_num'),
                'sentence_order': sentence.get('sentence_order'),
                'file_name': sentence.get('file_name'),
                'section_type': sentence.get('section_type'),
                'workspace_id': sentence.get('workspace_id')
            })
        
        logger.info(f"用戶 {current_user.id} 在工作區 {workspace_id} 搜尋到 {len(formatted_sentences)} 個句子")
        
        return {
            'success': True,
            'data': formatted_sentences,
            'total': len(formatted_sentences),
            'search_params': {
                'workspace_id': workspace_id,
                'paper_id': paper_id,
                'section_type': section_type,
                'defining_type': defining_type,
                'keyword': keyword
            },
            'access_timestamp': datetime.now().isoformat()
        }
        
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"搜尋句子失敗: user={current_user.id}, workspace={workspace_id}, error={str(e)}")
        raise HTTPException(status_code=500, detail="內部伺服器錯誤")

@router.post("/data-migration")
async def migrate_legacy_data(
    workspace_id: str = Query(..., description="目標工作區ID"),
    migration_type: str = Query("full", description="遷移類型: full/partial"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _workspace_access: dict = Depends(WorkspaceAccessDep)
):
    """
    遷移遺留資料到指定工作區 - 安全遷移
    """
    try:
        workspace_uuid = uuid.UUID(workspace_id)
        
        # 驗證工作區存取權限
        has_access = await db_service.verify_workspace_access(db, current_user.id, workspace_uuid)
        if not has_access:
            raise HTTPException(
                status_code=403,
                detail=f"用戶無權存取工作區 {workspace_id}"
            )
        
        # 獲取工作區資訊
        workspace = await db_service.get_workspace_by_id(db, workspace_uuid)
        if not workspace:
            raise HTTPException(status_code=404, detail="工作區不存在")
        
        # 檢查遷移權限 - 只有工作區擁有者可以執行遷移
        if str(workspace.user_id) != str(current_user.id):
            raise HTTPException(
                status_code=403,
                detail="只有工作區擁有者可以執行資料遷移"
            )
        
        # 執行遷移 (這裡是框架，實際實作需要根據具體需求)
        migration_result = {
            'migration_id': str(uuid.uuid4()),
            'workspace_id': workspace_id,
            'migration_type': migration_type,
            'status': 'initiated',
            'timestamp': datetime.now().isoformat(),
            'user_id': str(current_user.id)
        }
        
        logger.info(f"用戶 {current_user.id} 發起工作區 {workspace_id} 的資料遷移")
        
        return {
            'success': True,
            'data': migration_result,
            'message': '資料遷移已啟動，請稍後檢查進度'
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="無效的工作區ID格式")
    except Exception as e:
        logger.error(f"資料遷移失敗: user={current_user.id}, workspace={workspace_id}, error={str(e)}")
        raise HTTPException(status_code=500, detail="內部伺服器錯誤")

@router.get("/access-log")
async def get_legacy_access_log(
    workspace_id: str = Query(..., description="工作區ID"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _workspace_access: dict = Depends(WorkspaceAccessDep)
):
    """
    獲取工作區存取記錄 - 審計追蹤
    """
    try:
        workspace_uuid = uuid.UUID(workspace_id)
        
        # 驗證工作區存取權限
        has_access = await db_service.verify_workspace_access(db, current_user.id, workspace_uuid)
        if not has_access:
            raise HTTPException(
                status_code=403,
                detail=f"用戶無權存取工作區 {workspace_id}"
            )
        
        # 這裡應該從存取記錄表中獲取資料
        # 目前返回模擬資料
        access_log = [
            {
                'id': str(uuid.uuid4()),
                'user_id': str(current_user.id),
                'workspace_id': workspace_id,
                'action': 'legacy_data_access',
                'resource_type': 'papers',
                'timestamp': datetime.now().isoformat(),
                'ip_address': '127.0.0.1',  # 實際應該從請求中獲取
                'user_agent': 'API Client'
            }
        ]
        
        return {
            'success': True,
            'data': access_log,
            'workspace_id': workspace_id,
            'access_timestamp': datetime.now().isoformat()
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="無效的工作區ID格式")
    except Exception as e:
        logger.error(f"獲取存取記錄失敗: user={current_user.id}, workspace={workspace_id}, error={str(e)}")
        raise HTTPException(status_code=500, detail="內部伺服器錯誤") 