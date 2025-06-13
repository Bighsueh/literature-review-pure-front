#!/usr/bin/env python3
"""
分析 TEI XML 中的頁碼資訊格式
"""
import asyncio
import xml.etree.ElementTree as ET
import re
from backend.core.database import AsyncSessionLocal
from backend.services.db_service import db_service

PAPER_ID = "7bd19181-b596-4cd1-891a-4a8d50b852f9"

async def analyze_tei_xml():
    print("🔍 分析 TEI XML 中的頁碼資訊")
    print("=" * 50)
    
    session = AsyncSessionLocal()
    try:
        # 獲取 TEI XML
        paper = await db_service.get_paper_by_id(session, PAPER_ID)
        if not paper or not paper.tei_xml:
            print("❌ 無法獲取 TEI XML")
            return
        
        tei_xml = paper.tei_xml
        print(f"📄 TEI XML 長度: {len(tei_xml)} 字符")
        
        # 解析 XML
        try:
            root = ET.fromstring(tei_xml)
            ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
            
            print("\n🔍 分析 XML 結構:")
            
            # 1. 檢查是否有 pb (page break) 元素
            pb_elements = root.findall('.//tei:pb', ns)
            print(f"   📖 找到 {len(pb_elements)} 個 <pb> (page break) 元素")
            
            if pb_elements:
                print("   📋 前5個 pb 元素的屬性:")
                for i, pb in enumerate(pb_elements[:5]):
                    attrs = pb.attrib
                    print(f"      {i+1}. {attrs}")
            
            # 2. 檢查 div 元素的屬性
            div_elements = root.findall('.//tei:text//tei:div', ns)
            print(f"   📑 找到 {len(div_elements)} 個 div 元素")
            
            print("   📋 前5個 div 元素的屬性:")
            for i, div in enumerate(div_elements[:5]):
                attrs = div.attrib
                print(f"      {i+1}. {attrs}")
                
                # 檢查 div 內是否有 pb 元素
                pb_in_div = div.findall('.//tei:pb', ns)
                if pb_in_div:
                    print(f"         └─ 包含 {len(pb_in_div)} 個 pb 元素")
            
            # 3. 檢查是否有 coords 屬性
            coords_elements = []
            for elem in root.iter():
                if 'coords' in elem.attrib:
                    coords_elements.append(elem)
            
            print(f"   🎯 找到 {len(coords_elements)} 個有 coords 屬性的元素")
            
            if coords_elements:
                print("   📋 前5個 coords 屬性:")
                for i, elem in enumerate(coords_elements[:5]):
                    coords = elem.get('coords')
                    tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                    print(f"      {i+1}. <{tag}> coords=\"{coords}\"")
            
            # 4. 檢查是否有其他頁碼相關屬性
            page_attrs = ['page', 'n', 'facs']
            for attr in page_attrs:
                elements_with_attr = []
                for elem in root.iter():
                    if attr in elem.attrib:
                        elements_with_attr.append(elem)
                
                if elements_with_attr:
                    print(f"   📄 找到 {len(elements_with_attr)} 個有 '{attr}' 屬性的元素")
                    for i, elem in enumerate(elements_with_attr[:3]):
                        value = elem.get(attr)
                        tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                        print(f"      {i+1}. <{tag}> {attr}=\"{value}\"")
            
            # 5. 檢查文字內容中是否有頁碼模式
            text_content = ''.join(root.itertext())
            page_patterns = [
                r'Page\s+(\d+)',
                r'p\.\s*(\d+)',
                r'\[(\d+)\]',
                r'(\d+)\s*$'  # 行末數字
            ]
            
            print("\n🔍 檢查文字內容中的頁碼模式:")
            for pattern in page_patterns:
                matches = re.findall(pattern, text_content[:5000])  # 只檢查前5000字符
                if matches:
                    print(f"   📄 模式 '{pattern}': 找到 {len(matches)} 個匹配")
                    print(f"      前5個: {matches[:5]}")
            
        except ET.ParseError as e:
            print(f"❌ XML 解析失敗: {e}")
            
    except Exception as e:
        print(f"❌ 分析失敗: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(analyze_tei_xml()) 