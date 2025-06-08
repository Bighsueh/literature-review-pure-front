"""
檔案處理流水線服務
整合Grobid,N8N API和資料庫服務的完整處理流程
"""

import asyncio
import time
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import os

from ..core.config import settings
from ..core.logging import get_logger
from .queue_service import queue_service, QueueTask, TaskStatus, TaskPriority, TaskProgress
from .file_service import file_service
from .grobid_service import grobid_service
from .n8n_service import n8n_service
from .db_service import db_service
from .split_sentences_service import split_sentences_service
from sqlalchemy.dialects.postgresql import insert as pg_insert
from ..database.connection import db_manager

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
        options: Dict[str, Any] = None
    ) -> str:
        """
        開始檔案處理流程
        
        Args:
            file_id: 檔案ID
            user_id: 使用者ID
            priority: 任務優先序
            options: 處理選項
            
        Returns:
            任務ID
        """
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
        """檔案處理主流程"""
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
            paper = await db_service.get_paper_by_id(db, file_id)
            
            if not paper:
                raise ValueError(f"檔案不存在: {file_id}")
            
            # 檢查論文狀態
            if paper.processing_status == "error":
                raise ValueError(f"檔案狀態為錯誤: {paper.error_message}")
            
            # 構建檔案路徑（假設檔案存儲在暫存目錄中）
            file_path = os.path.join(settings.temp_files_dir, paper.file_name)
            
            if not os.path.exists(file_path):
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
            section_analysis = {
                "section_id": section.get("section_id", ""),
                "title": section.get("title", ""),
                "content": section.get("content", ""),
                "section_type": section.get("section_type", "other"),
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
        sentence_id = 1
        
        for section in sections_analysis:
            section_id = section["section_id"]
            section_title = section["title"]
            
            for sentence_text in section["sentences"]:
                if len(sentence_text.strip()) > 10:  # 過濾太短的句子
                    sentences_data.append({
                        "sentence_id": f"sent_{sentence_id:06d}",
                        "text": sentence_text.strip(),
                        "section_id": section_id,
                        "section_title": section_title,
                        "section_type": section["section_type"],
                        "word_count": len(sentence_text.split()),
                        "position_in_section": len([s for s in sentences_data if s.get("section_id") == section_id])
                    })
                    sentence_id += 1
        
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
        async with db_manager.async_session_maker() as session:
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
                        "page_num": section_data.get("page"),
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
            # 這裡可以清理 Grobid 產生的暫存檔案
            # 目前 Grobid 服務自行管理暫存檔案，所以這裡暫時不做處理
            logger.debug("暫存檔案清理完成")
        except Exception as e:
            logger.warning(f"暫存檔案清理失敗: {e}")
    
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

# 建立服務實例
processing_service = ProcessingService()
