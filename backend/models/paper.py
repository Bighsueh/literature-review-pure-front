from sqlalchemy import Column, String, Integer, Text, Boolean, TIMESTAMP, DECIMAL, ForeignKey, UUID, BIGINT
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid

Base = declarative_base()

# ===== SQLAlchemy ORM Models =====

class Paper(Base):
    __tablename__ = "papers"
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    file_name = Column(String(255), nullable=False)
    original_filename = Column(String(255))
    upload_timestamp = Column(TIMESTAMP, default=func.current_timestamp())
    processing_status = Column(String(50), default='uploading')
    file_size = Column(BIGINT)
    file_hash = Column(String(64), unique=True)
    grobid_processed = Column(Boolean, default=False)
    sentences_processed = Column(Boolean, default=False)
    od_cd_processed = Column(Boolean, default=False)
    pdf_deleted = Column(Boolean, default=False)
    error_message = Column(Text)
    tei_xml = Column(Text)
    tei_metadata = Column(JSONB)
    processing_completed_at = Column(TIMESTAMP)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    
    # Relationships
    sections = relationship("PaperSection", back_populates="paper", cascade="all, delete-orphan")
    sentences = relationship("Sentence", back_populates="paper", cascade="all, delete-orphan")
    selection = relationship("PaperSelection", back_populates="paper", uselist=False, cascade="all, delete-orphan")
    processing_queue = relationship("ProcessingQueue", back_populates="paper", cascade="all, delete-orphan")

class PaperSection(Base):
    __tablename__ = "paper_sections"
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    paper_id = Column(UUID, ForeignKey('papers.id', ondelete='CASCADE'), nullable=False)
    section_type = Column(String(50), nullable=False)
    page_num = Column(Integer)
    content = Column(Text, nullable=False)
    section_order = Column(Integer)
    tei_coordinates = Column(JSONB)
    word_count = Column(Integer)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    
    # Relationships
    paper = relationship("Paper", back_populates="sections")
    sentences = relationship("Sentence", back_populates="section", cascade="all, delete-orphan")

class Sentence(Base):
    __tablename__ = "sentences"
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    paper_id = Column(UUID, ForeignKey('papers.id', ondelete='CASCADE'), nullable=False)
    section_id = Column(UUID, ForeignKey('paper_sections.id', ondelete='CASCADE'), nullable=False)
    content = Column(Text, nullable=False)
    sentence_order = Column(Integer)
    word_count = Column(Integer)
    char_count = Column(Integer)
    
    # 檢測結果欄位
    has_objective = Column(Boolean, default=None)
    has_dataset = Column(Boolean, default=None)
    has_contribution = Column(Boolean, default=None)
    detection_status = Column(String(20), default='unknown')
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    explanation = Column(Text)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, default=func.current_timestamp())
    
    # Relationships
    paper = relationship("Paper", back_populates="sentences")
    section = relationship("PaperSection", back_populates="sentences")

    # 為了向後相容，添加一個屬性別名
    @property
    def sentence_text(self):
        return self.content
    
    @sentence_text.setter
    def sentence_text(self, value):
        self.content = value

class PaperSelection(Base):
    __tablename__ = "paper_selections"
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    paper_id = Column(UUID, ForeignKey('papers.id', ondelete='CASCADE'), nullable=False, unique=True)
    is_selected = Column(Boolean, default=True)
    selected_timestamp = Column(TIMESTAMP, default=func.current_timestamp())
    
    # Relationships
    paper = relationship("Paper", back_populates="selection")

class ProcessingQueue(Base):
    __tablename__ = "processing_queue"
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    paper_id = Column(UUID, ForeignKey('papers.id', ondelete='CASCADE'), nullable=False)
    processing_stage = Column(String(50), nullable=False)
    status = Column(String(20), default='pending')
    priority = Column(Integer, default=0)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    started_at = Column(TIMESTAMP)
    completed_at = Column(TIMESTAMP)
    error_message = Column(Text)
    processing_details = Column(JSONB)
    
    # Relationships
    paper = relationship("Paper", back_populates="processing_queue")

class SystemSettings(Base):
    __tablename__ = "system_settings"
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    setting_key = Column(String(100), unique=True, nullable=False)
    setting_value = Column(JSONB)
    description = Column(Text)
    updated_at = Column(TIMESTAMP, default=func.current_timestamp())

# ===== Pydantic Schemas =====

class ProcessingStatusEnum(str, Enum):
    uploading = "uploading"
    processing = "processing"
    completed = "completed"
    error = "error"

class DefiningTypeEnum(str, Enum):
    OD = "OD"
    CD = "CD" 
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"

# Base schemas
class PaperBase(BaseModel):
    file_name: str
    original_filename: Optional[str] = None
    file_size: Optional[int] = None

class PaperCreate(PaperBase):
    file_hash: str

class PaperUpdate(BaseModel):
    processing_status: Optional[ProcessingStatusEnum] = None
    grobid_processed: Optional[bool] = None
    sentences_processed: Optional[bool] = None
    od_cd_processed: Optional[bool] = None
    pdf_deleted: Optional[bool] = None
    error_message: Optional[str] = None
    tei_xml: Optional[str] = None
    tei_metadata: Optional[Dict[str, Any]] = None
    processing_completed_at: Optional[datetime] = None

class PaperResponse(PaperBase):
    id: str
    upload_timestamp: datetime
    processing_status: ProcessingStatusEnum
    grobid_processed: bool
    sentences_processed: bool
    od_cd_processed: bool
    pdf_deleted: bool
    error_message: Optional[str] = None
    processing_completed_at: Optional[datetime] = None
    created_at: datetime
    is_selected: Optional[bool] = None  # From PaperSelection
    
    class Config:
        from_attributes = True

# Section schemas
class SectionBase(BaseModel):
    section_type: str
    page_num: Optional[int] = None
    content: str
    section_order: Optional[int] = None
    word_count: Optional[int] = None

class SectionCreate(SectionBase):
    paper_id: str
    tei_coordinates: Optional[Dict[str, Any]] = None

class SectionResponse(SectionBase):
    id: str
    paper_id: str
    tei_coordinates: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# Sentence schemas
class SentenceBase(BaseModel):
    content: str  # 改為 content
    sentence_order: Optional[int] = None
    word_count: Optional[int] = None
    char_count: Optional[int] = None
    # 檢測結果欄位
    has_objective: Optional[bool] = None
    has_dataset: Optional[bool] = None
    has_contribution: Optional[bool] = None
    detection_status: Optional[str] = 'unknown'
    error_message: Optional[str] = None
    retry_count: Optional[int] = 0
    explanation: Optional[str] = None
    
    # 為了向後相容，添加一個屬性別名
    @property
    def sentence_text(self):
        return self.content
    
    @sentence_text.setter
    def sentence_text(self, value):
        self.content = value

class SentenceCreate(SentenceBase):
    paper_id: str
    section_id: str

class SentenceResponse(SentenceBase):
    id: str
    paper_id: str
    section_id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Processing queue schemas
class ProcessingQueueCreate(BaseModel):
    paper_id: str
    processing_stage: str
    priority: int = 0

class ProcessingQueueUpdate(BaseModel):
    status: Optional[str] = None
    retry_count: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    processing_details: Optional[Dict[str, Any]] = None

class ProcessingQueueResponse(BaseModel):
    id: str
    paper_id: str
    processing_stage: str
    status: str
    priority: int
    retry_count: int
    max_retries: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    processing_details: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True

# Paper selection schemas
class PaperSelectionUpdate(BaseModel):
    is_selected: bool

class PaperSelectionResponse(BaseModel):
    id: str
    paper_id: str
    is_selected: bool
    selected_timestamp: datetime
    
    class Config:
        from_attributes = True

# Complex response schemas
class PaperWithSectionsResponse(PaperResponse):
    sections: List[SectionResponse] = []

class SectionSummary(BaseModel):
    section_type: str
    page_num: Optional[int] = None
    word_count: Optional[int] = None
    brief_content: str
    od_count: int = 0
    cd_count: int = 0
    total_sentences: int = 0

class PaperSectionSummary(BaseModel):
    file_name: str
    sections: List[SectionSummary] = []

# Query schemas
class QueryRequest(BaseModel):
    query: str

class QueryResult(BaseModel):
    response: str
    references: Optional[List[Dict[str, Any]]] = None
    selected_sections: Optional[List[Dict[str, Any]]] = None
    analysis_focus: Optional[str] = None
    source_summary: Optional[Dict[str, Any]] = None

class UnifiedQueryRequest(BaseModel):
    """統一查詢請求模型"""
    query: str
    query_type: Optional[str] = "general"
    selected_paper_ids: Optional[List[str]] = None 
    options: Optional[Dict[str, Any]] = None 