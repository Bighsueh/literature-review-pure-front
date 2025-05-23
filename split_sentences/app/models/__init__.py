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