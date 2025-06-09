import asyncio
import aiohttp
import aiofiles
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element
import re
import time
import uuid
from datetime import datetime

from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger("grobid_service")

class GrobidService:
    """Grobid服務包裝類"""
    
    def __init__(self):
        self.base_url = settings.grobid_url
        self.timeout = aiohttp.ClientTimeout(total=300)  # 5分鐘超時
        self.max_retries = 3
        self.retry_delay = 2  # 秒
        
        # TEI XML命名空間
        self.tei_ns = {
            'tei': 'http://www.tei-c.org/ns/1.0'
        }
        
        logger.info(f"Grobid服務初始化完成，URL: {self.base_url}")
    
    # ===== Grobid API呼叫 =====
    
    async def health_check(self) -> bool:
        """檢查Grobid服務健康狀態"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(f"{self.base_url}/api/isalive") as response:
                    if response.status == 200:
                        logger.info("Grobid服務健康檢查通過")
                        return True
                    else:
                        logger.warning(f"Grobid服務健康檢查失敗，狀態碼: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"Grobid服務健康檢查失敗: {e}")
            return False
    
    async def process_pdf_to_tei(self, pdf_path: str) -> Optional[str]:
        """
        使用Grobid處理PDF檔案，返回TEI XML
        """
        try:
            if not Path(pdf_path).exists():
                raise FileNotFoundError(f"PDF檔案不存在: {pdf_path}")
            
            logger.info(f"開始Grobid處理: {pdf_path}")
            start_time = time.time()
            
            # 嘗試多次重試
            for attempt in range(self.max_retries):
                try:
                    tei_xml = await self._call_grobid_api(pdf_path)
                    if tei_xml:
                        process_time = time.time() - start_time
                        logger.info(f"Grobid處理完成，耗時: {process_time:.2f}秒")
                        return tei_xml
                except Exception as e:
                    logger.warning(f"Grobid處理嘗試 {attempt + 1} 失敗: {e}")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay)
                    else:
                        raise
            
            return None
            
        except Exception as e:
            logger.error(f"Grobid處理失敗: {e}")
            raise
    
    async def _call_grobid_api(self, pdf_path: str) -> Optional[str]:
        """實際呼叫Grobid API"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                # 準備檔案上傳
                async with aiofiles.open(pdf_path, 'rb') as f:
                    pdf_content = await f.read()
                
                data = aiohttp.FormData()
                data.add_field('input', 
                             pdf_content, 
                             filename=Path(pdf_path).name,
                             content_type='application/pdf')
                data.add_field('consolidateHeader', '1')
                data.add_field('consolidateCitations', '0')  # 加快處理速度
                data.add_field('includeRawCitations', '1')
                data.add_field('includeRawAffiliations', '1')
                data.add_field('teiCoordinates', 'persName,figure,ref,head,note,s')
                
                # 呼叫processFulltextDocument API
                url = f"{self.base_url}/api/processFulltextDocument"
                async with session.post(url, data=data) as response:
                    if response.status == 200:
                        tei_xml = await response.text()
                        logger.debug(f"成功獲得TEI XML，長度: {len(tei_xml)} 字符")
                        return tei_xml
                    else:
                        error_text = await response.text()
                        logger.error(f"Grobid API呼叫失敗，狀態碼: {response.status}, 錯誤: {error_text}")
                        return None
                        
        except asyncio.TimeoutError:
            logger.error("Grobid API呼叫超時")
            return None
        except Exception as e:
            logger.error(f"Grobid API呼叫異常: {e}")
            raise
    
    # ===== TEI XML解析 =====
    
    def parse_tei_xml(self, tei_xml: str) -> Dict[str, Any]:
        """
        解析TEI XML，提取論文元資料和結構
        """
        try:
            root = ET.fromstring(tei_xml)
            
            # 提取基本元資料
            metadata = self._extract_metadata(root)
            
            # 提取章節結構
            sections = self._extract_sections(root)
            
            # 提取參考文獻
            references = self._extract_references(root)
            
            # 提取圖表
            figures = self._extract_figures(root)
            
            result = {
                "metadata": metadata,
                "sections": sections,
                "references": references,
                "figures": figures,
                "section_count": len(sections),
                "total_word_count": sum(section.get('word_count', 0) for section in sections),
                "processing_timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"TEI XML解析完成，找到 {len(sections)} 個章節")
            return result
            
        except ET.ParseError as e:
            logger.error(f"TEI XML解析失敗，XML格式錯誤: {e}")
            raise ValueError(f"無效的TEI XML格式: {e}")
        except Exception as e:
            logger.error(f"TEI XML解析失敗: {e}")
            raise
    
    def _extract_metadata(self, root: Element) -> Dict[str, Any]:
        """提取論文元資料"""
        metadata = {}
        
        try:
            # 提取標題
            title_elem = root.find('.//tei:titleStmt/tei:title', self.tei_ns)
            if title_elem is not None:
                metadata['title'] = self._clean_text(title_elem.text or '')
            
            # 提取作者
            authors = []
            author_elems = root.findall('.//tei:author', self.tei_ns)
            for author in author_elems:
                name_elem = author.find('.//tei:persName', self.tei_ns)
                if name_elem is not None:
                    # 提取姓名各部分
                    forename = name_elem.find('./tei:forename', self.tei_ns)
                    surname = name_elem.find('./tei:surname', self.tei_ns)
                    
                    author_name = ""
                    if forename is not None:
                        author_name += forename.text or ""
                    if surname is not None:
                        if author_name:
                            author_name += " "
                        author_name += surname.text or ""
                    
                    if author_name:
                        authors.append(author_name.strip())
            
            metadata['authors'] = authors
            
            # 提取摘要
            abstract_elem = root.find('.//tei:abstract', self.tei_ns)
            if abstract_elem is not None:
                metadata['abstract'] = self._clean_text(''.join(abstract_elem.itertext()))
            
            # 提取關鍵詞
            keywords = []
            keyword_elems = root.findall('.//tei:keywords/tei:term', self.tei_ns)
            for keyword in keyword_elems:
                if keyword.text:
                    keywords.append(keyword.text.strip())
            metadata['keywords'] = keywords
            
            logger.debug(f"提取元資料完成: {metadata.get('title', 'Unknown')}")
            
        except Exception as e:
            logger.warning(f"元資料提取部分失敗: {e}")
        
        return metadata
    
    def _extract_sections(self, root: Element) -> List[Dict[str, Any]]:
        """提取章節內容"""
        sections = []
        
        try:
            # 查找所有章節
            div_elems = root.findall('.//tei:text//tei:div', self.tei_ns)
            
            for i, div in enumerate(div_elems):
                section = {}
                
                # 提取章節標題
                head_elem = div.find('./tei:head', self.tei_ns)
                if head_elem is not None:
                    section['title'] = self._clean_text(head_elem.text or '')
                else:
                    section['title'] = f"Section {i + 1}"
                
                # 提取章節內容
                content_parts = []
                for elem in div.iter():
                    if elem.tag.endswith('}p'):  # 段落
                        text = self._clean_text(''.join(elem.itertext()))
                        if text:
                            content_parts.append(text)
                
                section['content'] = '\n\n'.join(content_parts)
                section['word_count'] = len(section['content'].split())
                section['section_order'] = i + 1
                
                # 嘗試分類章節類型
                section['section_type'] = self._classify_section_type(section['title'])
                
                # 提取頁碼資訊（如果有座標資訊）
                section['page_num'] = self._extract_page_info(div)
                
                if section['content']:  # 只添加有內容的章節
                    sections.append(section)
            
            logger.info(f"成功提取 {len(sections)} 個章節")
            
        except Exception as e:
            logger.error(f"章節提取失敗: {e}")
        
        return sections
    
    def _extract_references(self, root: Element) -> List[Dict[str, Any]]:
        """提取參考文獻"""
        references = []
        
        try:
            ref_elems = root.findall('.//tei:listBibl/tei:biblStruct', self.tei_ns)
            
            for i, ref in enumerate(ref_elems):
                reference = {
                    'id': i + 1,
                    'raw_text': self._clean_text(''.join(ref.itertext()))
                }
                
                # 提取標題
                title_elem = ref.find('.//tei:title', self.tei_ns)
                if title_elem is not None:
                    reference['title'] = self._clean_text(title_elem.text or '')
                
                # 提取作者
                authors = []
                author_elems = ref.findall('.//tei:author', self.tei_ns)
                for author in author_elems:
                    name = self._clean_text(''.join(author.itertext()))
                    if name:
                        authors.append(name)
                reference['authors'] = authors
                
                references.append(reference)
            
            logger.debug(f"提取 {len(references)} 個參考文獻")
            
        except Exception as e:
            logger.warning(f"參考文獻提取失敗: {e}")
        
        return references
    
    def _extract_figures(self, root: Element) -> List[Dict[str, Any]]:
        """提取圖表資訊"""
        figures = []
        
        try:
            figure_elems = root.findall('.//tei:figure', self.tei_ns)
            
            for i, fig in enumerate(figure_elems):
                figure = {
                    'id': i + 1,
                    'type': fig.get('type', 'unknown')
                }
                
                # 提取圖表標題
                head_elem = fig.find('./tei:head', self.tei_ns)
                if head_elem is not None:
                    figure['caption'] = self._clean_text(head_elem.text or '')
                
                figures.append(figure)
            
            logger.debug(f"提取 {len(figures)} 個圖表")
            
        except Exception as e:
            logger.warning(f"圖表提取失敗: {e}")
        
        return figures
    
    # ===== 工具方法 =====
    
    def _clean_text(self, text: str) -> str:
        """清理文字，移除多餘空白和控制字符"""
        if not text:
            return ""
        
        # 移除多餘空白
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text
    
    def _classify_section_type(self, title: str) -> str:
        """根據標題分類章節類型"""
        title_lower = title.lower()
        
        if any(keyword in title_lower for keyword in ['abstract', 'summary']):
            return 'abstract'
        elif any(keyword in title_lower for keyword in ['introduction', 'intro']):
            return 'introduction'
        elif any(keyword in title_lower for keyword in ['method', 'methodology', 'approach']):
            return 'methodology'
        elif any(keyword in title_lower for keyword in ['result', 'finding', 'outcome']):
            return 'results'
        elif any(keyword in title_lower for keyword in ['discussion', 'analysis']):
            return 'discussion'
        elif any(keyword in title_lower for keyword in ['conclusion', 'summary']):
            return 'conclusion'
        elif any(keyword in title_lower for keyword in ['reference', 'bibliography']):
            return 'references'
        elif any(keyword in title_lower for keyword in ['related work', 'literature review', 'background']):
            return 'related_work'
        else:
            return 'other'
    
    def _extract_page_info(self, element: Element) -> Optional[int]:
        """提取頁碼資訊"""
        try:
            # 查找座標資訊
            coords = element.get('coords')
            if coords:
                # 解析座標格式 (通常包含頁碼)
                parts = coords.split(',')
                if len(parts) >= 5:  # 頁碼通常在第5個位置
                    return int(parts[4])
        except:
            pass
        
        return None
    
    # ===== 高層級處理方法 =====
    
    async def process_paper_complete(self, pdf_path: str) -> Dict[str, Any]:
        """
        完整處理論文：從PDF到結構化資料
        """
        try:
            logger.info(f"開始完整論文處理: {pdf_path}")
            
            # Step 1: 處理PDF獲得TEI XML
            tei_xml = await self.process_pdf_to_tei(pdf_path)
            if not tei_xml:
                raise ValueError("無法獲得有效的TEI XML")
            
            # Step 2: 解析TEI XML
            parsed_data = self.parse_tei_xml(tei_xml)
            
            # Step 3: 添加處理資訊
            parsed_data['pdf_path'] = pdf_path
            parsed_data['tei_xml'] = tei_xml
            parsed_data['processing_success'] = True
            
            logger.info(f"論文處理完成: {parsed_data['metadata'].get('title', 'Unknown')}")
            return parsed_data
            
        except Exception as e:
            logger.error(f"完整論文處理失敗: {e}")
            return {
                'pdf_path': pdf_path,
                'processing_success': False,
                'error_message': str(e),
                'processing_timestamp': datetime.now().isoformat()
            }
    
    def get_section_summary(self, sections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成章節摘要統計"""
        if not sections:
            return {}
        
        section_types = {}
        total_words = 0
        
        for section in sections:
            section_type = section.get('section_type', 'other')
            section_types[section_type] = section_types.get(section_type, 0) + 1
            total_words += section.get('word_count', 0)
        
        return {
            'total_sections': len(sections),
            'section_types': section_types,
            'total_words': total_words,
            'average_words_per_section': total_words // len(sections) if sections else 0
        }

    # ===== 額外的相容性方法 (為了支援驗證測試) =====
    
    async def extract_metadata(self, tei_xml: str) -> Dict[str, Any]:
        """提取元數據 - 相容性方法"""
        try:
            root = ET.fromstring(tei_xml)
            return self._extract_metadata(root)
        except Exception as e:
            logger.error(f"提取元數據失敗: {e}")
            return {"error": str(e)}
    
    async def extract_sections(self, tei_xml: str) -> List[Dict[str, Any]]:
        """提取章節 - 相容性方法"""
        try:
            root = ET.fromstring(tei_xml)
            return self._extract_sections(root)
        except Exception as e:
            logger.error(f"提取章節失敗: {e}")
            return []
    
    def classify_section_type(self, title: str, content: str = "") -> str:
        """章節分類 - 相容性方法"""
        return self._classify_section_type(title)
    
    def extract_title_from_tei(self, tei_xml: str) -> str:
        """從TEI XML提取標題 - 相容性方法"""
        try:
            root = ET.fromstring(tei_xml)
            metadata = self._extract_metadata(root)
            return metadata.get('title', '')
        except Exception as e:
            logger.error(f"提取標題失敗: {e}")
            return ""
    
    def extract_authors_from_tei(self, tei_xml: str) -> List[Dict[str, Any]]:
        """從TEI XML提取作者 - 相容性方法"""
        try:
            root = ET.fromstring(tei_xml)
            metadata = self._extract_metadata(root)
            authors_list = metadata.get('authors', [])
            
            # 轉換為預期的格式
            return [{"full_name": author} for author in authors_list]
        except Exception as e:
            logger.error(f"提取作者失敗: {e}")
            return []
    
    def extract_sections_from_tei(self, tei_xml: str) -> List[Dict[str, Any]]:
        """從TEI XML提取章節 - 相容性方法"""
        try:
            root = ET.fromstring(tei_xml)
            return self._extract_sections(root)
        except Exception as e:
            logger.error(f"提取章節失敗: {e}")
            return []
    
    def extract_references_from_tei(self, tei_xml: str) -> List[Dict[str, Any]]:
        """從TEI XML提取參考文獻 - 相容性方法"""
        try:
            root = ET.fromstring(tei_xml)
            return self._extract_references(root)
        except Exception as e:
            logger.error(f"提取參考文獻失敗: {e}")
            return []

    async def parse_sections_from_xml(self, xml_string: str) -> List[Dict[str, Any]]:
        """從 TEI XML 字串中解析章節"""
        try:
            root = ET.fromstring(xml_string)
            ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
            
            sections = []
            
            # 處理正文內容
            body = root.find('.//tei:body', ns)
            if body is not None:
                for i, div in enumerate(body.findall('.//tei:div', ns)):
                    head = div.find('tei:head', ns)
                    title = head.text.strip() if head is not None and head.text else f"Untitled Section {i+1}"
                    
                    content_parts = []
                    for p in div.findall('.//tei:p', ns):
                        if p.text:
                            content_parts.append(p.text.strip())
                    
                    content = "\n".join(filter(None, content_parts))
                    
                    if content: # 只添加有內容的章節
                        sections.append({
                            "title": title,
                            "content": content,
                            "section_type": head.get("type", "unknown") if head is not None else "unknown",
                            "section_id": div.get('{http://www.w3.org/XML/1998/namespace}id', str(uuid.uuid4())),
                            "order": i,
                            "word_count": len(content.split())
                        })
            
            logger.info(f"從 XML 中成功解析出 {len(sections)} 個章節")
            return sections
            
        except ET.ParseError as e:
            logger.error(f"解析 TEI XML 失敗: {e}")
            return []
        except Exception as e:
            logger.error(f"從 XML 解析章節時發生未知錯誤: {e}")
            return []

# 建立服務實例
grobid_service = GrobidService() 