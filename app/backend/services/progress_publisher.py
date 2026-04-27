"""
进度推送服务

负责向Redis Pub/Sub推送任务进度消息
"""
from __future__ import annotations

from typing import Any, Union

import json
import redis as redis_module
from backend.config import RedisKeyManager
from backend.utils.logging_config import get_logger

logger = get_logger(__name__)


class ProgressPublisher:
    """进度推送器"""

    def __init__(self, redis_client: redis_module.Redis, task_id: int) -> None:
        """
        初始化进度推送器

        Args:
            redis_client: Redis客户端
            task_id: 任务ID
        """
        self.redis = redis_client
        self.task_id = task_id
        self.channel_name = RedisKeyManager.stream_channel(task_id)

    def publish_message(self, msg_type: str, content: Any) -> None:
        """
        推送消息到Redis频道

        Args:
            msg_type: 消息类型 (stream/block/progress/done/fatal)
            content: 消息内容
        """
        payload = json.dumps({"type": msg_type, "content": content})
        message = f"data: {payload}\n\n"

        try:
            self.redis.publish(self.channel_name, message)
            logger.debug(f"推送消息 [{msg_type}] 到任务 {self.task_id}")
        except Exception as e:
            logger.error(f"推送消息失败: {str(e)}")

    def publish_status(self, status: str, message: str = "") -> None:
        """推送状态消息"""
        self.publish_message("status", {"status": status, "message": message})

    def publish_chunk(self, content: str) -> None:
        """推送文本片段"""
        self.publish_message("chunk", content)

    def publish_stream(self, content: str) -> None:
        """推送流式内容（增量追加）"""
        self.publish_message("stream", content)

    def publish_full(self, content: str) -> None:
        """推送完整结果（替换而非追加）"""
        self.publish_message("full", content)

    def publish_block(self, content: str) -> None:
        """推送块消息"""
        self.publish_message("block", content)

    def publish_progress(self, percentage: int) -> None:
        """推送进度百分比"""
        self.publish_message("progress", percentage)

    def publish_done(self, download_url: str = "") -> None:
        """推送完成消息"""
        self.publish_message("done", {"download_url": download_url} if download_url else "完成")

    def publish_error(self, error_msg: str) -> None:
        """推送错误消息"""
        self.publish_message("fatal", error_msg)

    def publish_download(self, download_url: str) -> None:
        """推送下载链接"""
        self.publish_message("download", download_url)
