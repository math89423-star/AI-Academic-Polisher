"""
提示词构建器

负责根据模式和策略构建提示词，从外部 md 文件加载
"""
import random
from backend.prompts_config import (
    load_strategy_prompt,
    load_extractor_prompt,
    load_simple_extractor_prompt,
)


class PromptBuilder:
    """提示词构建器"""

    def __init__(self, strategies_config: dict):
        self.strategies = strategies_config

    def build_prompt(self, mode: str, strategy_key: str = 'standard') -> str:
        prompt = load_strategy_prompt(strategy_key, mode)
        hard_constraint = "\n\n【指令】：你可以进行思考和步骤拆解，但请务必在最后提供完整合并的润色正文。"
        return prompt + hard_constraint

    def build_extractor_prompt(self) -> str:
        return load_extractor_prompt()

    def build_simple_extractor_prompt(self) -> str:
        return load_simple_extractor_prompt()


class APIParameterGenerator:
    """API参数生成器"""

    @staticmethod
    def get_dynamic_temperature(strategy: str = 'standard') -> float:
        if strategy == 'strict':
            return round(random.uniform(0.90, 0.98), 2)
        else:
            return round(random.uniform(0.85, 0.95), 2)

    @staticmethod
    def get_api_params(strategy: str = 'standard') -> dict:
        base_params = {
            'temperature': APIParameterGenerator.get_dynamic_temperature(strategy),
        }
        if strategy == 'strict':
            base_params['presence_penalty'] = 0.6
            base_params['frequency_penalty'] = 0.7
        else:
            base_params['presence_penalty'] = 0.3
            base_params['frequency_penalty'] = 0.4
        return base_params
