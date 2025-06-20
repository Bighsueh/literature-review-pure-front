"""
共用的資料庫基礎模型
解決循環導入和Base類衝突問題
"""

from sqlalchemy.ext.declarative import declarative_base
import uuid

# 創建唯一的Base類供所有模型使用
Base = declarative_base() 