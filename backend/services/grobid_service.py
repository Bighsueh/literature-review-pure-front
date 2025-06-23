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
import httpx
from .pdf_analyzer import pdf_analyzer

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
            # 使用更寬鬆的超時設定，並禁用SSL驗證以避免憑證問題
            timeout = aiohttp.ClientTimeout(total=15, connect=10)
            connector = aiohttp.TCPConnector(ssl=False, limit=10, limit_per_host=5)
            
            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                health_url = f"{self.base_url}/api/isalive"
                logger.info(f"正在檢查Grobid健康狀態: {health_url}")
                
                async with session.get(health_url) as response:
                    response_text = await response.text()
                    logger.info(f"Grobid健康檢查回應: 狀態={response.status}, 內容='{response_text}'")
                    
                    if response.status == 200:
                        # 檢查回應內容是否為預期的 "true"
                        if response_text.strip().lower() in ['true', 'ok', 'alive']:
                            logger.info("Grobid服務健康檢查通過")
                            return True
                        else:
                            logger.warning(f"Grobid服務回應異常內容: {response_text}")
                            return False
                    else:
                        logger.warning(f"Grobid服務健康檢查失敗，狀態碼: {response.status}")
                        return False
                        
        except aiohttp.ClientConnectorError as e:
            logger.error(f"Grobid服務連接失敗 (DNS/網路問題): {e}")
            return False
        except aiohttp.ServerTimeoutError as e:
            logger.error(f"Grobid服務健康檢查超時: {e}")
            return False
        except Exception as e:
            logger.error(f"Grobid服務健康檢查失敗: {type(e).__name__}: {e}")
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
            # 使用與健康檢查相同的連接器配置
            timeout = aiohttp.ClientTimeout(total=300, connect=10)
            connector = aiohttp.TCPConnector(ssl=False, limit=10, limit_per_host=5)
            
            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
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
                logger.info(f"呼叫Grobid API: {url}, 檔案大小: {len(pdf_content)} bytes")
                
                async with session.post(url, data=data) as response:
                    if response.status == 200:
                        tei_xml = await response.text()
                        logger.info(f"成功獲得TEI XML，長度: {len(tei_xml)} 字符")
                        return tei_xml
                    else:
                        error_text = await response.text()
                        logger.error(f"Grobid API呼叫失敗，狀態碼: {response.status}, 錯誤: {error_text[:500]}...")
                        return None
                        
        except aiohttp.ClientConnectorError as e:
            logger.error(f"Grobid API連接失敗 (DNS/網路問題): {e}")
            return None
        except aiohttp.ServerTimeoutError as e:
            logger.error(f"Grobid API呼叫超時: {e}")
            return None
        except asyncio.TimeoutError:
            logger.error("Grobid API呼叫超時")
            return None
        except Exception as e:
            logger.error(f"Grobid API呼叫異常: {type(e).__name__}: {e}")
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
        """提取頁碼資訊 - 實用版本"""
        try:
            # 方法1: 檢查元素本身的頁碼相關屬性
            for attr in ['page', 'n', 'facs']:
                if attr in element.attrib:
                    try:
                        page_num = int(element.get(attr))
                        logger.info(f"從屬性 '{attr}' 獲得頁碼 {page_num}")
                        return page_num
                    except (ValueError, TypeError):
                        pass
            
            # 方法2: 檢查座標資訊
            coords = element.get('coords')
            if coords:
                parts = coords.split(',')
                if len(parts) >= 5:
                    try:
                        page_num = int(parts[4])
                        logger.info(f"從座標獲得頁碼 {page_num}")
                        return page_num
                    except (ValueError, TypeError):
                        pass
            
            # 方法3: 基於章節順序的實用估算
            # 這是最可靠的方法，假設每頁包含約2-3個章節
            # 我們可以從外部傳入章節索引來計算
            return None  # 讓調用者處理估算
            
        except Exception as e:
            logger.info(f"頁碼提取異常: {e}")
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

    async def parse_sections_from_xml(self, xml_string: str, pdf_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """從 TEI XML 字串中解析章節 - 整合 PDF 分析版本"""
        try:
            root = ET.fromstring(xml_string)
            ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
            
            sections = []
            pdf_analysis = None
            
            # 如果提供了 PDF 路徑，進行 PDF 分析
            if pdf_path:
                try:
                    logger.info(f"開始 PDF 分析以獲取頁碼資訊: {pdf_path}")
                    pdf_analysis = await pdf_analyzer.analyze_pdf(pdf_path)
                    logger.info(f"PDF 分析完成，共 {pdf_analysis['total_pages']} 頁，{len(pdf_analysis['text_blocks'])} 個文本塊")
                except Exception as e:
                    logger.warning(f"PDF 分析失敗，將使用估算方法: {e}")
                    pdf_analysis = None
            
            # 使用完整的章節提取邏輯
            # 查找所有章節 div 元素
            div_elems = root.findall('.//tei:text//tei:div', ns)
            
            logger.info(f"找到 {len(div_elems)} 個章節 div 元素")
            
            for i, div in enumerate(div_elems):
                section = {}
                
                # 提取章節標題
                head_elem = div.find('./tei:head', ns)
                if head_elem is not None and head_elem.text:
                    title = self._clean_text(head_elem.text)
                else:
                    title = f"Section {i+1}"
                
                # 提取章節內容
                content_parts = []
                for p_elem in div.findall('.//tei:p', ns):
                    if p_elem.text:
                        content_parts.append(self._clean_text(p_elem.text))
                
                content = " ".join(content_parts).strip()
                
                if content:  # 只添加有內容的章節
                    # 使用完整的章節類型分類
                    section_type = self._classify_section_type(title)
                    
                    # 提取頁碼資訊 - 整合 PDF 分析
                    page_num = await self._extract_page_info_with_pdf(
                        div, title, content, i, len(div_elems), pdf_analysis
                    )
                    
                    logger.info(f"章節 '{title}' 頁碼提取結果: {page_num}")
                    
                    # 構建完整的章節資訊
                    section_data = {
                        "title": title,
                        "content": content,
                        "section_type": section_type,  # 修復：使用正確的分類方法
                        "page_num": page_num,          # 修復：添加頁碼資訊
                        "section_id": div.get('{http://www.w3.org/XML/1998/namespace}id', str(uuid.uuid4())),
                        "order": i + 1,                # 修復：從1開始計數
                        "word_count": len(content.split()),
                        "section_order": i + 1         # 添加相容性欄位
                    }
                    
                    sections.append(section_data)
                    logger.info(f"章節 {i+1}: '{title}' -> 類型: {section_type}, 頁碼: {page_num}, 字數: {section_data['word_count']}")
            
            logger.info(f"從 XML 中成功解析出 {len(sections)} 個有效章節")
            return sections
            
        except Exception as e:
            logger.error(f"解析 TEI XML 失敗: {e}", exc_info=True)
            return []

    async def _extract_page_info_with_pdf(
        self, 
        element: ET.Element, 
        title: str, 
        content: str, 
        section_index: int, 
        total_sections: int, 
        pdf_analysis: Optional[Dict[str, Any]]
    ) -> int:
        """
        整合 PDF 分析的頁碼提取方法
        
        Args:
            element: TEI XML 元素
            title: 章節標題
            content: 章節內容
            section_index: 章節索引
            total_sections: 總章節數
            pdf_analysis: PDF 分析結果
            
        Returns:
            頁碼
        """
        try:
            # 方法1: 從 TEI XML 元素提取（原有方法）
            page_num = self._extract_page_info(element)
            if page_num and page_num > 0:
                logger.info(f"從 TEI XML 獲得頁碼: {page_num}")
                return page_num
            
            # 方法2: 使用 PDF 分析進行文本匹配
            if pdf_analysis and pdf_analysis.get('text_blocks'):
                # 嘗試標題匹配
                title_page = pdf_analyzer.find_text_page(title, pdf_analysis['text_blocks'])
                if title_page:
                    logger.info(f"通過標題匹配獲得頁碼: {title_page}")
                    return title_page
                
                # 嘗試內容匹配（使用內容的前100個字符）
                content_sample = content[:100] if len(content) > 100 else content
                content_page = pdf_analyzer.find_text_page(content_sample, pdf_analysis['text_blocks'])
                if content_page:
                    logger.info(f"通過內容匹配獲得頁碼: {content_page}")
                    return content_page
            
            # 方法3: 基於 PDF 總頁數的智能估算
            if pdf_analysis and pdf_analysis.get('total_pages'):
                estimated_page = pdf_analyzer.estimate_page_from_position(
                    section_index, total_sections, pdf_analysis['total_pages']
                )
                logger.info(f"基於 PDF 總頁數估算頁碼: {estimated_page}")
                return estimated_page
            
            # 方法4: 基於章節順序的簡單估算（備用方案）
            estimated_page = max(1, (section_index // 2) + 1)
            logger.info(f"使用簡單順序估算頁碼: {estimated_page}")
            return estimated_page
            
        except Exception as e:
            logger.error(f"頁碼提取失敗: {e}")
            return max(1, (section_index // 2) + 1)  # 備用方案

# 建立服務實例
grobid_service = GrobidService() 