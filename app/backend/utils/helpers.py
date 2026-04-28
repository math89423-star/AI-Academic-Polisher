import re

def extract_title(text: str, length: int = 7) -> str:
    """提取文章正文的前N个字作为标题"""
    if not text: return "空白文稿"
    clean_text = "".join(text.split())
    return clean_text[:length] if clean_text else "空白文稿"

def split_text_into_chunks(text: str, max_chars: int = 1500) -> list:
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

        if len(current_chunk) + len(para) <= max_chars:
            current_chunk += para + "\n"
        else:
            sentences = re.split(r'([。！？.!?])', para)

            for i in range(0, len(sentences)-1, 2):
                sentence = sentences[i] + sentences[i+1]
                if len(sentence) > max_chars:
                    for j in range(0, len(sentence), max_chars):
                        part = sentence[j:j+max_chars]
                        if len(current_chunk) + len(part) > max_chars:
                            if current_chunk:
                                chunks.append(current_chunk.strip())
                            current_chunk = part
                        else:
                            current_chunk += part
                elif len(current_chunk) + len(sentence) > max_chars:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = sentence
                else:
                    current_chunk += sentence

            if len(sentences) % 2 != 0 and sentences[-1]:
                last_part = sentences[-1]
                if len(last_part) > max_chars:
                    for j in range(0, len(last_part), max_chars):
                        part = last_part[j:j+max_chars]
                        if len(current_chunk) + len(part) > max_chars:
                            if current_chunk:
                                chunks.append(current_chunk.strip())
                            current_chunk = part
                        else:
                            current_chunk += part
                elif len(current_chunk) + len(last_part) > max_chars:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = last_part
                else:
                    current_chunk += last_part

            current_chunk += "\n"

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    # 尾块合并：最后一块太短时并入倒数第二块，避免碎片单独走一次 AI 调用
    if len(chunks) >= 2 and len(chunks[-1]) < max_chars * 0.3:
        chunks[-2] = chunks[-2] + "\n" + chunks[-1]
        chunks.pop()

    return chunks