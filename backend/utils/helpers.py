import re

def extract_title(text: str, length: int = 7) -> str:
    """提取文章正文的前N个字作为标题"""
    if not text: return "空白文稿"
    clean_text = "".join(text.split())
    return clean_text[:length] if clean_text else "空白文稿"

def split_text_into_chunks(text: str, max_chars: int = 600) -> list:
    """
    智能文本分片：按换行符和全角/半角句号进行安全切分，
    保证每个 chunk 长度贴近 max_chars，且不切断句子。
    """
    if not text:
        return []

    paragraphs = text.split('\n')
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # 如果当前累积的段落加上新段落不超标，直接合并
        if len(current_chunk) + len(para) <= max_chars:
            current_chunk += para + "\n"
        else:
            # 如果单段超级长，则按标点符号进一步切分
            sentences = re.split(r'([。！？.!?])', para)
            
            for i in range(0, len(sentences)-1, 2):
                sentence = sentences[i] + sentences[i+1] # 句子本体 + 标点
                if len(current_chunk) + len(sentence) > max_chars:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = sentence
                else:
                    current_chunk += sentence
            
            # 处理结尾没有标点的剩余部分
            if len(sentences) % 2 != 0 and sentences[-1]:
                last_part = sentences[-1]
                if len(current_chunk) + len(last_part) > max_chars:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = last_part
                else:
                    current_chunk += last_part
            
            current_chunk += "\n"

    # 装填尾部残余
    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks