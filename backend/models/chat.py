"""
對話歷史模型
支援工作區隔離的對話記錄
"""

from sqlalchemy import Column, String, ForeignKey, TIMESTAMP, UUID, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from .base import Base

# ===== SQLAlchemy ORM Models =====

class ChatHistory(Base):
    __tablename__ = "chat_histories"
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID, ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False)
    user_question = Column(Text, nullable=False)
    ai_response = Column(Text, nullable=False)
    context_papers = Column(JSON, nullable=True)  # 儲存相關論文ID列表
    context_sentences = Column(JSON, nullable=True)  # 儲存相關句子ID列表
    query_metadata = Column(JSON, nullable=True)  # 儲存查詢的元數據（如查詢時間、處理時間等）
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    
    # Relationships
    workspace = relationship("Workspace", back_populates="chat_histories")

# ===== Pydantic Schemas =====

class ChatHistoryBase(BaseModel):
    user_question: str
    ai_response: str
    context_papers: Optional[List[str]] = None
    context_sentences: Optional[List[str]] = None
    query_metadata: Optional[Dict[str, Any]] = None

class ChatHistoryCreate(ChatHistoryBase):
    workspace_id: str

class ChatHistoryResponse(ChatHistoryBase):
    id: str
    workspace_id: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class ChatHistoryListResponse(BaseModel):
    chats: List[ChatHistoryResponse]
    total_count: int
    page: int
    page_size: int
    has_next: bool
    has_previous: bool

class ChatContextInfo(BaseModel):
    """對話上下文信息"""
    paper_titles: List[str] = []
    sentence_count: int = 0
    source_papers: List[Dict[str, Any]] = []
    
class ChatWithContextResponse(ChatHistoryResponse):
    """包含上下文信息的對話響應"""
    context_info: Optional[ChatContextInfo] = None 