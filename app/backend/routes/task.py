"""
任务路由（重构版）

使用TaskService和装饰器
"""
from __future__ import annotations

from flask import Blueprint, request, jsonify, Response, send_file
from backend.services.task_service import TaskService
from backend.services.user_service import UserService
from backend.utils.text_hash import check_duplicate_text
from backend.config import RedisKeyManager
from backend.extensions import redis_client, task_queue, db
from backend.utils.logging_config import get_logger
import os
import json

task_bp = Blueprint('task', __name__)
logger = get_logger(__name__)

def _task_service() -> TaskService:
    return TaskService()

def _user_service() -> UserService:
    return UserService()


@task_bp.route('/check_duplicate', methods=['POST'])
def check_duplicate():
    """检查文本是否重复"""
    data = request.json
    username = data.get('username', '').strip()
    text = data.get('text', '').strip()

    try:
        user = _user_service().authenticate_user(username)
    except ValueError:
        return jsonify({"error": "无效用户"}), 401

    if not text:
        return jsonify({"is_duplicate": False}), 200

    # 检查是否重复（24小时内）
    result = check_duplicate_text(redis_client, text, user.id, hours=24)
    return jsonify(result), 200


@task_bp.route('/create', methods=['POST'])
def create_task():
    """创建文本任务"""
    data = request.json
    username = data.get('username', '').strip()
    original_text = data.get('text', '').strip()
    mode = data.get('mode', 'zh').strip()
    strategy = data.get('strategy', 'standard').strip()

    # 验证用户
    try:
        user = _user_service().authenticate_user(username)
    except ValueError as e:
        return jsonify({"error": str(e)}), 401

    # 验证文本
    if not original_text:
        return jsonify({"error": "文本不能为空"}), 400

    # 创建任务
    try:
        task = _task_service().create_text_task(user, original_text, mode, strategy)
        logger.info(f"用户 {username} 创建文本任务: {task.id}")
        return jsonify({"task_id": task.id, "title": task.title}), 201

    except Exception as e:
        logger.error(f"创建任务失败: {str(e)}")
        return jsonify({"error": "创建任务失败"}), 500


@task_bp.route('/upload_docx', methods=['POST'])
@task_bp.route('/upload_document', methods=['POST'])
def upload_document():
    """上传文档任务（支持 doc/docx/pdf）"""
    if 'file' not in request.files:
        return jsonify({"error": "未找到文件"}), 400

    file = request.files['file']
    username = request.form.get('username')
    mode = request.form.get('mode', 'zh')
    strategy = request.form.get('strategy', 'standard')

    filename = file.filename or ''
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ('.doc', '.docx', '.pdf'):
        return jsonify({"error": "仅支持 doc、docx、pdf 格式"}), 400

    # 验证用户
    try:
        user = _user_service().authenticate_user(username)
    except ValueError as e:
        return jsonify({"error": str(e)}), 403

    # 创建文档任务
    try:
        if ext == '.pdf':
            task = _task_service().create_pdf_task(user, file, mode, strategy)
        else:
            task = _task_service().create_docx_task(user, file, mode, strategy)
        logger.info(f"用户 {username} 上传文档任务: {task.id} ({ext})")
        return jsonify({"task_id": task.id, "title": task.title}), 201

    except Exception as e:
        logger.error(f"上传文档失败: {str(e)}")
        return jsonify({"error": "上传失败"}), 500


@task_bp.route('/<int:task_id>/stream', methods=['GET'])
def stream_results(task_id):
    """SSE流式推送任务结果"""
    def generate():
        from backend.model.models import Task
        from backend.config import SSEConfig
        import time

        pubsub = redis_client.pubsub()
        channel_name = RedisKeyManager.stream_channel(task_id)
        pubsub.subscribe(channel_name)

        try:
            initial_payload = json.dumps({
                'type': 'block',
                'content': '⏳ 已连接到推送通道，等待 AI 响应...\n\n'
            })
            yield f"data: {initial_payload}\n\n"

            task = Task.query.get(task_id)
            if task and task.status == 'completed' and task.polished_text:
                done_payload = json.dumps({'type': 'stream', 'content': task.polished_text})
                yield f"data: {done_payload}\n\n"
                finish_payload = json.dumps({'type': 'done', 'content': '完成'})
                yield f"data: {finish_payload}\n\n"
                return
            if task and task.status == 'failed':
                err_payload = json.dumps({'type': 'fatal', 'content': '任务处理失败'})
                yield f"data: {err_payload}\n\n"
                return

            last_message_time = time.time()
            last_db_check = time.time()
            db_check_interval = 3
            timeout = SSEConfig.TIMEOUT
            heartbeat_interval = SSEConfig.HEARTBEAT_INTERVAL

            while True:
                now = time.time()

                if now - last_message_time > timeout:
                    error_payload = json.dumps({
                        'type': 'fatal',
                        'content': '连接超时，请刷新页面重试'
                    })
                    yield f"data: {error_payload}\n\n"
                    break

                message = pubsub.get_message(timeout=heartbeat_interval)

                if message and message['type'] == 'message':
                    raw_data = message['data']
                    yield raw_data
                    last_message_time = time.time()

                    if '"type": "done"' in raw_data or '"type": "fatal"' in raw_data:
                        break
                else:
                    if now - last_db_check >= db_check_interval:
                        last_db_check = now
                        db.session.expire_all()
                        task = Task.query.get(task_id)
                        if task and task.status == 'completed' and task.polished_text:
                            done_payload = json.dumps({'type': 'stream', 'content': task.polished_text})
                            yield f"data: {done_payload}\n\n"
                            finish_payload = json.dumps({'type': 'done', 'content': '完成'})
                            yield f"data: {finish_payload}\n\n"
                            break
                        elif task and task.status == 'failed':
                            err_payload = json.dumps({'type': 'fatal', 'content': '任务处理失败'})
                            yield f"data: {err_payload}\n\n"
                            break

                    yield ": heartbeat\n\n"

        finally:
            pubsub.unsubscribe(channel_name)
            pubsub.close()

    return Response(generate(), mimetype='text/event-stream')


@task_bp.route('/<int:task_id>/detail', methods=['GET'])
def get_task_detail(task_id: int):
    """获取单个任务详情"""
    from backend.model.models import Task
    task = Task.query.get(task_id)
    if not task:
        return jsonify({"error": "任务不存在"}), 404
    return jsonify({
        "id": task.id,
        "title": task.title or "未命名任务",
        "original_text": task.original_text,
        "polished_text": task.polished_text or "",
        "status": task.status,
        "task_type": getattr(task, 'task_type', 'text'),
        "download_url": f"/api/tasks/download/{task.id}" if getattr(task, 'task_type', 'text') in ('docx', 'pdf') and task.status == 'completed' else "",
        "created_at": task.created_at.strftime("%Y-%m-%d %H:%M:%S") if task.created_at else ""
    }), 200


@task_bp.route('/history', methods=['GET'])
def get_history():
    """获取用户任务历史"""
    username = request.args.get('username', '').strip()

    try:
        user = _user_service().authenticate_user(username)
    except ValueError:
        return jsonify({"error": "无权访问"}), 401

    tasks = _task_service().get_user_tasks(user.id, limit=50)
    return jsonify(tasks), 200


@task_bp.route('/<int:task_id>/cancel', methods=['POST'])
def cancel_task(task_id):
    """取消任务"""
    data = request.json
    username = data.get('username')

    try:
        user = _user_service().authenticate_user(username)
    except ValueError:
        return jsonify({"error": "无权操作"}), 403

    try:
        result = _task_service().cancel_task(task_id, user.id)
        logger.info(f"用户 {username} 取消任务: {task_id}")
        return jsonify(result), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 403


@task_bp.route('/<int:task_id>/resume', methods=['POST'])
def resume_task(task_id):
    """恢复任务"""
    data = request.json
    username = data.get('username')

    try:
        user = _user_service().authenticate_user(username)
    except ValueError:
        return jsonify({"error": "无权操作"}), 403

    try:
        result = _task_service().resume_task(task_id, user.id)
        logger.info(f"用户 {username} 恢复任务: {task_id}")
        return jsonify(result), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@task_bp.route('/download/<int:task_id>', methods=['GET'])
def download_docx(task_id):
    """下载润色后的文档"""
    from backend.model.models import Task

    task = Task.query.get(task_id)

    if not task or task.status != 'completed' or not task.result_file_path:
        return jsonify({"error": "文件不存在或尚未完成"}), 404

    # 获取项目绝对路径并拼接
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, '../../'))
    absolute_file_path = os.path.join(project_root, task.result_file_path)

    return send_file(
        absolute_file_path,
        as_attachment=True,
        download_name=f"Polished_{os.path.splitext(task.title)[0]}.docx"
    )


@task_bp.route('/<int:task_id>/delete', methods=['POST'])
def delete_task(task_id):
    """删除任务"""
    data = request.json
    username = data.get('username')

    try:
        user = _user_service().authenticate_user(username)
    except ValueError:
        return jsonify({"error": "无权操作"}), 403

    try:
        result = _task_service().delete_task(task_id, user.id)
        logger.info(f"用户 {username} 删除任务: {task_id}")
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@task_bp.route('/queue_status', methods=['GET'])
def queue_status():
    """获取当前排队任务数"""
    pending = len(task_queue)
    return jsonify({"pending_count": pending}), 200


@task_bp.route('/strategies', methods=['GET'])
def get_strategies():
    """获取可用策略列表（根据用户权限过滤）"""
    from backend.prompts_config import STRATEGIES
    from backend.model.models import User

    username = request.args.get('username', '')
    user = User.query.filter_by(username=username).first() if username else None

    result = []
    for key, value in STRATEGIES.items():
        if key == 'strict' and user and not user.can_use_strict and user.role != 'admin':
            continue
        result.append({
            "id": key,
            "name": value.get("name", key),
            "color": value.get("color", "#334155")
        })

    result.sort(key=lambda x: 0 if x['id'] == 'standard' else 1)

    return jsonify(result), 200
