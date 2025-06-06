from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List
import asyncio
from datetime import datetime
import os

from ..core.database import get_db
from ..services.file_service import file_service
from ..services.db_service import db_service
from ..services.grobid_service import grobid_service
from ..services.n8n_service import n8n_service
from ..services.split_sentences_service import split_sentences_service
from ..models.paper import PaperCreate, PaperResponse, ProcessingQueueCreate, SectionCreate, SentenceCreate
from ..core.logging import get_logger

logger = get_logger("upload")

router = APIRouter(prefix="/upload", tags=["upload"])

# 處理管道函數
async def process_paper_pipeline(paper_id: str):
    """論文處理的完整流程"""
    logger.info(f"開始處理論文: {paper_id}")
    
    # 創建新的資料庫會話
    from ..core.database import AsyncSessionLocal
    
    async with AsyncSessionLocal() as db:
        try:
            # 階段1: 更新狀態為處理中
            logger.info(f"更新論文 {paper_id} 狀態為處理中")
            await db_service.update_paper_status(db, paper_id, "processing")
            
            # 獲取論文資訊
            paper = await db_service.get_paper_by_id(db, paper_id)
            if not paper:
                raise ValueError(f"論文不存在: {paper_id}")
            
            # 構建檔案路徑 (使用設定中的暫存目錄)
            from ..core.config import settings
            file_path = os.path.join(settings.temp_files_dir, paper.file_name)
            if not os.path.exists(file_path):
                raise ValueError(f"檔案實體不存在: {file_path}")
            
            # 階段2: Grobid TEI處理
            logger.info(f"開始Grobid處理: {paper_id}")
            tei_result = await grobid_service.process_paper_complete(file_path)
            
            if not tei_result.get("processing_success"):
                error_msg = tei_result.get('error_message', '未知的 Grobid 處理錯誤')
                raise Exception(f"Grobid 處理失敗: {error_msg}")
            
            # 階段3: 儲存TEI XML和元數據
            logger.info(f"儲存TEI資料: {paper_id}")
            await db_service.update_paper_status(
                db, paper_id, "processing"
            )
            
            # 階段4: 解析並儲存章節
            sections = tei_result.get('sections', [])
            section_ids = []
            
            for i, section in enumerate(sections):
                section_data = SectionCreate(
                    paper_id=paper_id,
                    section_type=section.get("type", "unknown"),
                    page_num=section.get("page_start", 1),
                    content=section.get("content", ""),
                    section_order=i,
                    word_count=len(section.get("content", "").split())
                )
                section_id = await db_service.create_paper_section(db, section_data)
                section_ids.append((section_id, section.get("content", "")))
            
            # 階段5: 句子切分與分析
            logger.info(f"開始句子分析: {paper_id}")
            await db_service.update_paper_status(
                db, paper_id, "processing"
            )
            
            total_sentences = 0
            processed_sentences = 0
            
            for section_id, section_content in section_ids:
                if len(section_content.strip()) < 10:  # 跳過太短的章節
                    continue
                
                # 句子切分
                try:
                    # 準備章節數據為 split_sentences_service 需要的格式
                    section_data = [{
                        "section_type": "unknown",  # 這裡可以根據實際情況設定
                        "content": section_content,
                        "page_num": 1  # 預設頁碼
                    }]
                    
                    # 調用句子切分服務
                    sentence_results = await split_sentences_service.process_sections_to_sentences(section_data)
                    sentences = [result["text"] for result in sentence_results]
                    total_sentences += len(sentences)
                    
                    # 批次處理句子 (每次處理5句，避免API過載)
                    for i in range(0, len(sentences), 5):
                        batch = sentences[i:i+5]
                        
                        # 處理這批句子的OD/CD分析
                        for j, sentence in enumerate(batch):
                            try:
                                # 調用N8N API進行OD/CD分析
                                analysis = await n8n_service.detect_od_cd(sentence)
                                
                                # 儲存句子
                                sentence_data = SentenceCreate(
                                    paper_id=paper_id,
                                    section_id=section_id,
                                    sentence_text=sentence,
                                    sentence_order=i + j,
                                    defining_type=analysis.get("defining_type", "UNKNOWN").upper(),
                                    analysis_reason=analysis.get("reason", ""),
                                    word_count=len(sentence.split())
                                )
                                await db_service.create_sentence(db, sentence_data)
                                processed_sentences += 1
                                
                            except Exception as e:
                                logger.warning(f"句子分析失敗: {e}")
                                # 儲存未分析的句子
                                sentence_data = SentenceCreate(
                                    paper_id=paper_id,
                                    section_id=section_id,
                                    sentence_text=sentence,
                                    sentence_order=i + j,
                                    defining_type="UNKNOWN",
                                    analysis_reason=f"分析失敗: {str(e)}",
                                    word_count=len(sentence.split())
                                )
                                await db_service.create_sentence(db, sentence_data)
                                processed_sentences += 1
                        
                        # 更新進度
                        progress = f"已處理 {processed_sentences}/{total_sentences} 個句子"
                        logger.info(f"進度更新: {paper_id} - {progress}")
                        
                        # 避免過快請求，短暫延遲
                        await asyncio.sleep(0.5)
                
                except Exception as e:
                    logger.error(f"章節處理失敗: {e}")
                    continue
            
            # 階段6: 標記完成
            logger.info(f"處理完成: {paper_id}, 共處理 {processed_sentences} 個句子")
            await db_service.update_paper_status(db, paper_id, "completed")
            
            # 階段7: 清理臨時檔案
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"已刪除臨時檔案: {file_path}")
            except Exception as e:
                logger.warning(f"刪除臨時檔案失敗: {e}")
            
        except Exception as e:
            logger.error(f"處理失敗: {paper_id}, 錯誤: {e}")
            await db_service.update_paper_status(db, paper_id, "error", str(e))

# ===== 檔案上傳 =====

@router.post("/", response_model=Dict[str, Any])
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    上傳PDF檔案
    """
    try:
        # 1. 驗證檔案
        is_valid, error_message = await file_service.validate_file(file)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message
            )
        
        # 2. 計算檔案雜湊值
        file_hash = await file_service.calculate_file_hash(file)
        
        # 3. 檢查是否為重複檔案
        existing_paper = await db_service.get_paper_by_hash(db, file_hash)
        if existing_paper:
            return {
                "success": True,
                "duplicate": True,
                "message": "檔案已存在",
                "paper_id": str(existing_paper.id),
                "existing_filename": existing_paper.file_name,
                "original_filename": file.filename
            }
        
        # 4. 儲存暫存檔案
        file_path, internal_filename = await file_service.save_temp_file(file, file_hash)
        file_size = file_service.get_file_size(file_path)
        
        # 5. 建立論文記錄
        paper_data = PaperCreate(
            file_name=internal_filename,
            original_filename=file.filename,
            file_hash=file_hash,
            file_size=file_size
        )
        
        paper_id = await db_service.create_paper(db, paper_data)
        
        # 6. 加入處理佇列
        queue_data = ProcessingQueueCreate(
            paper_id=paper_id,
            processing_stage="grobid_processing",
            priority=1
        )
        await db_service.add_to_queue(db, queue_data)
        
        # 7. 自動選取新上傳的論文
        await db_service.mark_paper_selected(db, paper_id)
        
        # 8. 開始背景處理
        background_tasks.add_task(process_paper_pipeline, paper_id)
        
        return {
            "success": True,
            "duplicate": False,
            "message": "檔案上傳成功",
            "paper_id": paper_id,
            "filename": internal_filename,
            "original_filename": file.filename,
            "file_size": file_size,
            "file_hash": file_hash
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"檔案上傳失敗: {str(e)}"
        )

@router.post("/batch", response_model=Dict[str, Any])
async def upload_multiple_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    批次上傳多個PDF檔案
    """
    try:
        results = []
        total_files = len(files)
        
        if total_files > 10:  # 限制批次上傳數量
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="批次上傳最多支援10個檔案"
            )
        
        for i, file in enumerate(files):
            try:
                # 1. 驗證檔案
                is_valid, error_message = await file_service.validate_file(file)
                if not is_valid:
                    results.append({
                        "filename": file.filename,
                        "success": False,
                        "error": error_message
                    })
                    continue
                
                # 2. 計算檔案雜湊值
                file_hash = await file_service.calculate_file_hash(file)
                
                # 3. 檢查是否為重複檔案
                existing_paper = await db_service.get_paper_by_hash(db, file_hash)
                if existing_paper:
                    results.append({
                        "filename": file.filename,
                        "success": True,
                        "duplicate": True,
                        "paper_id": str(existing_paper.id),
                        "message": "檔案已存在"
                    })
                    continue
                
                # 4. 儲存暫存檔案
                file_path, internal_filename = await file_service.save_temp_file(file, file_hash)
                file_size = file_service.get_file_size(file_path)
                
                # 5. 建立論文記錄
                paper_data = PaperCreate(
                    file_name=internal_filename,
                    original_filename=file.filename,
                    file_hash=file_hash,
                    file_size=file_size
                )
                
                paper_id = await db_service.create_paper(db, paper_data)
                
                # 6. 加入處理佇列
                queue_data = ProcessingQueueCreate(
                    paper_id=paper_id,
                    processing_stage="grobid_processing",
                    priority=1
                )
                await db_service.add_to_queue(db, queue_data)
                
                # 7. 自動選取新上傳的論文
                await db_service.mark_paper_selected(db, paper_id)
                
                results.append({
                    "filename": file.filename,
                    "success": True,
                    "duplicate": False,
                    "paper_id": paper_id,
                    "internal_filename": internal_filename,
                    "file_size": file_size
                })
                
            except Exception as e:
                results.append({
                    "filename": file.filename,
                    "success": False,
                    "error": str(e)
                })
        
        # 統計結果
        successful_uploads = sum(1 for r in results if r["success"] and not r.get("duplicate", False))
        duplicates = sum(1 for r in results if r.get("duplicate", False))
        failures = sum(1 for r in results if not r["success"])
        
        return {
            "success": True,
            "total_files": total_files,
            "successful_uploads": successful_uploads,
            "duplicates": duplicates,
            "failures": failures,
            "results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批次上傳失敗: {str(e)}"
        )

# ===== 檔案管理 =====

@router.get("/info", response_model=Dict[str, Any])
async def get_upload_info():
    """取得上傳相關資訊"""
    try:
        directory_info = file_service.get_temp_directory_info()
        
        return {
            "success": True,
            "upload_limits": {
                "max_file_size_mb": file_service.max_file_size // (1024 * 1024),
                "allowed_formats": ["PDF"],
                "batch_upload_limit": 10
            },
            "directory_info": directory_info
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"取得上傳資訊失敗: {str(e)}"
        )

@router.post("/cleanup", response_model=Dict[str, Any])
async def cleanup_files(
    max_age_hours: int = 24,
    db: AsyncSession = Depends(get_db)
):
    """清理暫存檔案"""
    try:
        # 1. 清理過期檔案
        cleanup_result = await file_service.cleanup_temp_files(max_age_hours)
        
        # 2. 清理孤立檔案
        # 取得資料庫中所有有效的檔案雜湊
        papers = await db_service.get_all_papers(db)
        valid_hashes = [paper.file_hash for paper in papers if paper.file_hash]
        
        orphan_cleanup_result = await file_service.cleanup_orphaned_files(valid_hashes)
        
        return {
            "success": True,
            "expired_files_cleanup": cleanup_result,
            "orphaned_files_cleanup": orphan_cleanup_result,
            "total_files_deleted": cleanup_result.get("deleted_count", 0) + orphan_cleanup_result.get("deleted_count", 0),
            "total_space_freed_mb": cleanup_result.get("total_size_freed_mb", 0) + orphan_cleanup_result.get("total_size_freed_mb", 0)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"檔案清理失敗: {str(e)}"
        )

@router.delete("/{paper_id}")
async def delete_uploaded_file(
    paper_id: str,
    db: AsyncSession = Depends(get_db)
):
    """刪除已上傳的檔案和相關記錄"""
    try:
        # 1. 檢查論文是否存在
        paper = await db_service.get_paper_by_id(db, paper_id)
        if not paper:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="論文不存在"
            )
        
        # 2. 找到對應的檔案路徑
        file_hash = paper.file_hash
        existing_file_path = await file_service.check_duplicate_file(file_hash)
        
        # 3. 刪除實體檔案
        if existing_file_path:
            await file_service.delete_file(existing_file_path)
        
        # 4. 這裡之後會實作完整的資料庫記錄刪除
        # await db_service.delete_paper(db, paper_id)
        
        return {
            "success": True,
            "message": f"檔案 {paper.original_filename} 已刪除",
            "paper_id": paper_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"刪除檔案失敗: {str(e)}"
        ) 