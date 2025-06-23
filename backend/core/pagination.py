"""
統一的分頁機制
提供標準化的分頁參數和響應格式
"""

from typing import TypeVar, Generic, List, Optional, Dict, Any
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from sqlalchemy.sql.selectable import Select
from fastapi import Query
import math

T = TypeVar('T')

class PaginationParams(BaseModel):
    """分頁參數"""
    page: int = Field(1, ge=1, description="頁碼，從1開始")
    size: int = Field(50, ge=1, le=100, description="每頁數量，最大100")
    sort_by: Optional[str] = Field(None, description="排序字段")
    sort_order: str = Field("desc", pattern="^(asc|desc)$", description="排序方向：asc或desc")

class PaginationMeta(BaseModel):
    """分頁元數據"""
    page: int
    size: int
    total: int
    total_pages: int
    has_next: bool
    has_previous: bool

class PaginatedResponse(BaseModel, Generic[T]):
    """分頁響應格式"""
    items: List[T]
    meta: PaginationMeta

def create_pagination_params(
    page: int = Query(1, ge=1, description="頁碼，從1開始"),
    size: int = Query(50, ge=1, le=100, description="每頁數量，最大100"),
    sort_by: Optional[str] = Query(None, description="排序字段"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="排序方向")
) -> PaginationParams:
    """
    創建分頁參數的FastAPI依賴項
    
    Usage:
        @app.get("/items")
        async def get_items(pagination: PaginationParams = Depends(create_pagination_params)):
            ...
    """
    return PaginationParams(
        page=page,
        size=size,
        sort_by=sort_by,
        sort_order=sort_order
    )

async def paginate_query(
    db: AsyncSession,
    query: Select,
    pagination: PaginationParams,
    count_query: Optional[Select] = None
) -> tuple[List[Any], PaginationMeta]:
    """
    對SQLAlchemy查詢應用分頁
    
    Args:
        db: 數據庫會話
        query: 主查詢語句
        pagination: 分頁參數
        count_query: 可選的計數查詢，如果不提供會自動生成
    
    Returns:
        (結果列表, 分頁元數據)
    """
    
    # 計算總數
    if count_query is None:
        # 從主查詢生成計數查詢
        count_query = select(func.count()).select_from(query.subquery())
    
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # 計算偏移量
    offset = (pagination.page - 1) * pagination.size
    
    # 應用分頁
    paginated_query = query.offset(offset).limit(pagination.size)
    
    # 執行查詢
    result = await db.execute(paginated_query)
    items = result.scalars().all()
    
    # 計算分頁元數據
    total_pages = math.ceil(total / pagination.size) if total > 0 else 0
    has_next = pagination.page < total_pages
    has_previous = pagination.page > 1
    
    meta = PaginationMeta(
        page=pagination.page,
        size=pagination.size,
        total=total,
        total_pages=total_pages,
        has_next=has_next,
        has_previous=has_previous
    )
    
    return items, meta

class FilterParams(BaseModel):
    """通用過濾參數"""
    search: Optional[str] = Field(None, description="搜索關鍵字")
    status: Optional[str] = Field(None, description="狀態過濾")
    start_date: Optional[str] = Field(None, description="開始日期 (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="結束日期 (YYYY-MM-DD)")

def create_filter_params(
    search: Optional[str] = Query(None, description="搜索關鍵字"),
    status: Optional[str] = Query(None, description="狀態過濾"),
    start_date: Optional[str] = Query(None, description="開始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="結束日期 (YYYY-MM-DD)")
) -> FilterParams:
    """
    創建過濾參數的FastAPI依賴項
    """
    return FilterParams(
        search=search,
        status=status,
        start_date=start_date,
        end_date=end_date
    )

class SortableField:
    """可排序字段定義"""
    def __init__(self, field_name: str, db_column, default_order: str = "desc"):
        self.field_name = field_name
        self.db_column = db_column
        self.default_order = default_order

def apply_sorting(query: Select, pagination: PaginationParams, sortable_fields: Dict[str, SortableField]) -> Select:
    """
    對查詢應用排序
    
    Args:
        query: SQLAlchemy查詢
        pagination: 分頁參數
        sortable_fields: 可排序字段映射
    
    Returns:
        應用排序後的查詢
    """
    if pagination.sort_by and pagination.sort_by in sortable_fields:
        field = sortable_fields[pagination.sort_by]
        if pagination.sort_order == "asc":
            query = query.order_by(field.db_column.asc())
        else:
            query = query.order_by(field.db_column.desc())
    else:
        # 使用默認排序
        default_field = next(iter(sortable_fields.values()))
        if default_field.default_order == "asc":
            query = query.order_by(default_field.db_column.asc())
        else:
            query = query.order_by(default_field.db_column.desc())
    
    return query

class CacheConfig:
    """快取配置"""
    def __init__(self, ttl: int = 300, key_prefix: str = ""):
        self.ttl = ttl  # 快取存活時間（秒）
        self.key_prefix = key_prefix

def generate_cache_key(prefix: str, **kwargs) -> str:
    """
    生成快取鍵
    
    Args:
        prefix: 前綴
        **kwargs: 鍵值對參數
    
    Returns:
        快取鍵字符串
    """
    parts = [prefix]
    for key, value in sorted(kwargs.items()):
        if value is not None:
            parts.append(f"{key}:{value}")
    
    return ":".join(parts)

# 工作區相關的分頁輔助函數
async def paginate_workspace_papers(
    db: AsyncSession,
    workspace_id: str,
    pagination: PaginationParams,
    filters: Optional[FilterParams] = None
) -> tuple[List[Any], PaginationMeta]:
    """
    分頁獲取工作區中的論文
    """
    from ..models.paper import Paper
    
    # 構建基礎查詢
    query = select(Paper).where(Paper.workspace_id == workspace_id)
    
    # 應用過濾條件
    if filters:
        if filters.search:
            query = query.where(
                Paper.file_name.ilike(f"%{filters.search}%") |
                Paper.original_filename.ilike(f"%{filters.search}%")
            )
        
        if filters.status:
            query = query.where(Paper.processing_status == filters.status)
        
        if filters.start_date:
            query = query.where(Paper.upload_timestamp >= filters.start_date)
        
        if filters.end_date:
            query = query.where(Paper.upload_timestamp <= filters.end_date)
    
    # 定義可排序字段
    sortable_fields = {
        "upload_timestamp": SortableField("upload_timestamp", Paper.upload_timestamp, "desc"),
        "file_name": SortableField("file_name", Paper.file_name, "asc"),
        "file_size": SortableField("file_size", Paper.file_size, "desc"),
        "processing_status": SortableField("processing_status", Paper.processing_status, "asc")
    }
    
    # 應用排序
    query = apply_sorting(query, pagination, sortable_fields)
    
    # 執行分頁查詢
    return await paginate_query(db, query, pagination)

async def paginate_workspace_chats(
    db: AsyncSession,
    workspace_id: str,
    pagination: PaginationParams,
    filters: Optional[FilterParams] = None
) -> tuple[List[Any], PaginationMeta]:
    """
    分頁獲取工作區中的對話歷史
    """
    from ..models.chat import ChatHistory
    
    # 構建基礎查詢
    query = select(ChatHistory).where(ChatHistory.workspace_id == workspace_id)
    
    # 應用過濾條件
    if filters:
        if filters.search:
            query = query.where(
                ChatHistory.user_question.ilike(f"%{filters.search}%") |
                ChatHistory.ai_response.ilike(f"%{filters.search}%")
            )
        
        if filters.start_date:
            query = query.where(ChatHistory.created_at >= filters.start_date)
        
        if filters.end_date:
            query = query.where(ChatHistory.created_at <= filters.end_date)
    
    # 定義可排序字段
    sortable_fields = {
        "created_at": SortableField("created_at", ChatHistory.created_at, "desc")
    }
    
    # 應用排序
    query = apply_sorting(query, pagination, sortable_fields)
    
    # 執行分頁查詢
    return await paginate_query(db, query, pagination) 