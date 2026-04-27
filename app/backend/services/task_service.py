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
import subprocess
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
        创建文档任务（支持 .docx 和 .doc）

        .doc 文件会先通过 LibreOffice 转换为 .docx
        """
        filename = secure_filename(file.filename)
        ext = os.path.splitext(filename)[1].lower()
        save_path = os.path.join('uploads', f"{user.id}_{filename}")
        file.save(save_path)

        if ext == '.doc':
            save_path = self._convert_doc_to_docx(save_path)
            filename = os.path.splitext(filename)[0] + '.docx'

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
            self.queue.enqueue('backend.worker_engine.process_task', task.id)
            return task

        except Exception as e:
            self.db.session.rollback()
            if os.path.exists(save_path):
                os.remove(save_path)
            raise

    def create_pdf_task(self, user: User, file: Any, mode: str, strategy: str) -> Task:
        """创建PDF文档任务"""
        filename = secure_filename(file.filename)
        save_path = os.path.join('uploads', f"{user.id}_{filename}")
        file.save(save_path)

        try:
            task = Task(
                user_id=user.id,
                title=filename[:20],
                original_text=f"[PDF任务] {filename}",
                mode=mode,
                strategy=strategy,
                status='queued',
                task_type='pdf',
                file_path=save_path
            )

            self.db.session.add(task)
            self.db.session.commit()
            self.queue.enqueue('backend.worker_engine.process_task', task.id)
            return task

        except Exception as e:
            self.db.session.rollback()
            if os.path.exists(save_path):
                os.remove(save_path)
            raise

    def _convert_doc_to_docx(self, doc_path: str) -> str:
        """将 .doc 文件转换为 .docx（需要系统安装 LibreOffice）"""
        output_dir = os.path.dirname(doc_path)
        try:
            subprocess.run(
                ['libreoffice', '--headless', '--convert-to', 'docx', doc_path, '--outdir', output_dir],
                timeout=60, check=True, capture_output=True
            )
        except FileNotFoundError:
            raise ValueError("服务器未安装 LibreOffice，无法处理 .doc 文件，请转换为 .docx 后重新上传")
        except subprocess.TimeoutExpired:
            raise ValueError(".doc 文件转换超时，请转换为 .docx 后重新上传")

        docx_path = os.path.splitext(doc_path)[0] + '.docx'
        if not os.path.exists(docx_path):
            raise ValueError(".doc 文件转换失败，请转换为 .docx 后重新上传")

        os.remove(doc_path)
        return docx_path

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
                "download_url": f"/api/tasks/download/{t.id}" if getattr(t, 'task_type', 'text') in ('docx', 'pdf') and t.status == 'completed' else "",
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
