# backend/utils/ai_service.py
import re
import time
from openai import OpenAI
from backend.prompts_config import STRATEGIES 

def remove_thinking_tags(text: str) -> str:
    """终极文本净化器：带防丢段落的安全兜底"""
    if not text: 
        return ""
    
    # 备份原始文本，防止被误杀干净
    original_backup = text 
    
    # 1. 常规清理：去除 <think> ... </think>
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    output_markers = [
        r'\*\*Final Output Generation\*\*',
        r'\*\*Final Polish Check:\*\*',
        r'\*Draft \d+ Polish:\*',
        r'\(End of Thought Process\)',
        r'I will now generate the response\.'
    ]
    
    for marker in output_markers:
        match = re.search(marker, text, flags=re.IGNORECASE)
        if match:
            text = text[match.end():]
            
    text = re.sub(r'^\s*\*\s*\*Draft.*?:\*\s*', '', text, flags=re.MULTILINE)
    cleaned_text = text.strip()
    
    # 如果在清洗后文本离奇消失（长度极短或为空），
    # 说明触发了严重误杀，立即回滚到只去除了 <think> 标签的版本！
    if len(cleaned_text) < 5: 
        safe_text = re.sub(r'<think>.*?</think>', '', original_backup, flags=re.DOTALL | re.IGNORECASE)
        return safe_text.strip()
        
    return cleaned_text


def get_prompt_by_mode(mode: str, strategy_key: str = 'standard') -> str:
    # 动态获取策略，如果找不到则回退到 standard
    strategy = STRATEGIES.get(strategy_key) or STRATEGIES.get('standard') or {}
    
    fallback_prompt = "你是一个专业的学术润色系统，请直接输出润色后的正文，不要任何寒暄。"
    prompt_key = "en_prompt" if mode == 'en' else "zh_prompt"
    
    return strategy.get(prompt_key, fallback_prompt)

def pure_ai_generator(text: str, api_key: str, base_url: str, model_name: str, mode: str = 'zh', strategy: str = 'standard', history_text: str = None):
    client = OpenAI(api_key=api_key, base_url=base_url)
    messages = [
        {"role": "system", "content": get_prompt_by_mode(mode, strategy)},
        {"role": "user", "content": f"原文：\n{text}"}
    ]
    if history_text:
        messages.append({"role": "assistant", "content": history_text})
        messages.append({"role": "user", "content": "由于刚才任务中断，请紧接上文，继续润色剩余的原文。注意：直接输出接下来的润色正文，绝对不要重复刚才已经输出过的部分，也不要任何寒暄解释。"})

    stream = client.chat.completions.create(model=model_name, messages=messages, temperature=0.7, stream=True)
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content

def sync_ai_request(text: str, api_key: str, base_url: str, model_name: str, mode: str = 'zh', strategy: str = 'standard', max_retries=4) -> str:
    client = OpenAI(api_key=api_key, base_url=base_url)
    messages = [
        {"role": "system", "content": get_prompt_by_mode(mode, strategy)},
        {"role": "user", "content": text}
    ]
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(model=model_name, messages=messages, temperature=0.7, stream=False)
            return response.choices[0].message.content or ""
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt) 
                continue
            raise e