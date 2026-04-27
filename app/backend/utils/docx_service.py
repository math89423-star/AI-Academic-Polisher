# backend/utils/docx_service.py
from __future__ import annotations

import re
from docx.text.paragraph import Paragraph


def is_paragraph_needs_polishing(para: Paragraph, mode: str = 'zh') -> bool:
    """判定一个段落是否需要被润色"""
    xml_str = para._element.xml
    if '<w:drawing' in xml_str or '<v:shape' in xml_str or '<w:pict' in xml_str:
        return False
        
    text = para.text.strip()
    
    # 过滤极短句、公式、图表编号
    if len(text) < 15: 
        return False
        
    style_name = para.style.name.lower()
    if any(keyword in style_name for keyword in ['heading', 'toc', 'title', 'caption', 'bibliography']):
        return False 
        
    # 根据选择的模式，进行双向语言隔离！
    if mode == 'zh':
        # 1. 中文润色模式：如果英文字母占比超过 80%，判定为英文段落，跳过
        en_chars = len(re.findall(r'[a-zA-Z]', text))
        if len(text) > 0 and (en_chars / len(text)) > 0.8:
            return False 
            
    elif mode == 'en':
        # 2. 英文润色模式：如果中文字符占比超过 40%，判定为中文段落，跳过
        # \u4e00-\u9fa5 是标准汉字的 Unicode 编码范围
        zh_chars = len(re.findall(r'[\u4e00-\u9fa5]', text))
        if len(text) > 0 and (zh_chars / len(text)) > 0.4:
            return False 
        
    return True

def replace_paragraph_text(para: Paragraph, new_text: str) -> None:
    for run in para.runs:
        run.text = ""
    para.add_run(new_text)

def check_stop_signal(text: str) -> bool:
    stop_keywords = ['参考文献', 'References', '致谢', 'Acknowledgements']
    for kw in stop_keywords:
        if kw in text:
            return True
    return False