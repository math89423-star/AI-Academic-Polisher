"""
重构后的Worker引擎

使用处理器模式，职责更加清晰
"""
from backend.extensions import db
from backend import create_app
from backend.model.models import Task
from backend.processors.text_processor import TextTaskProcessor
from backend.processors.docx_processor import DocxTaskProcessor
from backend.utils.logging_config import get_logger

logger = get_logger(__name__)

app = create_app()


def process_task(task_id: int):
    """
    处理任务（重构版）

    Args:
        task_id: 任务ID
    """
    with app.app_context():
        task = Task.query.get(task_id)

        if not task:
            logger.error(f"任务 {task_id} 不存在")
            return

        logger.info(f"=" * 50)
        logger.info(f"开始处理任务 ID: {task_id}, 类型: {getattr(task, 'task_type', 'text')}")
        logger.info(f"=" * 50)

        try:
            # 根据任务类型选择处理器
            processor = _get_processor(task)

            if processor is None:
                logger.error(f"未知的任务类型: {getattr(task, 'task_type', 'unknown')}")
                task.status = 'failed'
                db.session.commit()
                return

            # 运行处理器
            processor.run()

        except Exception as e:
            logger.critical(f"任务 {task_id} 处理过程中发生严重错误: {str(e)}", exc_info=True)
            task.status = 'failed'
            db.session.commit()

        finally:
            logger.info(f"任务 {task_id} 处理流程结束")


def _get_processor(task):
    """
    根据任务类型获取对应的处理器

    Args:
        task: 任务对象

    Returns:
        BaseTaskProcessor: 任务处理器实例
    """
    task_type = getattr(task, 'task_type', 'text')

    if task_type == 'text':
        return TextTaskProcessor(task)
    elif task_type == 'docx':
        return DocxTaskProcessor(task)
    else:
        return None
