from sqlalchemy import Column, String, ForeignKey, TIMESTAMP, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Union
from datetime import datetime
import uuid

from .base import Base

# ===== SQLAlchemy ORM Models =====

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    google_id = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    picture_url = Column(String(500))
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, default=func.current_timestamp())
    
    # Relationships
    workspaces = relationship("Workspace", back_populates="user", cascade="all, delete-orphan")


class Workspace(Base):
    __tablename__ = "workspaces"
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, default=func.current_timestamp())
    
    # Relationships
    user = relationship("User", back_populates="workspaces")
    chat_histories = relationship("ChatHistory", back_populates="workspace", cascade="all, delete-orphan")
    
    # Paper-related relationships (added in DB-03, DB-04, DB-05)
    papers = relationship("Paper", back_populates="workspace", cascade="all, delete-orphan")
    sections = relationship("PaperSection", back_populates="workspace", cascade="all, delete-orphan")
    sentences = relationship("Sentence", back_populates="workspace", cascade="all, delete-orphan")
    paper_selections = relationship("PaperSelection", back_populates="workspace", cascade="all, delete-orphan")
    processing_queue = relationship("ProcessingQueue", back_populates="workspace", cascade="all, delete-orphan")


# ===== Pydantic Schemas =====

class UserBase(BaseModel):
    google_id: str
    email: str
    name: str
    picture_url: Optional[str] = None


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    name: Optional[str] = None
    picture_url: Optional[str] = None


class UserResponse(UserBase):
    id: str
    created_at: datetime
    updated_at: datetime
    
    @validator('id', pre=True)
    def convert_uuid_to_string(cls, v):
        """將 UUID 轉換為字串"""
        if isinstance(v, uuid.UUID):
            return str(v)
        return v
    
    class Config:
        from_attributes = True


class WorkspaceBase(BaseModel):
    name: str


class WorkspaceCreate(WorkspaceBase):
    pass  # 移除 user_id，從認證用戶中自動獲取


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = None


class WorkspaceResponse(WorkspaceBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    
    @validator('id', 'user_id', pre=True)
    def convert_uuid_to_string(cls, v):
        """將 UUID 轉換為字串"""
        if isinstance(v, uuid.UUID):
            return str(v)
        return v
    
    class Config:
        from_attributes = True


class UserWithWorkspacesResponse(UserResponse):
    workspaces: List[WorkspaceResponse] = [] 