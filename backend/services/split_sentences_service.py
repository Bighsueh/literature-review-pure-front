"""
Split Sentences 服務客戶端
用於調用 TEI 句子切分 API
"""

import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger("split_sentences_service")

class SplitSentencesService:
    """Split Sentences 服務客戶端"""
    
    def __init__(self):
        self.base_url = settings.split_sentences_url
        self.timeout = aiohttp.ClientTimeout(total=300)  # 5分鐘超時
        self.max_retries = 3
        self.retry_delay = 2  # 秒
        
        logger.info(f"Split Sentences 服務初始化完成，URL: {self.base_url}")
    
    async def health_check(self) -> bool:
        """檢查 Split Sentences 服務健康狀態"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(f"{self.base_url}/health") as response:
                    if response.status == 200:
                        logger.info("Split Sentences 服務健康檢查通過")
                        return True
                    else:
                        logger.warning(f"Split Sentences 服務健康檢查失敗，狀態碼: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"Split Sentences 服務健康檢查失敗: {e}")
            return False
    
    async def split_tei_sections(
        self, 
        sections: List[Dict[str, Any]], 
        language: str = "mixed"
    ) -> Dict[str, Any]:
        """
        處理 TEI 章節，將每個章節的內容切分為句子
        
        Args:
            sections: TEI 章節列表，每個章節包含:
                - section_type: 章節類型
                - content: 章節文本內容
                - page_start: 起始頁碼
                - page_end: 結束頁碼
            language: 文本語言設定 (zh, en, mixed)
            
        Returns:
            Dict包含:
                - sentences: 處理後的句子列表
                - processing_stats: 處理統計資訊
        """
        try:
            logger.info(f"開始處理 {len(sections)} 個 TEI 章節")
            
            # 準備請求數據
            request_data = {
                "sections": [
                    {
                        "section_type": section.get("section_type", "other"),
                        "content": section.get("content", ""),
                        "page_start": section.get("page_start") or section.get("page_num"),
                        "page_end": section.get("page_end") or section.get("page_num")
                    }
                    for section in sections
                ],
                "language": language
            }
            
            # 嘗試多次重試
            for attempt in range(self.max_retries):
                try:
                    result = await self._call_split_api(request_data)
                    if result and "sentences" in result:
                        logger.info(f"TEI 句子切分完成，生成 {len(result['sentences'])} 個句子")
                        return result
                except Exception as e:
                    logger.warning(f"TEI 句子切分嘗試 {attempt + 1} 失敗: {e}")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay)
                    else:
                        raise
            
            return {"sentences": [], "processing_stats": {"error": "處理失敗"}}
            
        except Exception as e:
            logger.error(f"TEI 句子切分失敗: {e}")
            raise
    
    async def _call_split_api(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """實際調用 Split Sentences API"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                url = f"{self.base_url}/api/split-sentences"
                
                async with session.post(url, json=request_data) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.debug(f"成功獲得句子切分結果，句子數: {len(result.get('sentences', []))}")
                        return result
                    else:
                        error_text = await response.text()
                        logger.error(f"Split Sentences API 調用失敗，狀態碼: {response.status}, 錯誤: {error_text}")
                        return {"error": f"API調用失敗: {response.status}"}
                        
        except asyncio.TimeoutError:
            logger.error("Split Sentences API 調用超時")
            return {"error": "API調用超時"}
        except Exception as e:
            logger.error(f"Split Sentences API 調用異常: {e}")
            raise
    
    async def process_sections_to_sentences(
        self, 
        sections: List[Dict[str, Any]],
        language: str = "mixed"
    ) -> List[Dict[str, Any]]:
        """
        將章節處理為標準化的句子列表，便於後續 OD/CD 分析
        
        Args:
            sections: 章節列表
            language: 語言設定
            
        Returns:
            標準化的句子列表，每個句子包含:
                - text: 句子文本
                - section_type: 所屬章節類型
                - sentence_order: 句子在章節中的順序
                - page_num: 頁碼
                - confidence: 切分信心度
        """
        try:
            # 調用 TEI 句子切分
            split_result = await self.split_tei_sections(sections, language)
            
            if "error" in split_result:
                logger.error(f"章節句子切分失敗: {split_result['error']}")
                return []
            
            sentences = split_result.get("sentences", [])
            
            # 轉換為標準格式
            standardized_sentences = []
            global_sentence_id = 1
            
            for sentence in sentences:
                standardized_sentence = {
                    "sentence_id": f"sent_{global_sentence_id:06d}",
                    "text": sentence.get("text", ""),
                    "section_type": sentence.get("section_type", "other"),
                    "sentence_order": sentence.get("sentence_order", 0),
                    "page_num": sentence.get("page_num"),
                    "confidence": sentence.get("confidence", 1.0),
                    "word_count": len(sentence.get("text", "").split())
                }
                
                # 過濾太短的句子
                if len(standardized_sentence["text"].strip()) > 10:
                    standardized_sentences.append(standardized_sentence)
                    global_sentence_id += 1
            
            logger.info(f"句子標準化完成，有效句子: {len(standardized_sentences)}")
            return standardized_sentences
            
        except Exception as e:
            logger.error(f"章節句子處理失敗: {e}")
            return []

# 建立服務實例
split_sentences_service = SplitSentencesService() 