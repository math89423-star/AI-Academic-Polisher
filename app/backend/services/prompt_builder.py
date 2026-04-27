"""
提示词构建器

负责根据模式和策略构建提示词
"""
import random


class PromptBuilder:
    """提示词构建器"""

    def __init__(self, strategies_config: dict):
        """
        初始化提示词构建器

        Args:
            strategies_config: 策略配置字典（来自prompts_config.STRATEGIES）
        """
        self.strategies = strategies_config

    def build_prompt(self, mode: str, strategy_key: str = 'standard') -> str:
        """
        构建提示词

        Args:
            mode: 语言模式 (zh/en)
            strategy_key: 策略键 (standard/strict)

        Returns:
            str: 完整的提示词
        """
        strategy = self.strategies.get(strategy_key) or self.strategies.get('standard') or {}

        fallback_prompt = "你是一个专业的学术润色系统，请对原文进行润色改写。"
        prompt = strategy.get("en_prompt" if mode == 'en' else "zh_prompt", fallback_prompt)

        # 如果提示词是列表，合并为字符串
        if isinstance(prompt, list):
            prompt = "\n".join(prompt)

        # 添加硬约束
        hard_constraint = "\n\n【指令】：你可以进行思考和步骤拆解，但请务必在最后提供完整合并的润色正文。"
        return prompt + hard_constraint

    def build_extractor_prompt(self) -> str:
        """
        构建提取器提示词

        Returns:
            str: 提取器提示词
        """
        return """你是一个无情的文本提取器。
用户会输入包含"思考过程"、"分析步骤"以及"最终润色正文"的混合文本。
你的【唯一任务】：提取出最终合并好的润色正文部分，并直接输出。
【绝对禁止】：不要输出任何前缀（如"正文如下"、"润色正文："），不要输出原有的思考步骤，不要输出任何寒暄。只输出纯净的正文段落！"""

    def build_simple_extractor_prompt(self) -> str:
        """
        构建简单提取器提示词

        Returns:
            str: 简单提取器提示词
        """
        return "提取出以下文本中真正的最终改写正文，去除所有分析、思考步骤和引导前缀。直接输出正文本身："


class APIParameterGenerator:
    """API参数生成器"""

    @staticmethod
    def get_dynamic_temperature(strategy: str = 'standard') -> float:
        """
        动态生成temperature参数

        Args:
            strategy: 策略类型 (standard/strict)

        Returns:
            float: temperature值
        """
        if strategy == 'strict':
            return round(random.uniform(0.90, 0.98), 2)
        else:
            return round(random.uniform(0.85, 0.95), 2)

    @staticmethod
    def get_api_params(strategy: str = 'standard') -> dict:
        """
        根据策略返回API调用参数

        Args:
            strategy: 策略类型 (standard/strict)

        Returns:
            dict: 包含temperature, presence_penalty, frequency_penalty等参数
        """
        base_params = {
            'temperature': APIParameterGenerator.get_dynamic_temperature(strategy),
        }

        if strategy == 'strict':
            # 极致降重模式：更高的随机性和惩罚参数
            base_params['presence_penalty'] = 0.6
            base_params['frequency_penalty'] = 0.7
        else:
            # 标准模式：适中的惩罚参数
            base_params['presence_penalty'] = 0.3
            base_params['frequency_penalty'] = 0.4

        return base_params
