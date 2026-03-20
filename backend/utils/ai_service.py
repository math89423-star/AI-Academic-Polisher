import re
from openai import OpenAI
import time

def get_prompt_by_mode(mode: str, strategy_key: str = 'standard') -> str:
    from backend.prompts_config import STRATEGIES 
    strategy = STRATEGIES.get(strategy_key) or STRATEGIES.get('standard') or {}
    
    fallback_prompt = "你是一个专业的学术润色系统，请对原文进行润色改写。"
    prompt = strategy.get("en_prompt" if mode == 'en' else "zh_prompt", fallback_prompt)
    if isinstance(prompt, list): prompt = "\n".join(prompt)
    
    # 第一遍生成时，允许它思考，但要求它给出明确的正文
    hard_constraint = "\n\n【指令】：你可以进行思考和步骤拆解，但请务必在最后提供完整合并的润色正文。"
    return prompt + hard_constraint

def extract_clean_text_stream(raw_text: str, api_key: str, base_url: str, model_name: str):
    """
    第二遍：提取器（流式输出）
    使用极严苛的 System Prompt，剥离所有思考过程，只流式输出正文
    """
    client = OpenAI(api_key=api_key, base_url=base_url)
    
    extractor_prompt = """你是一个无情的文本提取器。
用户会输入包含“思考过程”、“分析步骤”以及“最终润色正文”的混合文本。
你的【唯一任务】：提取出最终合并好的润色正文部分，并直接输出。
【绝对禁止】：不要输出任何前缀（如“正文如下”、“润色正文：”），不要输出原有的思考步骤，不要输出任何寒暄。只输出纯净的正文段落！"""

    messages = [
        {"role": "system", "content": extractor_prompt},
        {"role": "user", "content": raw_text}
    ]
    
    # 提取过程使用较低的 temperature 保证稳定性，并开启流式输出推给前端
    stream = client.chat.completions.create(
        model=model_name, 
        messages=messages, 
        temperature=0.1, 
        stream=True
    )
    
    for chunk in stream:
        delta = chunk.choices[0].delta if chunk.choices else None
        if delta and hasattr(delta, 'content') and delta.content:
            yield delta.content

def pure_ai_generator(text: str, api_key: str, base_url: str, model_name: str, mode: str = 'zh', strategy: str = 'standard', history_text: str = None):
    """
    短文本流式入口：采用 Two-Pass 机制
    """
    client = OpenAI(api_key=api_key, base_url=base_url)
    
    user_content = f"原文：\n{text}"
    continue_prompt = "由于任务中断，请继续润色。注意：直接输出，不要重复，不要寒暄解释。"

    messages = [{"role": "system", "content": get_prompt_by_mode(mode, strategy)}, {"role": "user", "content": user_content}]
    if history_text:
        messages.extend([{"role": "assistant", "content": history_text}, {"role": "user", "content": continue_prompt}])

    # 第一遍：静默生成（非流式），允许模型尽情思考
    try:
        response = client.chat.completions.create(
            model=model_name, 
            messages=messages, 
            temperature=0.7, 
            stream=False
        )
        raw_mixed_text = response.choices[0].message.content or ""
    except Exception as e:
        yield f"【API 请求失败】: {str(e)}"
        return

    # 简单过滤一下标准的 <think> 标签以减轻提取器的压力
    raw_mixed_text = re.sub(r'<think>.*?</think>', '', raw_mixed_text, flags=re.DOTALL | re.IGNORECASE)

    # 第二遍：将生成的混合文本交给提取器，把纯净正文流式推给前端
    generator = extract_clean_text_stream(raw_mixed_text, api_key, base_url, model_name)
    for clean_chunk in generator:
        yield clean_chunk

def sync_ai_request(text: str, api_key: str, base_url: str, model_name: str, mode: str = 'zh', strategy: str = 'standard', max_retries=3) -> str:
    """
    长文本/Word文档 并发请求入口：采用 Two-Pass 机制
    """
    client = OpenAI(api_key=api_key, base_url=base_url)
    
    user_content = f"原文：\n{text}"
    messages = [{"role": "system", "content": get_prompt_by_mode(mode, strategy)}, {"role": "user", "content": user_content}]
    
    for attempt in range(max_retries):
        try:
            # 第一遍：获取完整混合文本
            response = client.chat.completions.create(model=model_name, messages=messages, temperature=0.7, stream=False)
            raw_mixed_text = response.choices[0].message.content or ""
            
            # 去除标准标签
            raw_mixed_text = re.sub(r'<think>.*?</think>', '', raw_mixed_text, flags=re.DOTALL | re.IGNORECASE)
            
            # 第二遍：非流式提取纯净文本
            extractor_prompt = "提取出以下文本中真正的最终改写正文，去除所有分析、思考步骤和引导前缀。直接输出正文本身："
            extract_messages = [
                {"role": "system", "content": extractor_prompt},
                {"role": "user", "content": raw_mixed_text}
            ]
            clean_response = client.chat.completions.create(
                model=model_name, 
                messages=extract_messages, 
                temperature=0.1, 
                stream=False
            )
            
            return (clean_response.choices[0].message.content or "").strip()
            
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt) 
                continue
            raise e