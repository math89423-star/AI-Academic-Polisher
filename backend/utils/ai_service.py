import re

def clean_ai_text(text):
    if not text: return ""
    
    # 1. 过滤标准 <think> 标签块及其内部所有内容
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'```.*?<think>.*?</think>.*?```', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # 2. 精准狙击代理商的固定废话
    text = re.sub(r'(?:<think>|think|\[think\])?\s*这其实是我思考的过程.*?不再将其展示出来了[。.]?\s*', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # 3. 强力劈分刀，提取正文
    split_keywords = [
        "润色正文：", "润色正文:", "润色结果：", "润色结果:", 
        "修改后的文本：", "修改后的文本:", "正文：", "正文:"
    ]
    for kw in split_keywords:
        if kw in text:
            text = text.split(kw)[-1]
            break
            
    # 4. 去除多余的聊天前缀
    text = re.sub(r'^(?:好的，|没问题，|这是|以下是|那么).*?(?:正文|结果|如下)[：:\s]*', '', text, flags=re.IGNORECASE)
    
    # 5. 清理残留的破损标签符号
    text = re.sub(r'^</?think>\s*', '', text, flags=re.IGNORECASE)
    
    # 6. 🟢 采纳你的建议：如果 "think" (忽略大小写) 孤单地占据了首行，直接干掉！
    # 完美避开 "Think about it" 的误杀，因为正常的句子不可能只有一个词且独自占一行。
    text = re.sub(r'^think\s*[\r\n]+', '', text, flags=re.IGNORECASE)
    
    return text.strip()

def get_prompt_by_mode(mode: str, strategy_key: str = 'standard') -> str:
    from backend.prompts_config import STRATEGIES 
    strategy = STRATEGIES.get(strategy_key) or STRATEGIES.get('standard') or {}
    
    fallback_prompt = "你是一个专业的学术润色系统，请直接输出润色后的正文，绝对不要输出任何寒暄或你的思考过程。"
    prompt = strategy.get("en_prompt" if mode == 'en' else "zh_prompt", fallback_prompt)
    if isinstance(prompt, list): prompt = "\n".join(prompt)
        
    hard_constraint = "\n\n【系统最高强制指令】：禁止输出任何形式的“思考过程”、“推理逻辑”或“寒暄”。请直接、立刻输出最终润色好的正文！绝对不要包含类似‘润色正文：’这样的前缀引导词！"
    return prompt + hard_constraint

def pure_ai_generator(text: str, api_key: str, base_url: str, model_name: str, mode: str = 'zh', strategy: str = 'standard', history_text: str = None):
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url=base_url)
    
    user_content = f"原文：\n{text}"
    continue_prompt = "由于任务中断，请继续润色。注意：直接输出，不要重复，不要寒暄解释。"

    messages = [{"role": "system", "content": get_prompt_by_mode(mode, strategy)}, {"role": "user", "content": user_content}]
    if history_text:
        messages.extend([{"role": "assistant", "content": history_text}, {"role": "user", "content": continue_prompt}])

    stream = client.chat.completions.create(model=model_name, messages=messages, temperature=0.7, stream=True)
    
    buffer = ""
    in_think_tag = False
    is_initial_buffering = True

    for chunk in stream:
        delta = chunk.choices[0].delta if chunk.choices else None
        if not delta: continue
        content = getattr(delta, 'content', '')
        if not content: continue
        
        buffer += content

        # 全局屏蔽规范的 <think> 标签流
        if not in_think_tag:
            if '<think>' in buffer.lower():
                idx = buffer.lower().find('<think>')
                if idx > 0: yield buffer[:idx]
                buffer = buffer[idx+7:]
                in_think_tag = True
                continue
        else:
            if '</think>' in buffer.lower():
                idx = buffer.lower().find('</think>')
                buffer = buffer[idx+8:]
                in_think_tag = False
            else:
                if len(buffer) > 10: buffer = buffer[-10:]
            continue

        # 智能缓冲池
        if is_initial_buffering:
            # 强制憋住前 80 个字符，防止碎渣漏到前端
            if len(buffer) < 80:
                continue
            
            is_initial_buffering = False
            clean_buf = clean_ai_text(buffer)
            if clean_buf: 
                yield clean_buf
            buffer = ""
            continue
            
        yield buffer
        buffer = ""

    # 处理不足 80 字的极短文本收尾 (像 Hello 这种短句最终会进入这里)
    if buffer and not in_think_tag:
        yield clean_ai_text(buffer)

def sync_ai_request(text: str, api_key: str, base_url: str, model_name: str, mode: str = 'zh', strategy: str = 'standard', max_retries=4) -> str:
    from openai import OpenAI
    import time
    client = OpenAI(api_key=api_key, base_url=base_url)
    
    user_content = f"原文：\n{text}"
    messages = [{"role": "system", "content": get_prompt_by_mode(mode, strategy)}, {"role": "user", "content": user_content}]
    
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(model=model_name, messages=messages, temperature=0.7, stream=False)
            return clean_ai_text(response.choices[0].message.content or "")
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt) 
                continue
            raise e