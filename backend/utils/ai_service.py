import re
import time
import random
from openai import OpenAI
import sys

# 自定义headers绕过反爬机制
def get_custom_headers():
    """返回自定义headers用于绕过反爬"""
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://chat.openai.com/",
        "Origin": "https://chat.openai.com"
    }

def get_prompt_by_mode(mode: str, strategy_key: str = 'standard') -> str:
    from backend.prompts_config import STRATEGIES
    strategy = STRATEGIES.get(strategy_key) or STRATEGIES.get('standard') or {}

    fallback_prompt = "你是一个专业的学术润色系统，请对原文进行润色改写。"
    prompt = strategy.get("en_prompt" if mode == 'en' else "zh_prompt", fallback_prompt)
    if isinstance(prompt, list): prompt = "\n".join(prompt)

    hard_constraint = "\n\n【指令】：你可以进行思考和步骤拆解，但请务必在最后提供完整合并的润色正文。"
    return prompt + hard_constraint

def get_dynamic_temperature() -> float:
    """动态生成 temperature 参数，范围 0.85-0.95"""
    return round(random.uniform(0.85, 0.95), 2)

def get_api_params(strategy: str = 'standard') -> dict:
    """
    根据策略返回 API 调用参数

    Args:
        strategy: 策略类型 ('standard' 或 'strict')

    Returns:
        dict: 包含 temperature, presence_penalty, frequency_penalty 等参数
    """
    base_params = {
        'temperature': get_dynamic_temperature(),
    }

    if strategy == 'strict':
        # 极致降重模式：更高的随机性和惩罚参数
        base_params['temperature'] = round(random.uniform(0.90, 0.98), 2)
        base_params['presence_penalty'] = 0.6
        base_params['frequency_penalty'] = 0.7
    else:
        # 标准模式：适中的惩罚参数
        base_params['presence_penalty'] = 0.3
        base_params['frequency_penalty'] = 0.4

    return base_params

def extract_clean_text_stream(raw_text: str, api_key: str, base_url: str, model_name: str):
    client = OpenAI(api_key=api_key, base_url=base_url, default_headers=get_custom_headers())
    extractor_prompt = """你是一个无情的文本提取器。
用户会输入包含“思考过程”、“分析步骤”以及“最终润色正文”的混合文本。
你的【唯一任务】：提取出最终合并好的润色正文部分，并直接输出。
【绝对禁止】：不要输出任何前缀（如“正文如下”、“润色正文：”），不要输出原有的思考步骤，不要输出任何寒暄。只输出纯净的正文段落！"""

    messages = [{"role": "system", "content": extractor_prompt}, {"role": "user", "content": raw_text}]
    
    stream = client.chat.completions.create(model=model_name, messages=messages, temperature=0.1, stream=True)
    
    has_yielded = False
    for chunk in stream:
        delta = chunk.choices[0].delta if chunk.choices else None
        if delta and hasattr(delta, 'content') and delta.content:
            has_yielded = True
            yield delta.content
            
    # 🟢 致命 Bug 修复：如果提取器因为过于严苛而返回了空字符串，立刻启用原始清洗文本兜底！
    if not has_yielded:
        print("\n⚠️ [警告] 提取器返回空值！触发保底机制，直接放行基础清洗后的文本。")
        yield raw_text

def pure_ai_generator(text: str, api_key: str, base_url: str, model_name: str, mode: str = 'zh', strategy: str = 'standard', history_text: str = None):
    client = OpenAI(api_key=api_key, base_url=base_url, default_headers=get_custom_headers())
    user_content = f"原文：\n{text}"
    continue_prompt = "由于任务中断，请继续润色。注意：直接输出，不要重复，不要寒暄解释。"

    messages = [{"role": "system", "content": get_prompt_by_mode(mode, strategy)}, {"role": "user", "content": user_content}]
    if history_text:
        messages.extend([{"role": "assistant", "content": history_text}, {"role": "user", "content": continue_prompt}])

    # 获取动态参数
    api_params = get_api_params(strategy)

    print(f"\n🚀 [{model_name}] 直接流式输出（无二次提取）...")
    print(f"📊 API 参数: temperature={api_params['temperature']}, presence_penalty={api_params.get('presence_penalty', 0)}, frequency_penalty={api_params.get('frequency_penalty', 0)}")

    try:
        stream = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=api_params['temperature'],
            presence_penalty=api_params.get('presence_penalty', 0),
            frequency_penalty=api_params.get('frequency_penalty', 0),
            stream=True
        )

        for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and hasattr(delta, 'content') and delta.content:
                yield delta.content

    except Exception as e:
        yield f"【API 请求失败】: {str(e)}"
        return

    print("✅ [短文本任务] 流式推送完毕！")

def sync_ai_request(text: str, api_key: str, base_url: str, model_name: str, mode: str = 'zh', strategy: str = 'standard', max_retries=3) -> str:
    client = OpenAI(api_key=api_key, base_url=base_url, default_headers=get_custom_headers())
    user_content = f"原文：\n{text}"
    messages = [{"role": "system", "content": get_prompt_by_mode(mode, strategy)}, {"role": "user", "content": user_content}]

    # 获取动态参数
    api_params = get_api_params(strategy)

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=api_params['temperature'],
                presence_penalty=api_params.get('presence_penalty', 0),
                frequency_penalty=api_params.get('frequency_penalty', 0),
                stream=False
            )
            raw_mixed_text = response.choices[0].message.content or ""

            # 🟢 增加后台日志：打印并发片段的原始输出
            print(f"\n[并发片段尝试 {attempt+1}] 原始输出预览 (前100字): {raw_mixed_text[:100].replace(chr(10), ' ')}...")

            basic_clean_text = re.sub(r'<think>.*?</think>', '', raw_mixed_text, flags=re.DOTALL | re.IGNORECASE).strip()

            extractor_prompt = "提取出以下文本中真正的最终改写正文，去除所有分析、思考步骤和引导前缀。直接输出正文本身："
            extract_messages = [{"role": "system", "content": extractor_prompt}, {"role": "user", "content": basic_clean_text}]

            clean_response = client.chat.completions.create(model=model_name, messages=extract_messages, temperature=0.1, stream=False)
            final_text = (clean_response.choices[0].message.content or "").strip()

            # 🟢 致命 Bug 修复：并发环境提取器失误时触发降级保护
            if not final_text:
                print(f"⚠️ [并发片段警告] 提取器返回为空，启用降级保护，使用基础清洗文本！")
                return basic_clean_text

            return final_text

        except Exception as e:
            print(f"❌ [并发任务报错]: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise e