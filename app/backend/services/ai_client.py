"""
AI客户端封装

负责OpenAI客户端的创建和管理
"""
from __future__ import annotations

from typing import Any, Union

from openai import OpenAI, Stream
from openai.types.chat import ChatCompletion, ChatCompletionChunk


class AIClient:
    """AI客户端封装"""

    def __init__(self, api_key: str, base_url: str, model_name: str):
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name
        self._client = None

    @property
    def client(self) -> OpenAI:
        """获取OpenAI客户端实例"""
        if self._client is None:
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                default_headers=self._get_custom_headers()
            )
        return self._client

    @staticmethod
    def _get_custom_headers() -> dict[str, str]:
        """返回自定义headers用于绕过反爬"""
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://chat.openai.com/",
            "Origin": "https://chat.openai.com"
        }

    def create_completion(self, messages: list[dict[str, str]], temperature: float, presence_penalty: float = 0,
                         frequency_penalty: float = 0, stream: bool = False) -> Union[ChatCompletion, Stream[ChatCompletionChunk]]:
        """
        创建聊天完成请求

        Args:
            messages: 消息列表
            temperature: 温度参数
            presence_penalty: 存在惩罚
            frequency_penalty: 频率惩罚
            stream: 是否流式输出

        Returns:
            响应对象
        """
        return self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=temperature,
            presence_penalty=presence_penalty,
            frequency_penalty=frequency_penalty,
            stream=stream
        )
