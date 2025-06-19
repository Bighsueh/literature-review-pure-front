from sqlalchemy import Column, String, ForeignKey, TIMESTAMP, UUID, Text, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

Base = declarative_base()

# ===== SQLAlchemy ORM Models =====

class ChatHistory(Base):
    __tablename__ = "chat_histories"
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID, ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    message_metadata = Column(JSONB)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    
    # Relationships
    workspace = relationship("Workspace", back_populates="chat_histories")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')", name='check_role_valid'),
    )


# ===== Pydantic Schemas =====

class ChatHistoryBase(BaseModel):
    role: str = Field(..., pattern=r'^(user|assistant)$')
    content: str
    message_metadata: Optional[Dict[str, Any]] = None


class ChatHistoryCreate(ChatHistoryBase):
    workspace_id: str


class ChatHistoryResponse(ChatHistoryBase):
    id: str
    workspace_id: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class ChatSessionResponse(BaseModel):
    workspace_id: str
    workspace_name: str
    messages: List[ChatHistoryResponse] = []
    
    class Config:
        from_attributes = True 