"""
任务处理器基类

定义任务处理的通用接口和流程
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from backend.services.progress_publisher import ProgressPublisher
from backend.services.cancellation_checker import CancellationChecker
from backend.services.ai_service_refactored import AIService
from backend.services.api_config_service import ApiConfigService
from backend.extensions import db
from backend.utils.logging_config import get_logger

logger = get_logger(__name__)


class BaseTaskProcessor(ABC):
    """任务处理器基类"""

    def __init__(self, task: object, redis_client: Any) -> None:
        self.task = task
        self.task_id: int = task.id
        self.redis_client = redis_client
        self.progress_publisher = ProgressPublisher(redis_client, task.id)
        self.cancellation_checker = CancellationChecker(redis_client, task.id)
        self.ai_service: Optional[AIService] = None

    def initialize_ai_service(self) -> None:
        """初始化AI服务"""
        from backend.model.models import User

        user = User.query.get(self.task.user_id)
        api_config_service = ApiConfigService()

        # 解析API配置
        api_key, base_url, model_name = api_config_service.resolve_config(
            user,
            getattr(self.task, 'strategy', 'standard')
        )

        if not api_key or not base_url:
            raise ValueError("系统未配置可用的 API 线路")

        self.ai_service = AIService(api_key, base_url, model_name)
        logger.info(f"任务 {self.task_id} 使用模型: {model_name}")

    def check_cancellation(self) -> bool:
        """
        检查任务是否被取消

        Returns:
            bool: 如果被取消返回True
        """
        if self.cancellation_checker.is_cancelled():
            logger.info(f"任务 {self.task_id} 检测到取消信号")
            self.cancellation_checker.mark_cancelled(self.task, db.session)
            return True
        return False

    def update_task_status(self, status: str) -> None:
        """
        更新任务状态

        Args:
            status: 新状态
        """
        self.task.status = status
        db.session.commit()
        logger.info(f"任务 {self.task_id} 状态更新为: {status}")

    @abstractmethod
    def process(self) -> None:
        """
        处理任务（子类必须实现）

        Raises:
            NotImplementedError: 子类未实现此方法
        """
        raise NotImplementedError("子类必须实现process方法")

    def run(self) -> None:
        """
        运行任务处理流程

        包含异常处理和状态管理
        """
        logger.info(f"开始处理任务 {self.task_id} (类型: {self.task.task_type})")

        try:
            # 初始化AI服务
            self.initialize_ai_service()

            # 更新状态为处理中
            self.update_task_status('processing')

            # 执行具体处理逻辑
            self.process()

            # 如果没有被取消，标记为完成
            if self.task.status != 'cancelled':
                self.update_task_status('completed')
                self.progress_publisher.publish_done()
                logger.info(f"任务 {self.task_id} 处理完成")

        except Exception as e:
            logger.error(f"任务 {self.task_id} 处理失败: {str(e)}", exc_info=True)
            db.session.rollback()
            self.task.status = 'failed'
            db.session.commit()
            self.progress_publisher.publish_error(f"处理失败: {str(e)}")
            self.handle_failure(e)

        finally:
            # 清理资源
            self.cleanup()

    def handle_failure(self, exception: Exception) -> None:
        """
        处理失败情况（子类可以覆盖）

        Args:
            exception: 异常对象
        """
        pass

    def cleanup(self) -> None:
        """
        清理资源（子类可以覆盖）
        """
        # 清理取消信号
        self.cancellation_checker.clear_cancel_signal()
        logger.debug(f"任务 {self.task_id} 资源清理完成")
