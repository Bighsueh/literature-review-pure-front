# 模型定義 
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class HealthResponse(BaseModel):
    """健康檢查響應模型"""
    status: str = Field(..., description="系統健康狀態")

class SentenceWithPage(BaseModel):
    """帶頁碼的句子模型"""
    sentence: str = Field(..., description="提取的句子")
    page: int = Field(..., description="句子所在頁碼")

class SentenceResponse(BaseModel):
    """句子列表響應模型"""
    sentences: List[SentenceWithPage] = Field(..., description="帶頁碼的句子列表")

class ErrorResponse(BaseModel):
    """錯誤響應模型"""
    error: str = Field(..., description="錯誤信息")

class WebSocketProgressUpdate(BaseModel):
    """WebSocket 進度更新模型"""
    status: str = Field(..., description="處理狀態")
    progress: float = Field(..., description="處理進度，0.0 到 1.0")
    message: str = Field(..., description="進度消息")

class WebSocketCompletedResponse(BaseModel):
    """WebSocket 完成響應模型"""
    status: str = Field(..., description="完成狀態，值為 'completed'")
    progress: float = Field(1.0, description="進度值，完成時為 1.0")
    sentences: List[SentenceWithPage] = Field(..., description="帶頁碼的句子列表")

class WebSocketErrorResponse(BaseModel):
    """WebSocket 錯誤響應模型"""
    status: str = Field(..., description="錯誤狀態，值為 'error'")
    error: str = Field(..., description="錯誤信息")

# TEI Section 輸入模型
class TEISection(BaseModel):
    section_type: str = Field(..., description="章節類型，如 abstract, introduction, methods 等")
    content: str = Field(..., description="章節文本內容")
    page_start: Optional[int] = Field(None, description="章節起始頁碼")
    page_end: Optional[int] = Field(None, description="章節結束頁碼")

class TEISplitRequest(BaseModel):
    sections: List[TEISection] = Field(..., description="要處理的章節列表")
    language: Optional[str] = Field("mixed", description="文本語言：zh, en, mixed")

# 處理後的句子模型
class ProcessedSentence(BaseModel):
    text: str = Field(..., description="句子文本")
    section_type: str = Field(..., description="所屬章節類型")
    sentence_order: int = Field(..., description="句子在章節中的順序")
    page_num: Optional[int] = Field(None, description="句子所在頁碼")
    confidence: float = Field(1.0, description="句子切分的信心度")

class ProcessingStats(BaseModel):
    total_sections: int = Field(..., description="處理的章節數")
    total_sentences: int = Field(..., description="生成的句子總數")
    processing_time_ms: float = Field(..., description="處理時間（毫秒）")

class TEISplitResponse(BaseModel):
    sentences: List[ProcessedSentence] = Field(..., description="處理後的句子列表")
    processing_stats: ProcessingStats = Field(..., description="處理統計資訊") 