# backend/utils/ai_service.py
import re
import time
from openai import OpenAI
from backend.prompts_config import STRATEGIES  # 🟢 直接引入 Python 字典

def remove_thinking_tags(text: str) -> str:
    if not text: return text
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE).strip()

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