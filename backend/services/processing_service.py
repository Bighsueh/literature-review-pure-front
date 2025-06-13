"""
檔案處理流水線服務
整合Grobid,N8N API和資料庫服務的完整處理流程
"""

import asyncio
import time
import json
import uuid
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import os
from sqlalchemy import select, and_, or_
from sqlalchemy.sql import func

from ..core.config import settings
from ..core.logging import get_logger
from ..services.grobid_service import grobid_service
from ..services.n8n_service import n8n_service
from ..services.split_sentences_service import split_sentences_service
from ..services.queue_service import queue_service, QueueTask, TaskPriority
from ..services.db_service import db_service
from ..core.database import get_db
from ..models.paper import Paper, PaperSection, Sentence
from sqlalchemy.dialects.postgresql import insert as pg_insert
from pathlib import Path

logger = get_logger("processing_service")

class ProcessingSteps:
    """處理步驟定義"""
    FILE_VALIDATION = "file_validation"
    GROBID_PROCESSING = "grobid_processing"
    SECTION_ANALYSIS = "section_analysis"
    SENTENCE_EXTRACTION = "sentence_extraction"
    OD_CD_DETECTION = "od_cd_detection"
    KEYWORD_EXTRACTION = "keyword_extraction"
    DATABASE_STORAGE = "database_storage"
    CLEANUP = "cleanup"

class ProcessingService:
    """檔案處理流水線服務"""
    
    def __init__(self):
        self.total_processing_steps = 8
        
        # 註冊任務處理器
        self._register_handlers()
        
        logger.info("檔案處理服務初始化完成")
    
    def _register_handlers(self):
        """註冊任務處理器到佇列服務"""
        queue_service.register_handler("file_processing", self._process_file)
        queue_service.register_handler("batch_sentence_analysis", self._batch_sentence_analysis)
        queue_service.register_handler("section_reprocessing", self._reprocess_sections)
        
        logger.info("任務處理器已註冊")
    
    # ===== 主要處理流程 =====
    
    async def process_file(
        self,
        file_id: str,
        user_id: str = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        options: Dict[str, Any] = None,
        session: Optional[AsyncSession] = None  # 新增可選的會話參數
    ) -> str:
        """
        開始檔案處理流程
        
        Args:
            file_id: 檔案ID
            user_id: 使用者ID
            priority: 任務優先序
            options: 處理選項
            session: 可選的資料庫會話，如果提供則會在創建任務前確保提交
            
        Returns:
            任務ID
        """
        # 如果有會話傳入，確保在創建任務前提交所有變更
        if session:
            if session.dirty or session.new or session.deleted:
                await session.commit()
                logger.debug("在創建處理任務前已提交會話變更")
        
        processing_options = {
            "extract_keywords": True,
            "detect_od_cd": True,
            "analyze_sections": True,
            "max_sentences_per_batch": 50,
            **(options or {})
        }
        
        task_data = {
            "file_id": file_id,
            "options": processing_options
        }
        
        task_id = await queue_service.add_task(
            task_type="file_processing",
            data=task_data,
            priority=priority,
            user_id=user_id,
            file_id=file_id,
            timeout_seconds=1800  # 30分鐘超時
        )
        
        logger.info(f"檔案處理任務已創建: {task_id} (檔案: {file_id})")
        return task_id
    
    async def _process_file(self, task: QueueTask) -> Dict[str, Any]:
        """
        檔案處理主流程 (可恢復)
        協調各個處理步驟，並允許從失敗點恢復
        """
        file_id = task.data["file_id"]
        options = task.data["options"]
        logger.info(f"開始處理檔案 (可恢復流程): {file_id}")

        from ..core.database import AsyncSessionLocal
        session = AsyncSessionLocal()
        try:
            # 獲取最新的論文狀態
            paper = await db_service.get_paper_by_id(session, file_id)
            if not paper:
                raise ValueError(f"處理開始時找不到論文記錄: {file_id}")

            # 步驟 1: Grobid TEI 解析
            if not paper.grobid_processed:
                await queue_service.update_progress(task.task_id, step_name="Grobid TEI 解析")
                file_info = await self._validate_file(file_id)
                grobid_result = await self._process_with_grobid(file_info)
                
                # 增量儲存 Grobid 結果
                await db_service.update_paper_grobid_results(
                    session,
                    paper_id=file_id,
                    grobid_result=grobid_result,
                    status="processing"
                )
                await session.commit()
                paper = await db_service.get_paper_by_id(session, file_id)
                logger.info(f"[進度] Grobid 處理完成並已儲存: {file_id}")
            
            # 步驟 2: 章節與句子提取
            if not paper.sentences_processed:
                await queue_service.update_progress(task.task_id, step_name="章節與句子提取")
                grobid_xml = paper.tei_xml
                if not grobid_xml:
                    raise ValueError(f"無法從資料庫獲取 TEI XML: {file_id}")
                
                # 使用 grobid_service 解析 XML 以獲取章節
                # 傳遞 PDF 路徑以進行頁碼分析
                pdf_path = f"./temp_files/{paper.file_name}"
                sections = await grobid_service.parse_sections_from_xml(grobid_xml, pdf_path)
                if not sections:
                    raise ValueError(f"從 TEI XML 解析章節失敗: {file_id}")
                
                logger.info(f"從 TEI XML 解析出 {len(sections)} 個章節 - paper_id: {file_id}")
                grobid_result_mock = {"sections": sections}

                sections_analysis = await self._analyze_sections(grobid_result_mock, options)
                if not sections_analysis:
                    raise ValueError(f"章節分析失敗: {file_id}")
                    
                sentences_data = await self._extract_sentences(sections_analysis)
                if not sentences_data:
                    raise ValueError(f"句子提取失敗: {file_id}")
                
                logger.info(f"準備儲存 {len(sections_analysis)} 個章節和 {len(sentences_data)} 個句子 - paper_id: {file_id}")
                
                # 增量儲存章節與句子 - 這裡會自動提交和驗證
                await db_service.save_sections_and_sentences(
                    session,
                    paper_id=file_id,
                    sections_analysis=sections_analysis,
                    sentences_data=sentences_data,
                )
                
                # 重新獲取論文狀態以確保更新
                await session.commit()
                paper = await db_service.get_paper_by_id(session, file_id)
                logger.info(f"[進度] 章節與句子提取完成並已儲存: {file_id}")
            else:
                # 步驟 2.5: 頁碼更新（可恢復流程中的額外步驟）
                await queue_service.update_progress(task.task_id, step_name="頁碼資訊更新")
                pdf_path = f"./temp_files/{paper.file_name}"
                
                # 檢查是否需要更新頁碼（如果所有章節的頁碼都是 NULL）
                existing_sections = await db_service.get_sections_for_paper(session, file_id)
                needs_page_update = any(section.page_num is None for section in existing_sections)
                
                if needs_page_update:
                    logger.info(f"檢測到章節缺少頁碼資訊，開始 PDF 分析更新: {file_id}")
                    page_update_success = await self._update_section_page_numbers(session, file_id, pdf_path)
                    if page_update_success:
                        logger.info(f"[進度] 頁碼資訊更新完成: {file_id}")
                    else:
                        logger.warning(f"頁碼資訊更新失敗，但不影響主流程: {file_id}")
                else:
                    logger.info(f"章節頁碼資訊已存在，跳過更新: {file_id}")
            
            # 步驟 3: OD/CD 檢測
            # 重新獲取 paper 對象以避免異步問題
            paper = await db_service.get_paper_by_id(session, file_id)
            if not paper.od_cd_processed and options.get("detect_od_cd", True):
                await queue_service.update_progress(task.task_id, step_name="OD/CD 檢測")
                
                # 驗證句子資料是否真的存在
                all_sentences = await db_service.get_sentences_for_paper(session, file_id)
                if not all_sentences:
                    raise ValueError(f"無法獲取句子資料進行 OD/CD 檢測: {file_id}")
                
                logger.info(f"開始 OD/CD 檢測，句子數量: {len(all_sentences)} - paper_id: {file_id}")
                
                od_cd_results = await self._detect_od_cd(all_sentences, {}) # grobid_result 在此不需要
                
                # 增量儲存 OD/CD 結果
                await db_service.save_od_cd_results(
                    session,
                    paper_id=file_id,
                    od_cd_results=od_cd_results
                )
                await session.commit()
                logger.info(f"[進度] OD/CD 檢測完成並已儲存: {file_id}")
            
            # 步驟 4: 最終驗證與處理
            await queue_service.update_progress(task.task_id, step_name="最終驗證")
            
            # 關鍵修復：在標記為完成前驗證所有資料真的存在
            final_verification = await self._verify_processing_completion(session, file_id)
            if not final_verification["success"]:
                error_msg = f"處理完成驗證失敗: {final_verification['error']}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            logger.info(f"處理完成驗證通過 - {final_verification['summary']}")
            
            # 步驟 5: 完成處理與清理
            await queue_service.update_progress(task.task_id, step_name="完成處理")
            
            # 更新最終狀態
            await db_service.update_paper_status(session, file_id, "completed")
            
            # 清理暫存檔案
            file_info = await self._validate_file(file_id) # 重新驗證以獲取路徑
            await self._cleanup_temp_files(file_info)

            logger.info(f"檔案處理完成: {file_id}")
            return {"status": "completed", "file_id": file_id, "verification": final_verification}

        except Exception as e:
            logger.error(f"檔案處理失敗: {file_id} - {e}", exc_info=True)
            # 在單獨的會話中更新錯誤狀態，以防主會話已回滾
            error_session = AsyncSessionLocal()
            try:
                await db_service.update_paper_status(error_session, file_id, "error", str(e))
                await error_session.commit()
            except Exception as update_error:
                logger.error(f"更新錯誤狀態失敗: {update_error}")
            finally:
                await error_session.close()
            raise
        finally:
            await session.close()
    
    async def _process_file_legacy(self, task: QueueTask) -> Dict[str, Any]:
        """檔案處理主流程 (舊版，單體式)"""
        file_id = task.data["file_id"]
        options = task.data["options"]
        
        logger.info(f"開始處理檔案: {file_id}")
        
        # 初始化進度
        await queue_service.update_progress(
            task.task_id,
            current_step=0,
            total_steps=self.total_processing_steps,
            step_name="開始處理",
            details={"file_id": file_id}
        )
        
        try:
            # 步驟 1: 檔案驗證
            await queue_service.update_progress(
                task.task_id,
                current_step=1,
                step_name="檔案驗證"
            )
            
            file_info = await self._validate_file(file_id)
            
            # 步驟 2: Grobid 處理
            await queue_service.update_progress(
                task.task_id,
                current_step=2,
                step_name="Grobid TEI 解析"
            )
            
            grobid_result = await self._process_with_grobid(file_info)
            
            # 步驟 3: 章節分析
            await queue_service.update_progress(
                task.task_id,
                current_step=3,
                step_name="章節分析"
            )
            
            sections_analysis = await self._analyze_sections(grobid_result, options)
            
            # 步驟 4: 句子提取
            await queue_service.update_progress(
                task.task_id,
                current_step=4,
                step_name="句子提取"
            )
            
            sentences_data = await self._extract_sentences(sections_analysis)
            
            # 步驟 5: OD/CD 檢測 (可選)
            od_cd_results = None
            if options.get("detect_od_cd", True):
                await queue_service.update_progress(
                    task.task_id,
                    current_step=5,
                    step_name="OD/CD 檢測"
                )
                
                od_cd_results = await self._detect_od_cd(sentences_data, grobid_result)
            
            # 步驟 6: 關鍵詞提取 (可選)
            keyword_results = None
            if options.get("extract_keywords", True):
                await queue_service.update_progress(
                    task.task_id,
                    current_step=6,
                    step_name="關鍵詞提取"
                )
                
                keyword_results = await self._extract_keywords(sections_analysis)
            
            # 步驟 7: 資料庫存儲
            await queue_service.update_progress(
                task.task_id,
                current_step=7,
                step_name="資料庫存儲"
            )
            
            storage_result = await self._store_results(
                paper_id=file_id,
                grobid_result=grobid_result,
                sections_analysis=sections_analysis,
                sentences_data=sentences_data,
                od_cd_results=od_cd_results,
                keyword_results=keyword_results
            )
            
            # 步驟 8: 清理
            await queue_service.update_progress(
                task.task_id,
                current_step=8,
                step_name="處理完成"
            )
            
            await self._cleanup_temp_files(file_info)
            
            # 編譯最終結果
            result = {
                "file_id": file_id,
                "processing_completed_at": datetime.now().isoformat(),
                "grobid_summary": {
                    "title": grobid_result.get("title"),
                    "authors": grobid_result.get("authors", []),
                    "sections_count": len(grobid_result.get("sections", [])),
                    "references_count": len(grobid_result.get("references", []))
                },
                "analysis_summary": {
                    "total_sentences": len(sentences_data),
                    "od_cd_detected": len([s for s in (od_cd_results or []) if s.get("is_od_cd")]) if od_cd_results else None,
                    "keywords_extracted": len(keyword_results or []),
                    "sections_processed": len(sections_analysis)
                },
                "storage_info": storage_result
            }
            
            logger.info(f"檔案處理完成: {file_id}")
            return result
            
        except Exception as e:
            logger.error(f"檔案處理失敗: {file_id} - {e}")
            raise
    
    # ===== 個別處理步驟 =====
    
    async def _validate_file(self, file_id: str) -> Dict[str, Any]:
        """檔案驗證"""
        # 直接從資料庫獲取檔案資訊
        from ..core.database import AsyncSessionLocal
        from sqlalchemy.ext.asyncio import AsyncSession
        
        # 創建一個新的資料庫會話來獲取檔案資訊
        async with AsyncSessionLocal() as db:
            try:
                paper = await db_service.get_paper_by_id(db, file_id)
                
                if not paper:
                    # 記錄詳細錯誤信息並檢查是否為重複任務
                    logger.error(f"檔案記錄不存在於資料庫: {file_id}")
                    logger.error(f"可能原因: 1) 記錄已被刪除 2) ID錯誤 3) 資料庫事務問題")
                    
                    # 停止相關的重複任務
                    await self._cleanup_failed_task(file_id)
                    raise ValueError(f"檔案記錄不存在於資料庫: {file_id}")
                
                # 檢查論文狀態
                if paper.processing_status == "error":
                    logger.warning(f"檔案狀態為錯誤，停止處理: {file_id} - {paper.error_message}")
                    await self._cleanup_failed_task(file_id)
                    raise ValueError(f"檔案狀態為錯誤: {paper.error_message}")
                
                # 構建檔案路徑（假設檔案存儲在暫存目錄中）
                file_path = os.path.join(settings.temp_files_dir, paper.file_name)
                
                if not os.path.exists(file_path):
                    logger.error(f"檔案實體不存在: {file_path}")
                    logger.error(f"Paper記錄: file_name={paper.file_name}, status={paper.processing_status}")
                    
                    # 列出 temp_files 目錄內容用於調試
                    try:
                        files = os.listdir(settings.temp_files_dir)
                        logger.error(f"temp_files 目錄內容 (前10個): {files[:10]}")
                    except Exception as e:
                        logger.error(f"無法列出 temp_files 目錄: {e}")
                    
                    # 更新資料庫狀態為錯誤
                    await db_service.update_paper_status(
                        db, file_id, "error", f"檔案實體不存在: {file_path}"
                    )
                    await self._cleanup_failed_task(file_id)
                    raise ValueError(f"檔案實體不存在: {file_path}")
                
                # 構建檔案資訊字典，與原 file_service 格式相容
                file_info = {
                    "file_id": file_id,
                    "file_path": file_path,
                    "filename": paper.file_name,
                    "original_filename": paper.original_filename,
                    "file_size": paper.file_size,
                    "status": "uploaded" if paper.processing_status in ["uploading", "uploaded"] else paper.processing_status,
                    "created_time": paper.created_at,
                    "modified_time": paper.upload_timestamp
                }
                
                logger.debug(f"檔案驗證通過: {file_id}")
                return file_info
                
            except ValueError:
                # 重新拋出我們的業務邏輯錯誤
                raise
            except Exception as e:
                logger.error(f"檔案驗證時發生未預期錯誤: {file_id} - {e}")
                await self._cleanup_failed_task(file_id)
                raise ValueError(f"檔案驗證失敗: {str(e)}")
    
    async def _cleanup_failed_task(self, file_id: str):
        """清理失敗的任務，防止無限重試"""
        try:
            # 1. 停止相關的重試任務
            logger.info(f"清理失敗任務: {file_id}")
            
            # 清理佇列中的失敗任務
            from .queue_service import queue_service
            await queue_service.cleanup_failed_tasks(file_id)
            
            # 2. 更新資料庫狀態（如果記錄存在）
            from ..core.database import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                try:
                    await db_service.update_paper_status(
                        db, file_id, "error", "處理失敗，任務已停止"
                    )
                    logger.info(f"已更新論文狀態為錯誤: {file_id}")
                except Exception as e:
                    logger.warning(f"無法更新論文狀態: {file_id} - {e}")
            
            # 3. 清理相關資源 (如果需要的話)
            # 例如：清理暫存檔案、停止相關服務等
            
        except Exception as e:
            logger.error(f"清理失敗任務時發生錯誤: {file_id} - {e}")
    
    async def _process_with_grobid(self, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """使用 Grobid 處理檔案"""
        file_path = file_info["file_path"]
        
        # 檢查 Grobid 服務健康狀態
        if not await grobid_service.health_check():
            raise Exception("Grobid 服務不可用")
        
        # 完整處理
        complete_result = await grobid_service.process_paper_complete(file_path)

        if not complete_result.get("processing_success"):
            error_msg = complete_result.get('error_message', '未知的 Grobid 處理錯誤')
            raise Exception(f"Grobid 處理失敗: {error_msg}")
        
        logger.info(f"Grobid 處理完成，提取到 {len(complete_result.get('sections', []))} 個章節")
        return complete_result
    
    async def _analyze_sections(
        self,
        grobid_result: Dict[str, Any],
        options: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """章節分析"""
        sections = grobid_result.get("sections", [])
        
        analyzed_sections = []
        
        for section in sections:
            # 如果原始的section_id不是UUID格式，生成新的UUID
            original_section_id = section.get("section_id", "")
            if original_section_id and len(original_section_id) < 32:  # 不是UUID格式
                section_id = str(uuid.uuid4())
            else:
                section_id = original_section_id or str(uuid.uuid4())
                
            section_analysis = {
                "section_id": section_id,
                "title": section.get("title", ""),
                "content": section.get("content", ""),
                "section_type": section.get("section_type", "other"),
                "page_num": section.get("page_num"),
                "word_count": section.get("word_count", 0),
                "order": section.get("order", 0),
                
                # 分析結果
                "sentences": [],
                "summary": "",
                "key_points": []
            }
            
            # 句子分割 (使用 Split Sentences 服務)
            content = section.get("content", "")
            if content.strip():
                # 為這個章節創建單個章節列表
                single_section = [{
                    "section_type": section.get("section_type", "other"),
                    "content": content,
                    "page_start": section.get("page_num", 1)
                }]
                
                # 調用 split_sentences 服務
                try:
                    processed_sentences = await split_sentences_service.process_sections_to_sentences(
                        single_section, 
                        language="mixed"
                    )
                    sentences = [s["text"] for s in processed_sentences]
                except Exception as e:
                    logger.warning(f"Split Sentences 服務調用失敗，使用備用方法: {e}")
                    sentences = self._split_sentences(content)
            else:
                sentences = []
            
            section_analysis["sentences"] = sentences
            
            # 生成摘要 (簡化版)
            if len(sentences) > 0:
                # 取前兩句作為摘要
                section_analysis["summary"] = " ".join(sentences[:2])
            
            analyzed_sections.append(section_analysis)
        
        logger.info(f"章節分析完成，處理 {len(analyzed_sections)} 個章節")
        return analyzed_sections
    
    async def _extract_sentences(self, sections_analysis: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """提取所有句子"""
        sentences_data = []
        
        for section in sections_analysis:
            section_id = section["section_id"]
            section_title = section["title"]
            
            for sentence_text in section["sentences"]:
                if len(sentence_text.strip()) > 10:  # 過濾太短的句子
                    sentences_data.append({
                        "sentence_id": str(uuid.uuid4()),
                        "text": sentence_text.strip(),
                        "section_id": section_id,
                        "section_title": section_title,
                        "section_type": section["section_type"],
                        "word_count": len(sentence_text.split()),
                        "position_in_section": len([s for s in sentences_data if s.get("section_id") == section_id])
                    })
        
        logger.info(f"句子提取完成，總共 {len(sentences_data)} 個句子")
        return sentences_data
    
    async def _detect_od_cd(
        self,
        sentences_data: List[Dict[str, Any]],
        grobid_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """OD/CD 檢測，帶有重試機制，確保單個失敗不影響整個批次"""
        logger.info(f"開始OD/CD檢測，句子總數: {len(sentences_data)}")
        
        # 使用Semaphore控制並發數
        semaphore = asyncio.Semaphore(n8n_service.max_concurrent_requests)
        
        async def detect_single_sentence_with_retry(idx: int, sentence_data: Dict[str, Any], max_retries: int = 3):
            """單個句子檢測，帶有重試機制"""
            sentence_text = sentence_data["text"]
            
            for attempt in range(max_retries):
                async with semaphore:
                    try:
                        logger.debug(f"檢測句子 {idx}，嘗試 {attempt + 1}/{max_retries}")
                        result = await n8n_service.detect_od_cd(
                            sentence=sentence_text,
                            cache_key=f"od_cd_{hash(sentence_text)}"
                        )
                        
                        # 成功獲得結果
                        if "error" not in result and "defining_type" in result:
                            defining_type = result.get("defining_type", "UNKNOWN").upper()
                            is_od_cd = defining_type in ["OD", "CD"]
                            
                            return {
                                **sentence_data,
                                "is_od_cd": is_od_cd,
                                "confidence": 1.0 if is_od_cd else 0.0,
                                "od_cd_type": defining_type,
                                "explanation": result.get("reason", ""),
                                "detection_status": "success",
                                "retry_count": attempt
                            }
                        else:
                            # API返回錯誤，但不重試，因為可能是業務邏輯問題
                            logger.warning(f"句子 {idx} N8N API返回錯誤: {result}")
                            break
                            
                    except Exception as e:
                        logger.warning(f"句子 {idx} 檢測失敗，嘗試 {attempt + 1}/{max_retries}: {e}")
                        
                        # 如果不是最後一次嘗試，等待後重試
                        if attempt < max_retries - 1:
                            await asyncio.sleep(1 * (attempt + 1))  # 遞增等待時間
                            continue
                        else:
                            # 最後一次嘗試也失敗了
                            logger.error(f"句子 {idx} 經過 {max_retries} 次嘗試後仍然失敗: {e}")
                            break
            
            # 三次嘗試都失敗，標記為錯誤
            return {
                **sentence_data,
                "is_od_cd": False,
                "confidence": 0.0,
                "od_cd_type": "ERROR",
                "explanation": f"API調用失敗，經過 {max_retries} 次重試",
                "detection_status": "error",
                "retry_count": max_retries
            }
        
        # 為每個句子創建檢測任務
        detection_tasks = []
        for idx, sentence_data in enumerate(sentences_data):
            task = detect_single_sentence_with_retry(idx, sentence_data)
            detection_tasks.append(task)
        
        logger.info(f"並發執行 {len(detection_tasks)} 個OD/CD檢測任務，最大並發數: {n8n_service.max_concurrent_requests}")
        
        # 並發執行所有檢測任務，使用return_exceptions=True確保單個失敗不影響其他
        detection_results = await asyncio.gather(*detection_tasks, return_exceptions=True)
        
        # 處理結果
        all_results = []
        successful_count = 0
        error_count = 0
        
        for idx, result in enumerate(detection_results):
            if isinstance(result, Exception):
                # 如果任務本身拋出異常（不太可能，因為我們已經處理了所有異常）
                logger.error(f"句子 {idx} 任務異常: {result}")
                sentence_data = sentences_data[idx]
                combined_result = {
                    **sentence_data,
                    "is_od_cd": False,
                    "confidence": 0.0,
                    "od_cd_type": "ERROR",
                    "explanation": f"任務執行異常: {str(result)}",
                    "detection_status": "error",
                    "retry_count": 3
                }
                error_count += 1
            else:
                combined_result = result
                if result.get("detection_status") == "success":
                    successful_count += 1
                elif result.get("detection_status") == "error":
                    error_count += 1
            
            all_results.append(combined_result)
        
        detected_count = sum(1 for r in all_results if r.get("is_od_cd"))
        
        logger.info(f"OD/CD 檢測完成:")
        logger.info(f"  - 總句子數: {len(all_results)}")
        logger.info(f"  - 成功檢測: {successful_count}")
        logger.info(f"  - 檢測失敗: {error_count}")
        logger.info(f"  - OD/CD句子: {detected_count}")
        
        return all_results
    
    async def _extract_keywords(self, sections_analysis: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """關鍵詞提取"""
        all_keywords = []
        
        for section in sections_analysis:
            content = section["content"]
            
            if len(content.strip()) > 50:  # 只處理有足夠內容的章節
                try:
                    result = await n8n_service.extract_keywords(
                        query=content,
                    )
                    
                    if "error" not in result and "keywords" in result:
                        section_keywords = {
                            "section_id": section["section_id"],
                            "section_title": section["title"],
                            "section_type": section["section_type"],
                            "keywords": result["keywords"],
                            "keyword_count": len(result["keywords"]),
                            "extraction_confidence": result.get("confidence", 0.0)
                        }
                        all_keywords.append(section_keywords)
                    else:
                        logger.warning(f"關鍵詞提取失敗: {section['section_id']} - {result.get('error', '未知錯誤')}")
                
                except Exception as e:
                    logger.error(f"關鍵詞提取異常: {section['section_id']} - {e}")
                
                # 避免 API 限流
                # await asyncio.sleep(0.3)  # ✅ 暫時註解掉延遲
        
        total_keywords = sum(len(k["keywords"]) for k in all_keywords)
        logger.info(f"關鍵詞提取完成，從 {len(all_keywords)} 個章節提取 {total_keywords} 個關鍵詞")
        
        return all_keywords
    
    async def _store_results(
        self,
        paper_id: str,
        grobid_result: Dict[str, Any],
        sections_analysis: List[Dict[str, Any]],
        sentences_data: List[Dict[str, Any]],
        od_cd_results: Optional[List[Dict[str, Any]]] = None,
        keyword_results: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """使用SQLAlchemy ORM將處理結果存儲到資料庫"""
        async with AsyncSessionLocal() as session:
            try:
                # 1. 更新Paper記錄
                paper_update_data = {
                    "processing_status": "completed",
                    "grobid_processed": True,
                    "sentences_processed": True,
                    "tei_xml": grobid_result.get("tei_xml"),
                    "tei_metadata": {
                        "title": grobid_result.get("title"),
                        "authors": grobid_result.get("authors", []),
                        "abstract": grobid_result.get("abstract"),
                    },
                    "processing_completed_at": datetime.now()
                }
                
                await session.execute(
                    update(Paper)
                    .where(Paper.id == paper_id)
                    .values(**paper_update_data)
                )

                # 2. 準備並批次插入章節 (PaperSection)
                sections_to_insert = []
                for section_data in sections_analysis:
                    sections_to_insert.append({
                        "id": section_data["section_id"],
                        "paper_id": paper_id,
                        "section_type": section_data["section_type"],
                        "page_num": section_data.get("page_num"),
                        "content": section_data["content"],
                        "section_order": section_data.get("order"),
                        "word_count": section_data.get("word_count"),
                    })

                if sections_to_insert:
                    stmt = pg_insert(PaperSection).values(sections_to_insert)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['id'],
                        set_={
                            "section_type": stmt.excluded.section_type,
                            "page_num": stmt.excluded.page_num,
                            "content": stmt.excluded.content,
                            "section_order": stmt.excluded.section_order,
                            "word_count": stmt.excluded.word_count,
                        }
                    )
                    await session.execute(stmt)

                # 3. 準備並批次插入句子 (Sentence)
                sentences_to_insert = []
                if od_cd_results:
                    for sentence_data in od_cd_results:
                        sentences_to_insert.append({
                            "id": sentence_data["sentence_id"],
                            "paper_id": paper_id,
                            "section_id": sentence_data["section_id"],
                            "sentence_text": sentence_data["sentence_text"],
                            "page_num": sentence_data.get("page"),
                            "sentence_order": sentence_data.get("order"),
                            "defining_type": sentence_data.get("is_od_cd", "UNKNOWN"),
                            "analysis_reason": sentence_data.get("reason"),
                            "word_count": len(sentence_data["sentence_text"].split()),
                            "confidence_score": sentence_data.get("confidence"),
                            "detection_status": sentence_data.get("detection_status", "completed"),
                            "error_message": sentence_data.get("error_message"),
                            "retry_count": sentence_data.get("retry_count", 0),
                            "explanation": sentence_data.get("explanation"),
                        })
                
                if sentences_to_insert:
                    stmt = pg_insert(Sentence).values(sentences_to_insert)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['id'],
                        set_={
                            "sentence_text": stmt.excluded.sentence_text,
                            "page_num": stmt.excluded.page_num,
                            "sentence_order": stmt.excluded.sentence_order,
                            "defining_type": stmt.excluded.defining_type,
                            "analysis_reason": stmt.excluded.analysis_reason,
                            "word_count": stmt.excluded.word_count,
                            "confidence_score": stmt.excluded.confidence_score,
                            "detection_status": stmt.excluded.detection_status,
                            "error_message": stmt.excluded.error_message,
                            "retry_count": stmt.excluded.retry_count,
                            "explanation": stmt.excluded.explanation,
                        }
                    )
                    await session.execute(stmt)

                await session.commit()
                
                storage_result = {
                    "stored_at": datetime.now().isoformat(),
                    "sections_stored": len(sections_to_insert),
                    "sentences_stored": len(sentences_to_insert),
                    "keywords_stored": 0 # 關鍵詞存儲邏輯待實現
                }
                
                logger.info(f"處理結果已存儲: {paper_id}")
                return storage_result

            except Exception as e:
                await session.rollback()
                logger.error(f"存儲處理結果失敗: {paper_id} - {e}", exc_info=True)
                # 更新Paper狀態為錯誤
                await session.execute(
                    update(Paper)
                    .where(Paper.id == paper_id)
                    .values(processing_status='error', error_message=f"Store results failed: {e}")
                )
                await session.commit()
                raise
    
    async def _cleanup_temp_files(self, file_info: Dict[str, Any]):
        """清理暫存檔案"""
        try:
            file_path = file_info.get("file_path")
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"暫存檔案已清理: {file_path}")
        except Exception as e:
            logger.warning(f"清理暫存檔案失敗: {e}")
    
    async def _verify_processing_completion(self, db: AsyncSession, paper_id: str) -> Dict[str, Any]:
        """驗證論文處理是否真正完成 - 關鍵的資料一致性檢查"""
        try:
            # 1. 檢查論文記錄
            paper = await db_service.get_paper_by_id(db, paper_id)
            if not paper:
                return {"success": False, "error": "論文記錄不存在"}
            
            # 2. 檢查 TEI XML
            if not paper.tei_xml or len(paper.tei_xml) < 1000:  # TEI XML 至少應該有基本結構
                return {"success": False, "error": "TEI XML 缺失或太短"}
            
            # 3. 檢查章節資料
            sections_query = select(func.count(PaperSection.id)).where(PaperSection.paper_id == paper_id)
            sections_count = await db.execute(sections_query)
            actual_sections = sections_count.scalar()
            
            if actual_sections == 0:
                return {"success": False, "error": "章節資料完全缺失"}
            
            # 4. 檢查句子資料
            sentences_query = select(func.count(Sentence.id)).where(Sentence.paper_id == paper_id)
            sentences_count = await db.execute(sentences_query)
            actual_sentences = sentences_count.scalar()
            
            if actual_sentences == 0:
                return {"success": False, "error": "句子資料完全缺失"}
            
            # 5. 檢查章節和句子的關聯性
            orphan_sentences_query = select(func.count(Sentence.id)).where(
                and_(
                    Sentence.paper_id == paper_id,
                    ~Sentence.section_id.in_(
                        select(PaperSection.id).where(PaperSection.paper_id == paper_id)
                    )
                )
            )
            orphan_sentences_count = await db.execute(orphan_sentences_query)
            orphan_sentences = orphan_sentences_count.scalar()
            
            if orphan_sentences > 0:
                return {"success": False, "error": f"發現 {orphan_sentences} 個孤立句子（沒有對應章節）"}
            
            # 6. 檢查處理狀態標記
            if not paper.grobid_processed:
                return {"success": False, "error": "Grobid 處理狀態未標記為完成"}
            
            if not paper.sentences_processed:
                return {"success": False, "error": "句子處理狀態未標記為完成"}
            
            # 7. 檢查章節內容質量
            empty_sections_query = select(func.count(PaperSection.id)).where(
                and_(
                    PaperSection.paper_id == paper_id,
                    or_(
                        PaperSection.content.is_(None),
                        func.length(PaperSection.content) < 10
                    )
                )
            )
            empty_sections_count = await db.execute(empty_sections_query)
            empty_sections = empty_sections_count.scalar()
            
            if empty_sections > actual_sections * 0.5:  # 如果超過50%的章節內容為空
                return {"success": False, "error": f"過多空白章節: {empty_sections}/{actual_sections}"}
            
            # 8. 檢查句子內容質量
            empty_sentences_query = select(func.count(Sentence.id)).where(
                and_(
                    Sentence.paper_id == paper_id,
                    or_(
                        Sentence.sentence_text.is_(None),
                        func.length(Sentence.sentence_text) < 5
                    )
                )
            )
            empty_sentences_count = await db.execute(empty_sentences_query)
            empty_sentences = empty_sentences_count.scalar()
            
            if empty_sentences > actual_sentences * 0.3:  # 如果超過30%的句子內容為空
                return {"success": False, "error": f"過多空白句子: {empty_sentences}/{actual_sentences}"}
            
            # 9. 構建成功摘要
            summary = {
                "paper_id": paper_id,
                "tei_xml_length": len(paper.tei_xml),
                "sections_count": actual_sections,
                "sentences_count": actual_sentences,
                "empty_sections": empty_sections,
                "empty_sentences": empty_sentences,
                "grobid_processed": paper.grobid_processed,
                "sentences_processed": paper.sentences_processed,
                "od_cd_processed": paper.od_cd_processed
            }
            
            return {
                "success": True, 
                "summary": f"驗證通過: {actual_sections} 章節, {actual_sentences} 句子",
                "details": summary
            }
            
        except Exception as e:
            logger.error(f"處理完成驗證時發生錯誤: {e}", exc_info=True)
            return {"success": False, "error": f"驗證過程發生錯誤: {str(e)}"}
    
    # ===== 批次處理功能 =====
    
    async def batch_process_files(
        self,
        file_ids: List[str],
        user_id: str = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        options: Dict[str, Any] = None
    ) -> List[str]:
        """批次處理多個檔案"""
        task_ids = []
        
        for file_id in file_ids:
            task_id = await self.process_file(
                file_id=file_id,
                user_id=user_id,
                priority=priority,
                options=options
            )
            task_ids.append(task_id)
        
        logger.info(f"批次處理任務已創建: {len(task_ids)} 個檔案")
        return task_ids
    
    async def _batch_sentence_analysis(self, task: QueueTask) -> Dict[str, Any]:
        """批次句子分析任務"""
        sentences = task.data["sentences"]
        analysis_type = task.data.get("analysis_type", "od_cd_detection")
        
        logger.info(f"開始批次句子分析: {len(sentences)} 個句子")
        
        if analysis_type == "od_cd_detection":
            # 修正：逐句處理而非批次傳遞
            sentence_results = []
            for sentence in sentences:
                try:
                    result = await n8n_service.detect_od_cd(
                        sentence=sentence,  # ✅ 正確的單句調用
                        cache_key=f"batch_analysis_{hash(sentence)}"
                    )
                    sentence_results.append({
                        "sentence": sentence,
                        "result": result
                    })
                except Exception as e:
                    logger.warning(f"批次分析單句失敗: {e}")
                    sentence_results.append({
                        "sentence": sentence,
                        "result": {"error": str(e)}
                    })
                
                # 控制API調用頻率
                # await asyncio.sleep(0.1)  # ✅ 暫時註解掉延遲
            
            return {
                "results": sentence_results,
                "total_sentences": len(sentences),
                "successful_detections": len([r for r in sentence_results if "error" not in r["result"]])
            }
        else:
            raise ValueError(f"不支援的分析類型: {analysis_type}")
        
        return result
    
    async def _reprocess_sections(self, task: QueueTask) -> Dict[str, Any]:
        """重新處理特定章節"""
        file_id = task.data["file_id"]
        section_ids = task.data["section_ids"]
        
        logger.info(f"重新處理章節: {file_id} - {section_ids}")
        
        # 實作章節重新處理邏輯
        # 這裡可以重新提取關鍵詞,重新分析內容等
        
        return {"reprocessed_sections": section_ids}
    
    # ===== 工具方法 =====
    
    def _split_sentences(self, text: str) -> List[str]:
        """簡單的句子分割"""
        import re
        
        # 使用正則表達式分割句子
        sentences = re.split(r'[.!?]+', text)
        
        # 清理和過濾
        clean_sentences = []
        for sentence in sentences:
            clean_sentence = sentence.strip()
            if len(clean_sentence) > 10:  # 過濾太短的句子
                clean_sentences.append(clean_sentence)
        
        return clean_sentences
    
    # ===== 狀態查詢 =====
    
    async def get_processing_status(self, file_id: str) -> Optional[Dict[str, Any]]:
        """獲取檔案處理狀態"""
        # 查找與檔案相關的任務
        all_tasks = []
        
        # 檢查佇列中的任務
        queue_status = await queue_service.get_queue_status()
        
        # 從資料庫查詢任務
        try:
            cursor = await db_service.get_connection()
            result = await cursor.execute(
                """SELECT task_data FROM queue_tasks 
                   WHERE JSON_EXTRACT(task_data, '$.file_id') = ?
                   ORDER BY JSON_EXTRACT(task_data, '$.created_at') DESC
                   LIMIT 1""",
                (file_id,)
            )
            
            row = await result.fetchone()
            if row:
                task_data = json.loads(row[0])
                task = queue_service.QueueTask.from_dict(task_data)
                
                return {
                    "file_id": file_id,
                    "task_id": task.task_id,
                    "status": task.status.value,
                    "progress": task.progress.to_dict() if hasattr(task.progress, 'to_dict') else asdict(task.progress),
                    "created_at": task.created_at.isoformat(),
                    "started_at": task.started_at.isoformat() if task.started_at else None,
                    "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                    "error_message": task.error_message,
                    "result_summary": task.result
                }
        
        except Exception as e:
            logger.error(f"查詢處理狀態失敗: {e}")
        
        return None

    async def _update_section_page_numbers(self, session: AsyncSession, paper_id: str, pdf_path: str) -> bool:
        """
        更新現有章節的頁碼資訊
        
        Args:
            session: 資料庫會話
            paper_id: 論文ID
            pdf_path: PDF 檔案路徑
            
        Returns:
            是否成功更新
        """
        try:
            logger.info(f"開始更新章節頁碼資訊: {paper_id}")
            
            # 檢查 PDF 檔案是否存在
            if not Path(pdf_path).exists():
                logger.warning(f"PDF 檔案不存在，跳過頁碼更新: {pdf_path}")
                return False
            
            # 獲取現有章節
            existing_sections = await db_service.get_sections_for_paper(session, paper_id)
            if not existing_sections:
                logger.warning(f"沒有找到現有章節: {paper_id}")
                return False
            
            logger.info(f"找到 {len(existing_sections)} 個現有章節，開始 PDF 分析")
            
            # 進行 PDF 分析
            from .pdf_analyzer import pdf_analyzer
            pdf_analysis = await pdf_analyzer.analyze_pdf(pdf_path)
            
            if not pdf_analysis or not pdf_analysis.get('text_blocks'):
                logger.warning(f"PDF 分析失敗或沒有文本塊: {paper_id}")
                return False
            
            logger.info(f"PDF 分析完成，共 {pdf_analysis['total_pages']} 頁，{len(pdf_analysis['text_blocks'])} 個文本塊")
            
            # 更新每個章節的頁碼
            updated_count = 0
            for i, section in enumerate(existing_sections):
                try:
                    # 使用 PDF 分析來確定頁碼
                    page_num = await self._determine_page_number_for_section(
                        section, i, len(existing_sections), pdf_analysis
                    )
                    
                    if page_num and page_num != section.page_num:
                        # 更新資料庫中的頁碼
                        await db_service.update_section_page_number(session, section.id, page_num)
                        updated_count += 1
                        logger.info(f"更新章節 {i+1} 頁碼: {section.page_num} -> {page_num}")
                    
                except Exception as e:
                    logger.error(f"更新章節 {i+1} 頁碼失敗: {e}")
                    continue
            
            await session.commit()
            logger.info(f"頁碼更新完成: {paper_id}, 更新了 {updated_count} 個章節")
            return updated_count > 0
            
        except Exception as e:
            logger.error(f"頁碼更新過程失敗: {paper_id} - {e}", exc_info=True)
            await session.rollback()
            return False
    
    async def _determine_page_number_for_section(
        self, 
        section: Any, 
        section_index: int, 
        total_sections: int, 
        pdf_analysis: Dict[str, Any]
    ) -> Optional[int]:
        """
        為單個章節確定頁碼
        
        Args:
            section: 章節對象
            section_index: 章節索引
            total_sections: 總章節數
            pdf_analysis: PDF 分析結果
            
        Returns:
            頁碼
        """
        try:
            from .pdf_analyzer import pdf_analyzer
            
            # 方法1: 通過內容匹配
            if hasattr(section, 'content') and section.content:
                content_sample = section.content[:100] if len(section.content) > 100 else section.content
                content_page = pdf_analyzer.find_text_page(content_sample, pdf_analysis['text_blocks'])
                if content_page:
                    logger.debug(f"章節 {section_index+1} 通過內容匹配獲得頁碼: {content_page}")
                    return content_page
            
            # 方法2: 基於 PDF 總頁數的智能估算
            if pdf_analysis.get('total_pages'):
                estimated_page = pdf_analyzer.estimate_page_from_position(
                    section_index, total_sections, pdf_analysis['total_pages']
                )
                logger.debug(f"章節 {section_index+1} 基於位置估算頁碼: {estimated_page}")
                return estimated_page
            
            # 方法3: 簡單估算（備用方案）
            estimated_page = max(1, (section_index // 2) + 1)
            logger.debug(f"章節 {section_index+1} 使用簡單估算頁碼: {estimated_page}")
            return estimated_page
            
        except Exception as e:
            logger.error(f"確定章節頁碼失敗: {e}")
            return max(1, (section_index // 2) + 1)  # 備用方案

# 建立服務實例
processing_service = ProcessingService()
