import os
import logging
import asyncio
from typing import List, Callable, Optional, Awaitable
import spacy
import tempfile
from pathlib import Path
import re

# 嘗試匯入 Nougat 相關模組
try:
    from nougat.utils.checkpoint import get_checkpoint
    from nougat.utils.device import init_device
    from nougat.dataset.transforms import NougatTransform
    from nougat.dataset.rasterize import load_pdf_or_image
    from nougat import NougatModel
except ImportError:
    logging.warning("無法匯入 Nougat 模塊，將嘗試使用替代方法。請確保已安裝 Nougat: pip install nougat-ocr")

# 設定日誌
logger = logging.getLogger(__name__)

class PdfProcessor:
    """
    PDF 處理服務：使用 Nougat 進行 PDF 文字提取，和 spaCy 進行句子分割
    """
    
    def __init__(self):
        """初始化處理器"""
        self.progress_callback = None
        self._initialize_spacy()
        self._initialize_nougat()
    
    def _initialize_spacy(self):
        """初始化 spaCy 模型"""
        try:
            # 載入中文模型，如果使用英文則可改為 'en_core_web_sm'
            self.nlp = spacy.load("zh_core_web_sm")
            logger.info("spaCy 模型載入成功")
        except OSError:
            # 如果模型未安裝，嘗試下載
            logger.warning("spaCy 模型未找到，嘗試下載...")
            try:
                spacy.cli.download("zh_core_web_sm")
                self.nlp = spacy.load("zh_core_web_sm")
                logger.info("spaCy 模型下載並載入成功")
            except Exception as e:
                logger.error(f"無法下載 spaCy 模型: {str(e)}")
                raise RuntimeError(f"無法初始化 spaCy: {str(e)}")
    
    def _initialize_nougat(self):
        """初始化 Nougat 模型"""
        try:
            # 初始化 Nougat 模型
            device, num_workers = init_device()
            checkpoint = get_checkpoint("default", download_root=os.environ.get("NOUGAT_CHECKPOINT_PATH", None))
            model = NougatModel.from_pretrained(checkpoint)
            model.to(device)
            self.nougat_transform = NougatTransform(
                image_size=(896, 672),
                patch_size=model.config.vision_config.patch_size,
            )
            self.nougat_model = model
            self.nougat_device = device
            logger.info("Nougat 模型載入成功")
        except Exception as e:
            logger.error(f"無法初始化 Nougat 模型: {str(e)}")
            self.nougat_model = None
            logger.warning("將使用替代方法進行 PDF 處理")
    
    def register_progress_callback(self, callback: Callable[[str, float], Awaitable[None]]):
        """註冊進度回調函數"""
        self.progress_callback = callback
    
    async def _report_progress(self, message: str, progress: float):
        """報告處理進度"""
        if self.progress_callback:
            await self.progress_callback(message, progress)
    
    async def process_pdf(self, pdf_path: str) -> List[str]:
        """
        處理 PDF 文件，提取文字並分割成句子
        
        Args:
            pdf_path: PDF 文件路徑
            
        Returns:
            List[str]: 分割後的句子列表
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"找不到 PDF 文件: {pdf_path}")
        
        await self._report_progress("開始處理 PDF 文件", 0.0)
        
        # 使用 Nougat 提取 PDF 文本
        text = await self._extract_text_from_pdf(pdf_path)
        
        await self._report_progress("文本提取完成，開始分割句子", 0.7)
        
        # 使用 spaCy 分割句子
        sentences = self._split_sentences(text)
        
        await self._report_progress("句子分割完成", 1.0)
        
        return sentences
    
    async def _extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        從 PDF 提取文字
        
        Args:
            pdf_path: PDF 文件路徑
            
        Returns:
            str: 提取的文本
        """
        try:
            # 如果 Nougat 模型可用，則使用 Nougat
            if self.nougat_model:
                return await self._extract_text_with_nougat(pdf_path)
            else:
                # 如果 Nougat 不可用，嘗試使用替代方法
                # 這裡只是一個簡單的示例，實際應用中應添加更多替代方案
                logger.warning("Nougat 不可用，嘗試使用替代方法提取文本")
                
                # 可以在這裡添加 PyMuPDF (fitz) 或其他 PDF 處理庫作為替代
                from io import StringIO
                import fitz  # PyMuPDF

                text_buffer = StringIO()
                doc = fitz.open(pdf_path)
                total_pages = len(doc)
                
                for i, page in enumerate(doc):
                    text = page.get_text("text")
                    text_buffer.write(text)
                    text_buffer.write("\n\n")
                    
                    # 報告進度
                    progress = 0.1 + (i / total_pages) * 0.6
                    await self._report_progress(f"處理頁面 {i+1}/{total_pages}", progress)
                
                doc.close()
                return text_buffer.getvalue()
                
        except Exception as e:
            logger.error(f"提取 PDF 文本時發生錯誤: {str(e)}")
            raise RuntimeError(f"無法提取 PDF 文本: {str(e)}")
    
    async def _extract_text_with_nougat(self, pdf_path: str) -> str:
        """
        使用 Nougat 從 PDF 提取文字
        
        Args:
            pdf_path: PDF 文件路徑
            
        Returns:
            str: 提取的文本
        """
        try:
            # 加載 PDF
            doc = load_pdf_or_image(pdf_path)
            total_pages = len(doc)
            full_text = []
            
            for i, page in enumerate(doc):
                # 報告進度
                await self._report_progress(f"使用 Nougat 處理頁面 {i+1}/{total_pages}", 0.1 + (i / total_pages) * 0.6)
                
                # 準備輸入
                image = page.convert("RGB")
                image = self.nougat_transform(image)
                image = image.unsqueeze(0).to(self.nougat_device)
                
                # 生成文本
                with tempfile.NamedTemporaryFile(suffix=".mmd", delete=True) as tmp_file:
                    output_path = Path(tmp_file.name)
                    self.nougat_model.inference(
                        image, 
                        output_path, 
                        batch_size=1,
                        beam_size=1,
                        postprocess=True
                    )
                    # 讀取生成的 MMD 文件
                    with open(output_path, "r", encoding="utf-8") as f:
                        mmd_text = f.read()
                    
                    # 處理 MMD 文本，去除標記等
                    cleaned_text = self._clean_mmd_text(mmd_text)
                    full_text.append(cleaned_text)
            
            return "\n\n".join(full_text)
        
        except Exception as e:
            logger.error(f"使用 Nougat 提取文本時發生錯誤: {str(e)}")
            raise RuntimeError(f"Nougat 提取失敗: {str(e)}")
    
    def _clean_mmd_text(self, mmd_text: str) -> str:
        """
        清理 Nougat 輸出的 MMD 文本
        
        Args:
            mmd_text: MMD 格式的文本
            
        Returns:
            str: 清理後的純文本
        """
        # 移除 Markdown 標題
        text = re.sub(r'#+\s+.*?\n', '\n', mmd_text)
        
        # 移除表格標記
        text = re.sub(r'\|.*?\|', ' ', text)
        
        # 移除LaTeX公式
        text = re.sub(r'\$\$.*?\$\$', ' ', text, flags=re.DOTALL)
        text = re.sub(r'\$.*?\$', ' ', text)
        
        # 移除其他常見 Markdown 標記
        text = re.sub(r'!\[.*?\]\(.*?\)', '', text)  # 圖片
        text = re.sub(r'\[.*?\]\(.*?\)', '', text)  # 鏈接
        text = re.sub(r'[*_]{1,2}(.*?)[*_]{1,2}', r'\1', text)  # 強調
        
        # 移除多餘空白行
        text = re.sub(r'\n\s*\n+', '\n\n', text)
        
        return text.strip()
    
    def _split_sentences(self, text: str) -> List[str]:
        """
        使用 spaCy 將文本分割成句子
        
        Args:
            text: 要分割的文本
            
        Returns:
            List[str]: 分割後的句子列表
        """
        # 分割長文本以避免 spaCy 處理過大的文本
        chunks = self._split_text_into_chunks(text, 50000)  # 每塊最大 50K 字符
        all_sentences = []
        
        for chunk in chunks:
            doc = self.nlp(chunk)
            chunk_sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
            all_sentences.extend(chunk_sentences)
        
        # 過濾掉太短的句子
        filtered_sentences = [s for s in all_sentences if len(s) > 3]
        
        return filtered_sentences
    
    def _split_text_into_chunks(self, text: str, max_length: int) -> List[str]:
        """
        將文本分割成較小的塊，以便 spaCy 處理
        
        Args:
            text: 要分割的文本
            max_length: 每塊的最大長度
            
        Returns:
            List[str]: 分割後的文本塊
        """
        chunks = []
        current_pos = 0
        text_length = len(text)
        
        while current_pos < text_length:
            # 嘗試在段落邊界切分
            end_pos = min(current_pos + max_length, text_length)
            if end_pos < text_length:
                # 嘗試在段落或句子邊界處切分
                paragraph_boundary = text.rfind('\n\n', current_pos, end_pos)
                sentence_boundary = text.rfind('. ', current_pos, end_pos)
                
                if paragraph_boundary != -1 and paragraph_boundary > current_pos + max_length // 2:
                    end_pos = paragraph_boundary + 2
                elif sentence_boundary != -1 and sentence_boundary > current_pos + max_length // 2:
                    end_pos = sentence_boundary + 2
            
            chunks.append(text[current_pos:end_pos])
            current_pos = end_pos
        
        return chunks 