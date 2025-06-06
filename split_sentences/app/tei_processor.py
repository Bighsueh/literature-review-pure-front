import time
import logging
from typing import List, Dict, Any, Optional
import spacy
from spacy.language import Language

from .models import TEISection, ProcessedSentence, ProcessingStats, TEISplitResponse
from .pdf_processor import custom_sentencizer

# 配置日誌
logger = logging.getLogger(__name__)

class TEIProcessor:
    """TEI 處理器類，專門處理 Grobid 輸出的結構化章節內容"""
    
    def __init__(self, nlp=None):
        """
        初始化 TEI 處理器
        
        Args:
            nlp: spaCy 語言模型，如果為 None 則加載適當的模型
        """
        if nlp is None:
            try:
                # 優先加載中文模型
                self.nlp = spacy.load("zh_core_web_sm")
                logger.info("成功加載中文 spaCy 模型")
            except OSError:
                try:
                    # 回退到英文模型
                    self.nlp = spacy.load("en_core_web_sm")
                    logger.info("中文模型不可用，使用英文 spaCy 模型")
                except OSError:
                    # 使用基本英文模型
                    self.nlp = spacy.blank("en")
                    logger.warning("預訓練模型不可用，使用基本英文模型")
        else:
            self.nlp = nlp
        
        # 確保加載自定義句子分割器
        if "custom_sentencizer" not in self.nlp.pipe_names:
            self.nlp.add_pipe("custom_sentencizer", 
                             before="parser" if "parser" in self.nlp.pipe_names else None)
            logger.info("已添加自定義句子分割器")
    
    def process_tei_sections(
        self, 
        sections: List[TEISection], 
        language: str = "mixed"
    ) -> TEISplitResponse:
        """
        處理 TEI 章節列表，將每個章節的內容切分為句子
        
        Args:
            sections: TEI 章節列表
            language: 文本語言設定
            
        Returns:
            TEISplitResponse: 包含處理後句子和統計資訊的回應
        """
        start_time = time.time()
        all_sentences = []
        total_sections = len(sections)
        
        logger.info(f"開始處理 {total_sections} 個章節")
        
        for section in sections:
            try:
                # 處理單個章節
                section_sentences = self._process_single_section(section)
                all_sentences.extend(section_sentences)
                
                logger.debug(f"章節 {section.section_type} 生成 {len(section_sentences)} 個句子")
                
            except Exception as e:
                logger.error(f"處理章節 {section.section_type} 時出錯: {str(e)}")
                # 繼續處理其他章節，不中斷整個流程
                continue
        
        # 計算處理統計
        processing_time_ms = (time.time() - start_time) * 1000
        total_sentences = len(all_sentences)
        
        stats = ProcessingStats(
            total_sections=total_sections,
            total_sentences=total_sentences,
            processing_time_ms=processing_time_ms
        )
        
        logger.info(f"TEI 處理完成：{total_sections} 個章節，{total_sentences} 個句子，耗時 {processing_time_ms:.2f}ms")
        
        return TEISplitResponse(
            sentences=all_sentences,
            processing_stats=stats
        )
    
    def _process_single_section(self, section: TEISection) -> List[ProcessedSentence]:
        """
        處理單個章節，將其內容切分為句子
        
        Args:
            section: TEI 章節
            
        Returns:
            List[ProcessedSentence]: 該章節的句子列表
        """
        sentences = []
        
        # 清理並預處理文本
        cleaned_content = self._clean_section_content(section.content)
        
        if not cleaned_content.strip():
            logger.warning(f"章節 {section.section_type} 內容為空")
            return sentences
        
        try:
            # 使用 spaCy 進行句子切分
            doc = self.nlp(cleaned_content)
            
            sentence_order = 0
            for sent in doc.sents:
                sentence_text = sent.text.strip()
                
                # 驗證句子品質
                if self._is_valid_sentence(sentence_text):
                    processed_sentence = ProcessedSentence(
                        text=sentence_text,
                        section_type=section.section_type,
                        sentence_order=sentence_order,
                        page_num=section.page_start,  # 使用章節起始頁作為句子頁碼
                        confidence=self._calculate_sentence_confidence(sentence_text)
                    )
                    
                    sentences.append(processed_sentence)
                    sentence_order += 1
        
        except Exception as e:
            logger.error(f"切分章節 {section.section_type} 句子時出錯: {str(e)}")
            # 如果句子切分失敗，至少保存原始內容
            if cleaned_content.strip():
                fallback_sentence = ProcessedSentence(
                    text=cleaned_content,
                    section_type=section.section_type,
                    sentence_order=0,
                    page_num=section.page_start,
                    confidence=0.5  # 低信心度表示這是回退結果
                )
                sentences.append(fallback_sentence)
        
        return sentences
    
    def _clean_section_content(self, content: str) -> str:
        """
        清理章節內容，移除多餘的空白和格式化字符
        
        Args:
            content: 原始章節內容
            
        Returns:
            str: 清理後的內容
        """
        import re
        
        # 移除多餘的空白和換行
        content = re.sub(r'\s+', ' ', content)
        
        # 移除首尾空白
        content = content.strip()
        
        # 移除重複的標點符號
        content = re.sub(r'([.!?])\1+', r'\1', content)
        
        # 處理常見的 OCR 錯誤和格式問題
        content = re.sub(r'\s+([,.!?;:])', r'\1', content)  # 標點前的空格
        content = re.sub(r'([.!?])\s*([A-Z])', r'\1 \2', content)  # 句子間確保有空格
        
        return content
    
    def _is_valid_sentence(self, text: str) -> bool:
        """
        驗證句子是否有效
        
        Args:
            text: 句子文本
            
        Returns:
            bool: 句子是否有效
        """
        if not text or len(text.strip()) < 3:
            return False
        
        # 過濾只包含標點或數字的句子
        if text.strip() in '.,;:!?()[]{}':
            return False
        
        # 過濾過短的句子（但保留有意義的短句）
        if len(text.strip()) < 10 and not any(char.isalpha() for char in text):
            return False
        
        # 過濾只有頁碼或參考號的句子
        import re
        if re.match(r'^\s*[\d\.\-\s]+\s*$', text):
            return False
        
        return True
    
    def _calculate_sentence_confidence(self, text: str) -> float:
        """
        計算句子切分的信心度
        
        Args:
            text: 句子文本
            
        Returns:
            float: 信心度 (0.0 - 1.0)
        """
        confidence = 1.0
        
        # 根據句子長度調整信心度
        length = len(text.strip())
        if length < 10:
            confidence *= 0.7
        elif length > 500:
            confidence *= 0.8
        
        # 檢查是否有適當的句子結尾
        if text.strip()[-1] in '.!?。！？':
            confidence *= 1.0
        else:
            confidence *= 0.9
        
        # 檢查是否有不完整的句子結構
        import re
        if re.search(r'\b(and|or|but|however|therefore|moreover)\s*$', text.lower()):
            confidence *= 0.8
        
        return min(confidence, 1.0) 
import logging
from typing import List, Dict, Any, Optional
import spacy
from spacy.language import Language

from .models import TEISection, ProcessedSentence, ProcessingStats, TEISplitResponse
from .pdf_processor import custom_sentencizer

# 配置日誌
logger = logging.getLogger(__name__)

class TEIProcessor:
    """TEI 處理器類，專門處理 Grobid 輸出的結構化章節內容"""
    
    def __init__(self, nlp=None):
        """
        初始化 TEI 處理器
        
        Args:
            nlp: spaCy 語言模型，如果為 None 則加載適當的模型
        """
        if nlp is None:
            try:
                # 優先加載中文模型
                self.nlp = spacy.load("zh_core_web_sm")
                logger.info("成功加載中文 spaCy 模型")
            except OSError:
                try:
                    # 回退到英文模型
                    self.nlp = spacy.load("en_core_web_sm")
                    logger.info("中文模型不可用，使用英文 spaCy 模型")
                except OSError:
                    # 使用基本英文模型
                    self.nlp = spacy.blank("en")
                    logger.warning("預訓練模型不可用，使用基本英文模型")
        else:
            self.nlp = nlp
        
        # 確保加載自定義句子分割器
        if "custom_sentencizer" not in self.nlp.pipe_names:
            self.nlp.add_pipe("custom_sentencizer", 
                             before="parser" if "parser" in self.nlp.pipe_names else None)
            logger.info("已添加自定義句子分割器")
    
    def process_tei_sections(
        self, 
        sections: List[TEISection], 
        language: str = "mixed"
    ) -> TEISplitResponse:
        """
        處理 TEI 章節列表，將每個章節的內容切分為句子
        
        Args:
            sections: TEI 章節列表
            language: 文本語言設定
            
        Returns:
            TEISplitResponse: 包含處理後句子和統計資訊的回應
        """
        start_time = time.time()
        all_sentences = []
        total_sections = len(sections)
        
        logger.info(f"開始處理 {total_sections} 個章節")
        
        for section in sections:
            try:
                # 處理單個章節
                section_sentences = self._process_single_section(section)
                all_sentences.extend(section_sentences)
                
                logger.debug(f"章節 {section.section_type} 生成 {len(section_sentences)} 個句子")
                
            except Exception as e:
                logger.error(f"處理章節 {section.section_type} 時出錯: {str(e)}")
                # 繼續處理其他章節，不中斷整個流程
                continue
        
        # 計算處理統計
        processing_time_ms = (time.time() - start_time) * 1000
        total_sentences = len(all_sentences)
        
        stats = ProcessingStats(
            total_sections=total_sections,
            total_sentences=total_sentences,
            processing_time_ms=processing_time_ms
        )
        
        logger.info(f"TEI 處理完成：{total_sections} 個章節，{total_sentences} 個句子，耗時 {processing_time_ms:.2f}ms")
        
        return TEISplitResponse(
            sentences=all_sentences,
            processing_stats=stats
        )
    
    def _process_single_section(self, section: TEISection) -> List[ProcessedSentence]:
        """
        處理單個章節，將其內容切分為句子
        
        Args:
            section: TEI 章節
            
        Returns:
            List[ProcessedSentence]: 該章節的句子列表
        """
        sentences = []
        
        # 清理並預處理文本
        cleaned_content = self._clean_section_content(section.content)
        
        if not cleaned_content.strip():
            logger.warning(f"章節 {section.section_type} 內容為空")
            return sentences
        
        try:
            # 使用 spaCy 進行句子切分
            doc = self.nlp(cleaned_content)
            
            sentence_order = 0
            for sent in doc.sents:
                sentence_text = sent.text.strip()
                
                # 驗證句子品質
                if self._is_valid_sentence(sentence_text):
                    processed_sentence = ProcessedSentence(
                        text=sentence_text,
                        section_type=section.section_type,
                        sentence_order=sentence_order,
                        page_num=section.page_start,  # 使用章節起始頁作為句子頁碼
                        confidence=self._calculate_sentence_confidence(sentence_text)
                    )
                    
                    sentences.append(processed_sentence)
                    sentence_order += 1
        
        except Exception as e:
            logger.error(f"切分章節 {section.section_type} 句子時出錯: {str(e)}")
            # 如果句子切分失敗，至少保存原始內容
            if cleaned_content.strip():
                fallback_sentence = ProcessedSentence(
                    text=cleaned_content,
                    section_type=section.section_type,
                    sentence_order=0,
                    page_num=section.page_start,
                    confidence=0.5  # 低信心度表示這是回退結果
                )
                sentences.append(fallback_sentence)
        
        return sentences
    
    def _clean_section_content(self, content: str) -> str:
        """
        清理章節內容，移除多餘的空白和格式化字符
        
        Args:
            content: 原始章節內容
            
        Returns:
            str: 清理後的內容
        """
        import re
        
        # 移除多餘的空白和換行
        content = re.sub(r'\s+', ' ', content)
        
        # 移除首尾空白
        content = content.strip()
        
        # 移除重複的標點符號
        content = re.sub(r'([.!?])\1+', r'\1', content)
        
        # 處理常見的 OCR 錯誤和格式問題
        content = re.sub(r'\s+([,.!?;:])', r'\1', content)  # 標點前的空格
        content = re.sub(r'([.!?])\s*([A-Z])', r'\1 \2', content)  # 句子間確保有空格
        
        return content
    
    def _is_valid_sentence(self, text: str) -> bool:
        """
        驗證句子是否有效
        
        Args:
            text: 句子文本
            
        Returns:
            bool: 句子是否有效
        """
        if not text or len(text.strip()) < 3:
            return False
        
        # 過濾只包含標點或數字的句子
        if text.strip() in '.,;:!?()[]{}':
            return False
        
        # 過濾過短的句子（但保留有意義的短句）
        if len(text.strip()) < 10 and not any(char.isalpha() for char in text):
            return False
        
        # 過濾只有頁碼或參考號的句子
        import re
        if re.match(r'^\s*[\d\.\-\s]+\s*$', text):
            return False
        
        return True
    
    def _calculate_sentence_confidence(self, text: str) -> float:
        """
        計算句子切分的信心度
        
        Args:
            text: 句子文本
            
        Returns:
            float: 信心度 (0.0 - 1.0)
        """
        confidence = 1.0
        
        # 根據句子長度調整信心度
        length = len(text.strip())
        if length < 10:
            confidence *= 0.7
        elif length > 500:
            confidence *= 0.8
        
        # 檢查是否有適當的句子結尾
        if text.strip()[-1] in '.!?。！？':
            confidence *= 1.0
        else:
            confidence *= 0.9
        
        # 檢查是否有不完整的句子結構
        import re
        if re.search(r'\b(and|or|but|however|therefore|moreover)\s*$', text.lower()):
            confidence *= 0.8
        
        return min(confidence, 1.0) 