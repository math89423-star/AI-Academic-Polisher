# backend/utils/docx_service.py
import re

def is_paragraph_needs_polishing(para):
    """判定一个段落是否需要被润色"""
    text = para.text.strip()
    if len(text) < 15: # 过滤极短句、公式、图表编号
        return False
        
    style_name = para.style.name.lower()
    if 'heading' in style_name or 'toc' in style_name or 'title' in style_name:
        return False # 过滤标题、目录
        
    en_chars = len(re.findall(r'[a-zA-Z]', text))
    if len(text) > 0 and en_chars / len(text) > 0.8:
        return False # 过滤纯英文段落
        
    return True

def replace_paragraph_text(para, new_text):
    """保留段落格式的同时替换文本"""
    for run in para.runs:
        run.text = ""
    para.add_run(new_text)

def check_stop_signal(text):
    """检查是否到达文末的参考文献部分"""
    stop_keywords = ['参考文献', 'References']
    for kw in stop_keywords:
        if kw in text:
            return True
    return False