from __future__ import annotations

from typing import Generator, Optional
from backend.services.ai_client import AIClient
from backend.services.prompt_builder import PromptBuilder, APIParameterGenerator
from backend.services.response_extractor import ResponseExtractor
from backend.services.retry_policy import RetryPolicy
from backend.prompts_config import STRATEGIES, load_continuation_prompt
from backend.utils.logging_config import get_logger

logger = get_logger(__name__)


class AIService:
    """AI服务（重构版）"""

    def __init__(self, api_key: str, base_url: str, model_name: str):
        """
        初始化AI服务

        Args:
            api_key: API密钥
            base_url: API基础URL
            model_name: 模型名称
        """
        self.ai_client = AIClient(api_key, base_url, model_name)
        self.prompt_builder = PromptBuilder(STRATEGIES)
        self.response_extractor = ResponseExtractor(self.ai_client, self.prompt_builder)
        self.retry_policy = RetryPolicy()
        self.param_generator = APIParameterGenerator()

    def generate_stream(self, text: str, mode: str = 'zh', strategy: str = 'standard', history_text: Optional[str] = None) -> Generator[str, None, None]:
        """
        流式生成润色内容（用于短文本）

        Args:
            text: 原始文本
            mode: 语言模式 (zh/en)
            strategy: 策略 (standard/strict)
            history_text: 历史文本（用于继续生成）

        Yields:
            str: 生成的文本片段
        """
        user_content = f"原文：\n{text}"
        continue_prompt = load_continuation_prompt()

        messages = [
            {"role": "system", "content": self.prompt_builder.build_prompt(mode, strategy)},
            {"role": "user", "content": user_content}
        ]

        if history_text:
            messages.extend([
                {"role": "assistant", "content": history_text},
                {"role": "user", "content": continue_prompt}
            ])

        # 获取动态参数
        api_params = self.param_generator.get_api_params(strategy)

        logger.info(f"开始流式生成 - 模型: {self.ai_client.model_name}, 参数: {api_params}")

        try:
            stream = self.ai_client.create_completion(
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

            logger.info("流式生成完成")

        except Exception as e:
            logger.error(f"流式生成失败: {str(e)}")
            yield f"【API 请求失败】: {str(e)}"

    def generate_sync(self, text: str, mode: str = 'zh', strategy: str = 'standard') -> str:
        """
        同步生成润色内容（用于并发切片）

        Args:
            text: 原始文本
            mode: 语言模式 (zh/en)
            strategy: 策略 (standard/strict)

        Returns:
            str: 润色后的文本
        """
        user_content = f"原文：\n{text}"
        messages = [
            {"role": "system", "content": self.prompt_builder.build_prompt(mode, strategy)},
            {"role": "user", "content": user_content}
        ]

        # 获取动态参数
        api_params = self.param_generator.get_api_params(strategy)

        def _request():
            response = self.ai_client.create_completion(
                messages=messages,
                temperature=api_params['temperature'],
                presence_penalty=api_params.get('presence_penalty', 0),
                frequency_penalty=api_params.get('frequency_penalty', 0),
                stream=False
            )
            return response.choices[0].message.content or ""

        # 使用重试策略执行请求
        try:
            raw_mixed_text = self.retry_policy.execute_with_retry(_request)
            logger.debug(f"原始输出预览: {raw_mixed_text[:100]}...")

            # 使用提取器提取纯净正文
            final_text = self.response_extractor.extract_clean_text(raw_mixed_text)

            return final_text

        except Exception as e:
            logger.error(f"同步生成失败: {str(e)}")
            raise
