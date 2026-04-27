"""
AI 润色系统提示词与策略全局配置文件

提示词内容已外置到 app/backend/prompts/ 目录下的 md 文件中
"""
import os

_PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")


def _load_prompt(filename: str) -> str:
    filepath = os.path.join(_PROMPTS_DIR, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


STRATEGIES = {
    "standard": {
        "name": "⚖️ 标准平衡 (针对朱雀，知网)",
        "color": "#334155",
        "zh_prompt_file": "cn_standard.md",
        "en_prompt_file": "en_standard.md",
    },
    "strict": {
        "name": "⚡ 极致降重 (针对维普)",
        "color": "#d97706",
        "zh_prompt_file": "cn_strict.md",
        "en_prompt_file": "en_strict.md",
    }
}


def load_strategy_prompt(strategy_key: str, mode: str) -> str:
    strategy = STRATEGIES.get(strategy_key) or STRATEGIES.get("standard") or {}
    filename = strategy.get("en_prompt_file" if mode == "en" else "zh_prompt_file")
    if filename:
        return _load_prompt(filename)
    return "你是一个专业的学术润色系统，请对原文进行润色改写。"


def load_extractor_prompt() -> str:
    return _load_prompt("extractor.md")


def load_simple_extractor_prompt() -> str:
    return "提取出以下文本中真正的最终改写正文，去除所有分析、思考步骤和引导前缀。直接输出正文本身："


def load_continuation_prompt() -> str:
    return _load_prompt("continuation.md").strip()
