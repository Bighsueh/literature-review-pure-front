"""
API模組初始化
包含所有API路由的定義
"""

from .papers import router as papers_router
from .upload import router as upload_router
from .processing import router as processing_router

__all__ = ["papers_router", "upload_router", "processing_router"] 