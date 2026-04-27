"""
重试策略

负责处理API请求的重试逻辑
"""
from __future__ import annotations

from typing import Any, Callable, Optional

import time
from backend.config import WorkerConfig
from backend.utils.logging_config import get_logger

logger = get_logger(__name__)


class RetryPolicy:
    """重试策略"""

    def __init__(self, max_retries: Optional[int] = None, delay_base: Optional[int] = None) -> None:
        """
        初始化重试策略

        Args:
            max_retries: 最大重试次数
            delay_base: 指数退避基数
        """
        self.max_retries = max_retries or WorkerConfig.RETRY_TIMES
        self.delay_base = delay_base or WorkerConfig.RETRY_DELAY_BASE

    def execute_with_retry(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """
        执行函数并在失败时重试

        Args:
            func: 要执行的函数
            *args: 函数参数
            **kwargs: 函数关键字参数

        Returns:
            函数执行结果

        Raises:
            Exception: 重试次数耗尽后抛出最后一次异常
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                logger.warning(f"尝试 {attempt + 1}/{self.max_retries} 失败: {str(e)}")

                if attempt < self.max_retries - 1:
                    # 指数退避
                    delay = self.delay_base ** attempt
                    logger.info(f"等待 {delay} 秒后重试...")
                    time.sleep(delay)
                else:
                    logger.error(f"重试次数耗尽，最终失败: {str(e)}")

        raise last_exception
