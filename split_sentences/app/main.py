from fastapi import FastAPI, File, UploadFile, WebSocket, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import json
import os
import uuid
import asyncio
from typing import Dict, List, Any, Optional, Union
import logging

from .pdf_processor import PDFProcessor, ProcessingStatus
from .models import SentenceResponse, ErrorResponse, HealthResponse

# 配置日誌
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 創建 FastAPI 應用
app = FastAPI(
    title="PDF 句子分割 API",
    description="從 PDF 文件中提取文本並分割成句子的 API 服務",
    version="1.0.0",
)

# 添加 CORS 支持
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 存儲活躍的 WebSocket 連接和處理狀態
active_connections: Dict[str, WebSocket] = {}
processing_statuses: Dict[str, ProcessingStatus] = {}

# 創建上傳目錄
UPLOAD_DIR = "upload_data"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 健康檢查端點
@app.get("/health", response_model=HealthResponse, tags=["系統"])
async def health_check():
    return {"status": "healthy"}

# API 端點上傳和處理 PDF
@app.post("/api/process-pdf", response_model=SentenceResponse, 
          responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
          tags=["PDF 處理"])
async def process_pdf(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    try:
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="只接受 PDF 文件")
        
        # 保存上傳的文件
        file_id = str(uuid.uuid4())
        file_path = os.path.join(UPLOAD_DIR, f"{file_id}.pdf")
        
        # 寫入文件
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())
        
        # 同步處理 PDF
        processor = PDFProcessor()
        result = await processor.process_pdf(file_path)
        
        # 清理臨時文件
        if os.path.exists(file_path):
            os.remove(file_path)
            
        return {"sentences": result}
        
    except Exception as e:
        logger.error(f"處理 PDF 時發生錯誤: {str(e)}")
        raise HTTPException(status_code=500, detail=f"處理 PDF 時發生錯誤: {str(e)}")

# WebSocket 端點
@app.websocket("/ws/process-pdf/{client_id}")
async def websocket_process_pdf(websocket: WebSocket, client_id: str):
    await websocket.accept()
    active_connections[client_id] = websocket
    processing_statuses[client_id] = ProcessingStatus(client_id=client_id)
    
    try:
        # 接收 PDF 文件
        pdf_data = await websocket.receive_bytes()
        
        # 保存 PDF 文件
        file_id = str(uuid.uuid4())
        file_path = os.path.join(UPLOAD_DIR, f"{file_id}.pdf")
        
        with open(file_path, "wb") as f:
            f.write(pdf_data)
        
        # 發送確認接收訊息
        await websocket.send_json({
            "status": "received",
            "message": "PDF 文件已接收，開始處理",
            "progress": 0.0
        })
        
        # 初始化 PDF 處理器
        processor = PDFProcessor()
        
        # 設置狀態回調
        async def status_callback(status: str, progress: float, message: str):
            await websocket.send_json({
                "status": status,
                "progress": progress,
                "message": message
            })
        
        # 進行處理
        processing_statuses[client_id].set_callback(status_callback)
        result = await processor.process_pdf(
            file_path, 
            status_tracker=processing_statuses[client_id]
        )
        
        # 發送完成結果
        await websocket.send_json({
            "status": "completed",
            "progress": 1.0,
            "sentences": result
        })
        
        # 清理臨時文件
        if os.path.exists(file_path):
            os.remove(file_path)
            
    except Exception as e:
        logger.error(f"WebSocket 處理時發生錯誤: {str(e)}")
        try:
            await websocket.send_json({
                "status": "error",
                "error": f"處理 PDF 時發生錯誤: {str(e)}"
            })
        except:
            pass
    finally:
        # 清理連接
        if client_id in active_connections:
            del active_connections[client_id]
        if client_id in processing_statuses:
            del processing_statuses[client_id] 