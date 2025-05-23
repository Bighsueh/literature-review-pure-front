from pydantic import BaseModel
from typing import List, Optional

class ProcessResponse(BaseModel):
    """PDF 處理結果響應模型"""
    sentences: List[str]

class ErrorResponse(BaseModel):
    """錯誤響應模型"""
    error: str 