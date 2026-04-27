"""
任务服务层

负责任务的创建、取消、恢复等业务逻辑
"""
from __future__ import annotations

from typing import Any, Optional

from backend.extensions import db, redis_client, task_queue
from backend.config import RedisKeyManager
from backend.model.models import Task, User
from backend.utils.helpers import extract_title
from backend.utils.text_hash import store_text_hash
import os
from werkzeug.utils import secure_filename


class TaskService:
    """任务服务"""

    def __init__(self, db_session: Any = None, redis: Any = None, queue: Any = None) -> None:
        self.db = db_session or db
        self.redis = redis or redis_client
        self.queue = queue or task_queue

    def create_text_task(self, user: User, text: str, mode: str, strategy: str) -> Task:
        """
        创建文本任务

        Args:
            user: 用户对象
            text: 原始文本
            mode: 语言模式 (zh/en)
            strategy: 策略 (standard/strict)

        Returns:
            Task: 创建的任务对象

        Raises:
            ValueError: 参数验证失败
        """
        if not text or not text.strip():
            raise ValueError("文本不能为空")

        try:
            task = Task(
                user_id=user.id,
                title=extract_title(text),
                original_text=text,
                mode=mode,
                strategy=strategy,
                status='queued',
                task_type='text'
            )

            # 扣除使用次数
            user.usage_count += 1

            self.db.session.add(task)
            self.db.session.commit()

            # 存储文本哈希（用于去重检测）
            store_text_hash(self.redis, text, user.id, task.id, hours=24)

            # 将任务入队
            self.queue.enqueue('backend.worker_engine.process_task', task.id)

            return task

        except Exception as e:
            self.db.session.rollback()
            raise

    def create_docx_task(self, user: User, file: Any, mode: str, strategy: str) -> Task:
        """
        创建文档任务

        Args:
            user: 用户对象
            file: 上传的文件对象
            mode: 语言模式 (zh/en)
            strategy: 策略 (standard/strict)

        Returns:
            Task: 创建的任务对象
        """
        filename = secure_filename(file.filename)
        save_path = os.path.join('uploads', f"{user.id}_{filename}")

        # 保存文件
        file.save(save_path)

        try:
            task = Task(
                user_id=user.id,
                title=filename[:20],
                original_text=f"[文档任务] {filename}",
                mode=mode,
                strategy=strategy,
                status='queued',
                task_type='docx',
                file_path=save_path
            )

            self.db.session.add(task)
            self.db.session.commit()

            # 异步入队
            self.queue.enqueue('backend.worker_engine.process_task', task.id)

            return task

        except Exception as e:
            self.db.session.rollback()
            # 删除已上传的文件
            if os.path.exists(save_path):
                os.remove(save_path)
            raise

    def cancel_task(self, task_id: int, user_id: int) -> dict:
        """
        取消任务

        Args:
            task_id: 任务ID
            user_id: 用户ID

        Returns:
            dict: 操作结果

        Raises:
            ValueError: 无权操作或任务状态不允许取消
        """
        task = Task.query.get(task_id)

        if not task or task.user_id != user_id:
            raise ValueError("无权操作此任务")

        if task.status in ['completed', 'failed', 'cancelled']:
            return {"message": "任务已结束", "status": task.status}

        # 更新任务状态
        task.status = 'cancelled'
        self.db.session.commit()

        # 给 Redis 写一个"取消令"标记
        cancel_key = RedisKeyManager.cancel_key(task_id)
        self.redis.setex(cancel_key, 3600, "1")

        channel_name = RedisKeyManager.stream_channel(task_id)
        import json
        payload = json.dumps({"type": "fatal", "content": "用户主动终止了任务"})
        self.redis.publish(channel_name, f"data: {payload}\n\n")

        return {"message": "任务已取消", "task_id": task_id}

    def resume_task(self, task_id: int, user_id: int) -> dict:
        """
        恢复任务

        Args:
            task_id: 任务ID
            user_id: 用户ID

        Returns:
            dict: 操作结果

        Raises:
            ValueError: 无权操作或任务状态不允许恢复
        """
        task = Task.query.get(task_id)

        if not task or task.user_id != user_id:
            raise ValueError("无权操作此任务")

        if task.status not in ['cancelled', 'failed']:
            raise ValueError("当前状态无法恢复")

        # 重置状态，重新入队
        task.status = 'queued'
        self.db.session.commit()

        self.queue.enqueue('backend.worker_engine.process_task', task.id)

        return {"message": "任务已恢复", "task_id": task_id}

    def get_user_tasks(self, user_id: int, limit: int = 50) -> list:
        """
        获取用户任务历史

        Args:
            user_id: 用户ID
            limit: 返回数量限制

        Returns:
            list: 任务列表
        """
        tasks = Task.query.filter_by(user_id=user_id).order_by(Task.id.desc()).limit(limit).all()

        result = []
        for t in tasks:
            result.append({
                "id": t.id,
                "title": t.title or "未命名任务",
                "original_text": t.original_text,
                "polished_text": t.polished_text or "",
                "status": t.status,
                "task_type": getattr(t, 'task_type', 'text'),
                "download_url": f"/api/tasks/download/{t.id}" if getattr(t, 'task_type', 'text') == 'docx' and t.status == 'completed' else "",
                "created_at": t.created_at.strftime("%Y-%m-%d %H:%M:%S") if t.created_at else ""
            })

        return result

    def delete_task(self, task_id: int, user_id: int) -> dict:
        task = Task.query.get(task_id)
        if not task or task.user_id != user_id:
            raise ValueError("无权操作此任务")
        if task.status in ['processing', 'queued']:
            raise ValueError("进行中的任务无法删除，请先取消")
        self.db.session.delete(task)
        self.db.session.commit()
        return {"message": "任务已删除", "task_id": task_id}
