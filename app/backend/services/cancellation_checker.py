"""
取消信号检测服务

负责检测和处理任务取消信号
"""
from backend.config import RedisConfig
from backend.utils.logging_config import get_logger

logger = get_logger(__name__)


class CancellationChecker:
    """取消信号检测器"""

    def __init__(self, redis_client, task_id: int):
        """
        初始化取消信号检测器

        Args:
            redis_client: Redis客户端
            task_id: 任务ID
        """
        self.redis = redis_client
        self.task_id = task_id
        self.cancel_key = f"{RedisConfig.CANCEL_KEY_PREFIX}{task_id}"

    def is_cancelled(self) -> bool:
        """
        检查任务是否被取消

        Returns:
            bool: 是否被取消
        """
        try:
            return self.redis.exists(self.cancel_key)
        except Exception as e:
            logger.error(f"检查取消信号失败: {str(e)}")
            return False

    def mark_cancelled(self, task, db_session):
        """
        标记任务为已取消

        Args:
            task: 任务对象
            db_session: 数据库会话
        """
        try:
            task.status = 'cancelled'
            db_session.commit()
            self.clear_cancel_signal()
            logger.info(f"任务 {self.task_id} 已标记为取消")
        except Exception as e:
            logger.error(f"标记任务取消失败: {str(e)}")
            db_session.rollback()

    def clear_cancel_signal(self):
        """清除取消信号"""
        try:
            self.redis.delete(self.cancel_key)
            logger.debug(f"清除任务 {self.task_id} 的取消信号")
        except Exception as e:
            logger.error(f"清除取消信号失败: {str(e)}")
