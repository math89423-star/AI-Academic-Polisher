"""
响应提取器

负责从AI响应中提取纯净的正文内容
"""
import re
from backend.services.ai_client import AIClient
from backend.services.prompt_builder import PromptBuilder
from backend.utils.logging_config import get_logger

logger = get_logger(__name__)


class ResponseExtractor:
    """响应提取器"""

    def __init__(self, ai_client: AIClient, prompt_builder: PromptBuilder):
        self.ai_client = ai_client
        self.prompt_builder = prompt_builder

    def extract_clean_text(self, raw_text: str) -> str:
        """
        从混合文本中提取纯净正文（同步版本）
        优化：先用正则提取，仅在正则失败时回退到 AI

        Args:
            raw_text: 原始混合文本

        Returns:
            str: 提取后的纯净正文
        """
        # 基础清洗：去除<think>标签
        basic_clean_text = re.sub(r'<think>.*?</think>', '', raw_text, flags=re.DOTALL | re.IGNORECASE).strip()

        # 正则提取：去除常见前缀和包裹
        cleaned = basic_clean_text
        cleaned = re.sub(r'^(润色结果|结果|输出|Output|Result)[:：]\s*', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'^```[\w]*\n', '', cleaned)
        cleaned = re.sub(r'\n```$', '', cleaned)
        cleaned = cleaned.strip()

        # 如果正则清洗后文本合理（长度 > 10 且不为空），直接返回
        if cleaned and len(cleaned) > 10:
            return cleaned

        # 降级：使用AI提取器进行二次提取
        try:
            extractor_prompt = self.prompt_builder.build_simple_extractor_prompt()
            messages = [
                {"role": "system", "content": extractor_prompt},
                {"role": "user", "content": basic_clean_text}
            ]

            response = self.ai_client.create_completion(
                messages=messages,
                temperature=0.1,
                stream=False
            )

            final_text = (response.choices[0].message.content or "").strip()

            if not final_text:
                logger.warning("提取器返回空值，启用降级保护，使用基础清洗文本")
                return basic_clean_text

            return final_text

        except Exception as e:
            logger.error(f"提取器失败: {str(e)}，使用基础清洗文本")
            return basic_clean_text

    def extract_clean_text_stream(self, raw_text: str):
        """
        从混合文本中提取纯净正文（流式版本）

        Args:
            raw_text: 原始混合文本

        Yields:
            str: 提取后的文本片段
        """
        extractor_prompt = self.prompt_builder.build_extractor_prompt()
        messages = [
            {"role": "system", "content": extractor_prompt},
            {"role": "user", "content": raw_text}
        ]

        try:
            stream = self.ai_client.create_completion(
                messages=messages,
                temperature=0.1,
                stream=True
            )

            has_yielded = False
            for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and hasattr(delta, 'content') and delta.content:
                    has_yielded = True
                    yield delta.content

            # 降级保护：如果提取器返回空，使用原始文本
            if not has_yielded:
                logger.warning("流式提取器返回空值，触发保底机制")
                yield raw_text

        except Exception as e:
            logger.error(f"流式提取器失败: {str(e)}，返回原始文本")
            yield raw_text
