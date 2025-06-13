"""
PDF 分析服務
用於直接分析 PDF 檔案，提取頁面資訊和文本塊位置
"""
import fitz  # PyMuPDF
import pdfplumber
from typing import List, Dict, Any, Optional, Tuple
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

class PDFAnalyzer:
    """PDF 分析器，用於提取頁面資訊和文本塊位置"""
    
    def __init__(self):
        self.pdf_doc = None
        self.text_blocks = []
        self.page_info = {}
    
    async def analyze_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        分析 PDF 檔案，提取頁面資訊和文本塊
        
        Args:
            pdf_path: PDF 檔案路徑
            
        Returns:
            包含頁面資訊和文本塊的字典
        """
        try:
            logger.info(f"開始分析 PDF 檔案: {pdf_path}")
            
            # 檢查檔案是否存在
            if not Path(pdf_path).exists():
                raise FileNotFoundError(f"PDF 檔案不存在: {pdf_path}")
            
            # 使用 PyMuPDF 分析（同步操作）
            analysis_result = self._analyze_with_pymupdf(pdf_path)
            
            # 使用 pdfplumber 補充分析（同步操作）
            plumber_result = self._analyze_with_pdfplumber(pdf_path)
            
            # 合併結果
            final_result = self._merge_analysis_results(analysis_result, plumber_result)
            
            logger.info(f"PDF 分析完成，共 {final_result['total_pages']} 頁，{len(final_result['text_blocks'])} 個文本塊")
            
            return final_result
            
        except Exception as e:
            logger.error(f"PDF 分析失敗: {e}", exc_info=True)
            raise
    
    def _analyze_with_pymupdf(self, pdf_path: str) -> Dict[str, Any]:
        """使用 PyMuPDF 分析 PDF"""
        try:
            doc = fitz.open(pdf_path)
            text_blocks = []
            page_info = {}
            total_pages = len(doc)  # 在關閉文檔前獲取頁數
            
            for page_num in range(total_pages):
                page = doc[page_num]
                page_number = page_num + 1
                
                # 獲取頁面資訊
                page_info[page_number] = {
                    'width': page.rect.width,
                    'height': page.rect.height,
                    'rotation': page.rotation
                }
                
                # 提取文本塊
                blocks = page.get_text("dict")["blocks"]
                
                for block_idx, block in enumerate(blocks):
                    if "lines" in block:  # 文本塊
                        block_text = ""
                        for line in block["lines"]:
                            for span in line["spans"]:
                                block_text += span["text"] + " "
                        
                        if block_text.strip():
                            text_blocks.append({
                                'page_num': page_number,
                                'block_idx': block_idx,
                                'text': block_text.strip(),
                                'bbox': block["bbox"],  # [x0, y0, x1, y1]
                                'font_info': self._extract_font_info(block),
                                'position': {
                                    'x': block["bbox"][0],
                                    'y': block["bbox"][1],
                                    'width': block["bbox"][2] - block["bbox"][0],
                                    'height': block["bbox"][3] - block["bbox"][1]
                                }
                            })
            
            doc.close()
            
            return {
                'total_pages': total_pages,  # 使用預先獲取的頁數
                'text_blocks': text_blocks,
                'page_info': page_info,
                'analyzer': 'pymupdf'
            }
            
        except Exception as e:
            logger.error(f"PyMuPDF 分析失敗: {e}")
            raise
    
    def _analyze_with_pdfplumber(self, pdf_path: str) -> Dict[str, Any]:
        """使用 pdfplumber 分析 PDF（補充分析）"""
        try:
            text_blocks = []
            page_info = {}
            
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_number = page_num + 1
                    
                    # 獲取頁面資訊
                    page_info[page_number] = {
                        'width': page.width,
                        'height': page.height,
                        'rotation': getattr(page, 'rotation', 0)
                    }
                    
                    # 提取文本（按行）
                    text_lines = page.extract_text_lines()
                    
                    for line_idx, line in enumerate(text_lines):
                        if line['text'].strip():
                            text_blocks.append({
                                'page_num': page_number,
                                'line_idx': line_idx,
                                'text': line['text'].strip(),
                                'bbox': [line['x0'], line['top'], line['x1'], line['bottom']],
                                'position': {
                                    'x': line['x0'],
                                    'y': line['top'],
                                    'width': line['x1'] - line['x0'],
                                    'height': line['bottom'] - line['top']
                                }
                            })
            
            return {
                'total_pages': len(pdf.pages),
                'text_blocks': text_blocks,
                'page_info': page_info,
                'analyzer': 'pdfplumber'
            }
            
        except Exception as e:
            logger.error(f"pdfplumber 分析失敗: {e}")
            return {'total_pages': 0, 'text_blocks': [], 'page_info': {}, 'analyzer': 'pdfplumber'}
    
    def _extract_font_info(self, block: Dict) -> Dict[str, Any]:
        """提取字體資訊"""
        font_info = {
            'sizes': set(),
            'families': set(),
            'flags': set()
        }
        
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                font_info['sizes'].add(span.get('size', 0))
                font_info['families'].add(span.get('font', ''))
                font_info['flags'].add(span.get('flags', 0))
        
        return {
            'sizes': list(font_info['sizes']),
            'families': list(font_info['families']),
            'flags': list(font_info['flags'])
        }
    
    def _merge_analysis_results(self, pymupdf_result: Dict, plumber_result: Dict) -> Dict[str, Any]:
        """合併兩種分析結果"""
        # 以 PyMuPDF 結果為主，pdfplumber 結果為輔
        merged_result = pymupdf_result.copy()
        
        # 如果 PyMuPDF 失敗，使用 pdfplumber 結果
        if not merged_result['text_blocks'] and plumber_result['text_blocks']:
            logger.info("PyMuPDF 未提取到文本塊，使用 pdfplumber 結果")
            merged_result = plumber_result.copy()
        
        return merged_result
    
    def find_text_page(self, target_text: str, text_blocks: List[Dict]) -> Optional[int]:
        """
        根據文本內容查找對應的頁碼
        
        Args:
            target_text: 目標文本
            text_blocks: 文本塊列表
            
        Returns:
            頁碼（如果找到）
        """
        try:
            # 清理目標文本
            target_clean = self._clean_text_for_matching(target_text)
            
            if not target_clean:
                return None
            
            best_match_page = None
            best_match_score = 0
            
            for block in text_blocks:
                block_clean = self._clean_text_for_matching(block['text'])
                
                # 計算匹配分數
                match_score = self._calculate_text_similarity(target_clean, block_clean)
                
                if match_score > best_match_score and match_score > 0.3:  # 閾值 30%
                    best_match_score = match_score
                    best_match_page = block['page_num']
            
            if best_match_page:
                logger.debug(f"文本匹配成功，頁碼: {best_match_page}, 匹配分數: {best_match_score:.2f}")
            
            return best_match_page
            
        except Exception as e:
            logger.error(f"文本頁碼匹配失敗: {e}")
            return None
    
    def _clean_text_for_matching(self, text: str) -> str:
        """清理文本用於匹配"""
        if not text:
            return ""
        
        # 移除多餘的空白字符
        text = re.sub(r'\s+', ' ', text.strip())
        
        # 移除標點符號（保留字母和數字）
        text = re.sub(r'[^\w\s]', '', text)
        
        # 轉換為小寫
        text = text.lower()
        
        return text
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """計算兩個文本的相似度"""
        if not text1 or not text2:
            return 0.0
        
        # 簡單的詞彙重疊計算
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def estimate_page_from_position(self, section_index: int, total_sections: int, total_pages: int) -> int:
        """
        根據章節位置估算頁碼
        
        Args:
            section_index: 章節索引（從0開始）
            total_sections: 總章節數
            total_pages: 總頁數
            
        Returns:
            估算的頁碼
        """
        if total_sections <= 0 or total_pages <= 0:
            return 1
        
        # 計算章節在文檔中的相對位置
        relative_position = section_index / max(total_sections - 1, 1)
        
        # 映射到頁碼範圍
        estimated_page = int(relative_position * (total_pages - 1)) + 1
        
        return max(1, min(estimated_page, total_pages))

# 創建全局實例
pdf_analyzer = PDFAnalyzer() 