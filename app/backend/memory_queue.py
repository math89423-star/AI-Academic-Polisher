"""
内存任务队列 — desktop 模式下替代 RQ + 外部 Worker 进程
单线程消费，在 Flask app_context 中执行任务
"""
import importlib
import threading
import queue
from typing import Any

from backend.utils.logging_config import get_logger

logger = get_logger(__name__)


class MemoryQueue:
    def __init__(self) -> None:
        self._queue: queue.Queue = queue.Queue()
        self._worker_thread: threading.Thread | None = None

    def enqueue(self, func_path: str, *args: Any, **kwargs: Any) -> None:
        self._queue.put((func_path, args))

    def __len__(self) -> int:
        return self._queue.qsize()

    def start_worker(self, app: Any) -> None:
        if self._worker_thread and self._worker_thread.is_alive():
            return
        # 注入 app 到 worker_engine，避免重复创建 Flask 实例
        from backend.worker_engine import set_app
        set_app(app)
        self._worker_thread = threading.Thread(
            target=self._worker_loop, args=(app,), daemon=True, name="MemoryQueueWorker"
        )
        self._worker_thread.start()
        logger.info("[MemoryQueue] Worker 线程已启动")

    def _worker_loop(self, app: Any) -> None:
        while True:
            try:
                func_path, args = self._queue.get()
            except Exception:
                continue
            try:
                fn = self._resolve_func(func_path)
                with app.app_context():
                    fn(*args)
            except Exception as e:
                logger.error(f"[MemoryQueue] 任务执行失败: {e}", exc_info=True)
            finally:
                self._queue.task_done()

    @staticmethod
    def _resolve_func(dotted_path: str) -> Any:
        module_path, func_name = dotted_path.rsplit('.', 1)
        module = importlib.import_module(module_path)
        return getattr(module, func_name)
