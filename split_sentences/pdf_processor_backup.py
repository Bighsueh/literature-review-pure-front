import os
import asyncio
import logging
import re
import string
from typing import List, Dict, Any, Optional, Callable, Coroutine
import spacy
from spacy.language import Language
import fitz  # PyMuPDF
import pdfplumber
from tqdm import tqdm

# 配置日誌
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 處理狀態追蹤類
class ProcessingStatus:
    """處理狀態追蹤類，用於跟蹤 PDF 處理進度並通過回調函數報告進度"""
    
    def __init__(self, client_id: str = None):
        self.client_id = client_id
        self.status = "waiting"
        self.progress = 0.0
        self.message = ""
        self.callback = None
    
    def set_callback(self, callback: Callable[[str, float, str], Coroutine]):
        """設置回調函數用於進度報告"""
        self.callback = callback
    
    async def update(self, status: str, progress: float, message: str):
        """更新處理狀態並通過回調函數報告"""
        self.status = status
        self.progress = progress
        self.message = message
        if self.callback is not None:
            await self.callback(status, progress, message)

# 自定義句子分割器，改進句子邊界識別
@Language.component("custom_sentencizer")
def custom_sentencizer(doc):
    """自定義句子分割器組件，識別句子邊界，避免過度分割
    
    Args:
        doc: spaCy Doc 對象
    
    Returns:
        doc: 處理後的 Doc 對象，帶有句子邊界標記
    """
    # 初始化：標記所有 token 的 is_sent_start 為 False
    for token in doc:
        token.is_sent_start = False
    
    # 第一個 token 是句子開始
    if len(doc) > 0:
        doc[0].is_sent_start = True
    
    # 定義強句子終止標記（一定會結束句子的標點）
    strong_end_marks = [".", "!", "?", "。", "！", "？"]
    
    # 定義不應該分割的縮寫和特殊情況的模式
    abbreviations = ["e.g.", "i.e.", "etc.", "vs.", "cf.", "Dr.", "Mr.", "Mrs.", "Ms.", "Jr.", "Sr.", "Prof.", "al.", "Fig.", "ﬁg.", "Ed.", "eds.", "vol.", "p.", "pp.", "Ch.", "Ph.D.", "M.D.", "St.", "Ltd.", "Inc.", "Co."]
    
    # 設置句子邊界
    for i, token in enumerate(doc[:-1]):
        next_token = doc[i+1]
        
        # 檢查是否是縮寫
        is_abbreviation = False
        for abbr in abbreviations:
            # 檢查當前位置的文本是否匹配縮寫
            if i + len(abbr.split()) <= len(doc):
                text_span = "".join([t.text_with_ws for t in doc[i:i+len(abbr.split())]])
                if text_span.strip() == abbr:
                    is_abbreviation = True
                    break
        
        # 作者名的特殊處理（如 "Smith, J." 或 "J. Smith"）
        if (token.text.endswith(".") and token.text[0].isupper() and len(token.text) <= 3) or \
           (next_token.text == "," and i+2 < len(doc) and doc[i+2].text[0].isupper() and len(doc[i+2].text) <= 3 and doc[i+2].text.endswith(".")):
            continue
        
        # 是強句子終止標記且不是縮寫的一部分
        if token.text in strong_end_marks and not is_abbreviation:
            # 檢查下一個標記
            if i + 1 < len(doc):
                # 如果下一個標記不是標點或括號，標記為句子開始
                if not next_token.is_punct or next_token.text in [")", "]", "}", "»", """, "'", "\""]:
                    next_token.is_sent_start = True
                # 除非這是連續引用的一部分 (如 "text." (Author, 2020).)
                elif next_token.text == "(" and i + 5 < len(doc) and any(doc[i+j].text == ")" for j in range(2, 6)):
                    continue
            
        # 行尾換行符通常意味著段落結束，但需要確保不是在段落中間的換行
        elif "\n" in token.whitespace_ and not token.is_punct and not next_token.is_punct:
            # 確保這不是標題或列表項目
            if not token.text.isdigit() and not (token.text.endswith('.') and token.text[:-1].isdigit()):
                next_token.is_sent_start = True
    
    return doc

class PDFProcessor:
    """PDF 處理器類，負責處理 PDF 文本提取和句子切分"""
    
    def __init__(self, nlp=None, use_pdfplumber: bool = False):
        """
        初始化 PDF 處理器
        
        Args:
            nlp: spaCy 語言模型，如果為 None 則加載默認的中文模型
            use_pdfplumber: 是否使用 pdfplumber 而不是 PyMuPDF 來提取文本
        """
        # 如果沒有提供語言模型，加載中文模型
        if nlp is None:
            try:
                self.nlp = spacy.load("zh_core_web_sm")
                # 加入自定義句子分割器
                if "custom_sentencizer" not in self.nlp.pipe_names:
                    self.nlp.add_pipe("custom_sentencizer", before="parser")
            except OSError:
                logger.warning("找不到中文模型，嘗試加載英文模型...")
                try:
                    self.nlp = spacy.load("en_core_web_sm")
                    if "custom_sentencizer" not in self.nlp.pipe_names:
                        self.nlp.add_pipe("custom_sentencizer", before="parser")
                except OSError:
                    logger.warning("無法加載預訓練模型，使用基本英文模型...")
                    self.nlp = spacy.blank("en")
                    # 對於空白模型，直接添加句子分割器
                    self.nlp.add_pipe("custom_sentencizer")
        else:
            self.nlp = nlp
            # 確保模型含有我們的自定義句子分割器
            if "custom_sentencizer" not in self.nlp.pipe_names:
                self.nlp.add_pipe("custom_sentencizer", before="parser" if "parser" in self.nlp.pipe_names else None)
        
        self.use_pdfplumber = use_pdfplumber
    
    def extract_text_from_pdf(self, pdf_path: str, status: ProcessingStatus = None) -> List[Dict[str, Any]]:
        """
        從 PDF 文件中提取文本
        
        Args:
            pdf_path: PDF 文件路徑
            status: 用於跟蹤處理進度的 ProcessingStatus 對象
        
        Returns:
            頁面文本列表，每個元素是包含頁碼和文本的字典
        """
        # 檢查文件是否存在
        if not os.path.exists(pdf_path):
            error_msg = f"PDF 文件不存在: {pdf_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        try:
            # 根據選擇使用不同的提取器
            if self.use_pdfplumber:
                return self._extract_with_pdfplumber(pdf_path, status)
            else:
                return self._extract_with_pymupdf(pdf_path, status)
        except Exception as e:
            error_msg = f"提取 PDF 文本時發生錯誤: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def _extract_with_pymupdf(self, pdf_path: str, status: ProcessingStatus = None) -> List[Dict[str, Any]]:
        """使用 PyMuPDF 提取 PDF 文本"""
        results = []
        
        try:
            # 打開 PDF 文件
            pdf_document = fitz.open(pdf_path)
            total_pages = len(pdf_document)
            
            # 遍歷每一頁
            for i, page in enumerate(pdf_document):
                # 提取文本
                text = page.get_text()
                
                # 清理文本（移除多餘空白等）
                text = self._clean_text(text)
                
                # 添加到結果列表
                if text.strip():  # 只有非空文本才加入結果
                    results.append({
                        "page": i + 1,  # 頁碼從 1 開始
                        "text": text
                    })
                
                # 更新進度
                if status:
                    progress = (i + 1) / total_pages
                    asyncio.create_task(status.update(
                        "extracting", 
                        progress, 
                        f"正在提取第 {i+1}/{total_pages} 頁"
                    ))
            
            return results
            
        except Exception as e:
            logger.error(f"PyMuPDF 提取失敗: {str(e)}")
            raise
    
    def _extract_with_pdfplumber(self, pdf_path: str, status: ProcessingStatus = None) -> List[Dict[str, Any]]:
        """使用 pdfplumber 提取 PDF 文本"""
        results = []
        
        try:
            # 打開 PDF 文件
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                
                # 遍歷每一頁
                for i, page in enumerate(pdf.pages):
                    # 提取文本
                    text = page.extract_text()
                    
                    # 如果提取出的文本為空，嘗試 OCR（需要額外設置）
                    if not text:
                        logger.warning(f"頁面 {i+1} 提取的文本為空")
                    
                    # 清理文本
                    if text:
                        text = self._clean_text(text)
                    
                    # 添加到結果列表
                    if text and text.strip():  # 只有非空文本才加入結果
                        results.append({
                            "page": i + 1,  # 頁碼從 1 開始
                            "text": text
                        })
                    
                    # 更新進度
                    if status:
                        progress = (i + 1) / total_pages
                        asyncio.create_task(status.update(
                            "extracting", 
                            progress, 
                            f"正在提取第 {i+1}/{total_pages} 頁"
                        ))
            
            return results
            
        except Exception as e:
            logger.error(f"pdfplumber 提取失敗: {str(e)}")
            raise
    
    def _clean_text(self, text: str) -> str:
        """清理文本，移除多餘空白和特殊字符"""
        # 替換多個連續空白為單個空格
        text = re.sub(r'\s+', ' ', text)
        # 移除非打印字符（除了空格和換行符）
        text = re.sub(r'[^\x20-\x7E\n]', '', text)
        return text.strip()
    
    def _is_valid_sentence(self, text: str) -> bool:
        """
        判斷一個文本是否是有效的完整句子
        
        Args:
            text: 要判斷的文本
        
        Returns:
            是否是有效的句子
        """
        # 如果句子為空或只包含空白字符，則不是有效句子
        if not text or text.isspace():
            return False
        
        # 如果句子太短（少於10個字符），可能不是有效句子
        # 增加最小長度以過濾掉片段
        if len(text) < 10:
            return False
            
        # 檢查是否是目錄項目（常以數字和點開頭，後面跟著標題和頁碼）
        if re.match(r'^\d+(\.\d+)*\s+.+\s+\d+$', text):
            return False
            
        # 檢查是否是頁碼參考（如 "25 http://dx."）
        if re.match(r'^\d+\s+https?://|^https?://', text):
            return False
            
        # 檢查是否只是URL片段
        if re.match(r'^(https?://|www\.)|(\.(com|org|net|edu|gov|io)/?)\s*$', text):
            return False
        
        # 如果句子只包含數字和標點符號，可能是頁碼或其他非正文內容
        punctuation = r'.,;:!?()[]{}"\'-_+=/<>@#$%^&*~`|\\' 
        if re.match(f'^[\\d\\s{re.escape(punctuation)}]+$', text):
            return False
        
        # 過濾掉可能的標題模式（例如：1.1 章節標題）
        if re.match(r'^\d+(\.\d+)*\s+[A-Z]', text) and not re.search(r'[\.\!\?]\s*$', text):
            return False
            
        # 過濾目錄中的 "Contents" 或其他目錄標記
        if text.startswith("Contents") and len(text.split()) < 4:
            return False
            
        # 過濾電子郵件地址
        if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', text):
            return False
            
        # 過濾頁眉頁腳（通常包含期刊名稱、卷號、頁碼等）
        journal_pattern = re.compile(r'(journal|volume|vol\.|no\.|pages|pp\.).*\d{4}.*\d+[-–]\d+')
        if journal_pattern.search(text.lower()) and len(text.split()) < 10:
            return False
            
        # 過濾引用片段（如 "(Smith, 2020)"）
        if re.match(r'^\([A-Za-z]+(\s+et\s+al\.)?(\s+&\s+[A-Za-z]+)?,\s+\d{4}\)\.?$', text):
            return False
            
        # 過濾通信作者信息
        if re.match(r'^(Corresponding author|E-mail|Tel\.|Address:)', text) and len(text.split()) < 10:
            return False
            
        # 過濾所有權聲明
        if text.strip() in ["All rights reserved.", "Copyright ©"]:
            return False
            
        # 過濾不以句號、問號或感嘆號結尾的短文本（可能是標題或片段）
        if len(text) < 30 and not re.search(r'[\.\!\?\。\？\！]$', text):
            return False
            
        # 確保完整句子有一個主語和謂語結構
        # 簡單啟發式：至少包含一個名詞和一個動詞
        has_subject_predicate = len(text.split()) >= 5
            
        # 通過所有檢查，視為有效句子
        return has_subject_predicate
    
    def combine_sentence_fragments(self, sentences: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        合併同一頁的句子片段
        
        Args:
            sentences: 初步提取的句子列表
        
        Returns:
            合併後的句子列表
        """
        if not sentences:
            return []
            
        result = []
        current_sentence = sentences[0]["sentence"]
        current_page = sentences[0]["page"]
        
        for i in range(1, len(sentences)):
            next_sent = sentences[i]["sentence"]
            next_page = sentences[i]["page"]
            
            # 檢查當前句子和下一個句子是否應該合併
            should_combine = False
            
            # 檢查結束標點
            current_ends_with_punct = re.search(r'[\.\!\?\。\？\！]$', current_sentence)
            
            # 檢查下一句的開頭是否為大寫（英文）或特定中文句首標記
            is_uppercase = False
            if next_sent and len(next_sent) > 0:
                if next_sent[0].isalpha():
                    is_uppercase = next_sent[0].isupper()
                elif next_sent.startswith(("然而", "但是", "不過", "因此", "所以", "因為", "由於")):
                    is_uppercase = True
            
            # 情況1: 當前句子不以標點結束，可能是片段
            if not current_ends_with_punct and current_page == next_page:
                should_combine = True
                
            # 情況2: 短句可能是片段，即使有標點結束（如縮寫或引用）
            elif len(current_sentence) < 30 and current_page == next_page:
                # 檢查是否為學術引用片段，如 "(Smith et al., 2020). The next sentence..."
                if re.search(r'\([A-Za-z\s\.,]+\d{4}\)[\.\,]?$', current_sentence):
                    should_combine = True
                # 檢查是否為縮寫
                elif current_sentence.endswith(("e.g.", "i.e.", "etc.", "vs.")):
                    should_combine = True
                # 檢查是否為數字列表或枚舉
                elif re.search(r'\d+\.$', current_sentence) and is_uppercase:
                    should_combine = True
            
            # 情況3: 括號處理
            if current_sentence.count('(') > current_sentence.count(')') and current_page == next_page:
                should_combine = True
            elif current_sentence.endswith(':') and current_page == next_page:
                should_combine = True
            
            # 如果應該合併，則合併句子
            if should_combine:
                # 選擇適當的連接符（空格或無）
                connector = " " if not (current_sentence.endswith("-") or next_sent.startswith("-")) else ""
                current_sentence = f"{current_sentence}{connector}{next_sent}"
            else:
                # 保存當前句子並開始新句子
                result.append({"sentence": current_sentence, "page": current_page})
                current_sentence = next_sent
                current_page = next_page
        
        # 添加最後一個句子
        if current_sentence:
            result.append({"sentence": current_sentence, "page": current_page})
            
        # 額外過濾：移除仍然不是有效句子的片段
        filtered_results = [s for s in result if self._is_valid_sentence(s["sentence"])]
        
        # 如果過濾後數量變化很大（超過原來的30%），可能過濾太嚴格，回退到更寬鬆的過濾
        if len(filtered_results) < len(result) * 0.7:
            # 二次過濾，僅過濾明顯無效的句子
            return [s for s in result if len(s["sentence"]) > 15 or re.search(r'[\.\!\?\。\？\！]$', s["sentence"])]
        
        return filtered_results
    
    def split_into_sentences(self, pages: List[Dict[str, Any]], status: ProcessingStatus = None) -> List[Dict[str, Any]]:
        """
        將 PDF 頁面文本分割成句子
        
        Args:
            pages: 包含頁碼和文本的字典列表
            status: 用於跟蹤處理進度的 ProcessingStatus 對象
        
        Returns:
            句子列表，每個元素是包含句子文本和頁碼的字典
        """
        sentences = []
        total_pages = len(pages)
        
        # 遍歷每一頁
        for i, page_data in enumerate(pages):
            page_num = page_data["page"]
            text = page_data["text"]
            
            # 預處理：修正常見的 PDF 提取問題
            text = self._preprocess_text(text)
            
            # 使用 spaCy 處理文本
            doc = self.nlp(text)
            
            # 提取句子
            page_sentences = []
            for sent in doc.sents:
                # 移除標題、頁眉、頁腳等（可根據需求添加更多規則）
                sent_text = sent.text.strip()
                
                # 添加到當前頁的句子列表
                page_sentences.append({
                    "sentence": sent_text,
                    "page": page_num
                })
            
            # 合併同一頁內的句子片段
            sentences.extend(page_sentences)
            
            # 更新進度
            if status:
                progress = (i + 1) / total_pages
                asyncio.create_task(status.update(
                    "splitting", 
                    progress, 
                    f"正在處理第 {i+1}/{total_pages} 頁的句子"
                ))
        
        # 合併片段並過濾無效句子
        final_sentences = self.combine_sentence_fragments(sentences)
        
        # 進行最終的過濾
        return [s for s in final_sentences if self._is_valid_sentence(s["sentence"])]
    
    def _preprocess_text(self, text: str) -> str:
        """
        對提取的原始文本進行預處理，修正常見的提取問題
        
        Args:
            text: 原始提取的文本
        
        Returns:
            處理後的文本
        """
        # 修復因換行導致的單詞斷裂
        text = re.sub(r'(\w+)-\n(\w+)', r'\1\2', text)
        
        # 統一各種引號
        text = text.replace('"', '"').replace('"', '"').replace(''', "'").replace(''', "'")
        
        # 修復行間距問題導致的句子斷裂
        text = re.sub(r'([a-z])\n([a-z])', r'\1 \2', text)
        
        # 修復作者名中間的換行
        text = re.sub(r'([A-Z][a-z]+)\n([A-Z]\.)', r'\1 \2', text)
        
        # 移除多餘的空白字符
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    async def process_pdf(self, pdf_path: str, status: ProcessingStatus = None) -> List[Dict[str, Any]]:
        """
        處理 PDF 文件並返回句子列表
        
        Args:
            pdf_path: PDF 文件路徑
            status: 用於跟蹤處理進度的 ProcessingStatus 對象
        
        Returns:
            句子列表，每個元素是包含句子文本和頁碼的字典
        """
        try:
            # 更新狀態
            if status:
                await status.update("starting", 0.0, "開始處理 PDF 文件")
            
            # 提取文本
            if status:
                await status.update("extracting", 0.0, "正在提取 PDF 文本")
            pages = self.extract_text_from_pdf(pdf_path, status)
            
            # 分割句子
            if status:
                await status.update("splitting", 0.0, "正在分割句子")
            sentences = self.split_into_sentences(pages, status)
            
            # 處理完成
            if status:
                await status.update("completed", 1.0, "PDF 處理完成")
            
            return sentences
            
        except Exception as e:
            error_msg = f"處理 PDF 文件時發生錯誤: {str(e)}"
            logger.error(error_msg)
            
            # 更新失敗狀態
            if status:
                await status.update("failed", 0.0, error_msg)
            
            raise RuntimeError(error_msg) 