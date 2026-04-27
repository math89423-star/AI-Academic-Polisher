"""
任务路由（重构版）

使用TaskService和装饰器
"""
from flask import Blueprint, request, jsonify, Response, send_file
from backend.services.task_service import TaskService
from backend.services.user_service import UserService
from backend.utils.text_hash import check_duplicate_text
from backend.extensions import redis_client
from backend.utils.logging_config import get_logger
import os
import json

task_bp = Blueprint('task', __name__)
task_service = TaskService()
user_service = UserService()
logger = get_logger(__name__)


@task_bp.route('/check_duplicate', methods=['POST'])
def check_duplicate():
    """检查文本是否重复"""
    data = request.json
    username = data.get('username', '').strip()
    text = data.get('text', '').strip()

    try:
        user = user_service.authenticate_user(username)
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
        user = user_service.authenticate_user(username)
    except ValueError as e:
        return jsonify({"error": str(e)}), 401

    # 验证文本
    if not original_text:
        return jsonify({"error": "文本不能为空"}), 400

    # 创建任务
    try:
        task = task_service.create_text_task(user, original_text, mode, strategy)
        logger.info(f"用户 {username} 创建文本任务: {task.id}")
        return jsonify({"task_id": task.id, "title": task.title}), 201

    except Exception as e:
        logger.error(f"创建任务失败: {str(e)}")
        return jsonify({"error": "创建任务失败"}), 500


@task_bp.route('/upload_docx', methods=['POST'])
def upload_docx():
    """上传文档任务"""
    if 'file' not in request.files:
        return jsonify({"error": "未找到文件"}), 400

    file = request.files['file']
    username = request.form.get('username')
    mode = request.form.get('mode', 'zh')
    strategy = request.form.get('strategy', 'standard')

    # 验证用户
    try:
        user = user_service.authenticate_user(username)
    except ValueError as e:
        return jsonify({"error": str(e)}), 403

    # 创建文档任务
    try:
        task = task_service.create_docx_task(user, file, mode, strategy)
        logger.info(f"用户 {username} 上传文档任务: {task.id}")
        return jsonify({"task_id": task.id, "title": task.title}), 201

    except Exception as e:
        logger.error(f"上传文档失败: {str(e)}")
        return jsonify({"error": "上传失败"}), 500


@task_bp.route('/stream/<int:task_id>', methods=['GET'])
def stream_results(task_id):
    """SSE流式推送任务结果"""
    def generate():
        pubsub = redis_client.pubsub()
        channel_name = f"stream:task:{task_id}"
        pubsub.subscribe(channel_name)

        try:
            # 发送初始连接消息
            initial_payload = json.dumps({
                'type': 'block',
                'content': '⏳ 已连接到推送通道，等待 AI 响应...\n\n'
            })
            yield f"data: {initial_payload}\n\n"

            # 添加超时机制
            import time
            last_message_time = time.time()
            timeout = 600  # 10分钟超时

            for message in pubsub.listen():
                # 检查超时
                if time.time() - last_message_time > timeout:
                    error_payload = json.dumps({
                        'type': 'fatal',
                        'content': '连接超时，请刷新页面重试'
                    })
                    yield f"data: {error_payload}\n\n"
                    break

                if message['type'] == 'message':
                    raw_data = message['data']
                    yield raw_data
                    last_message_time = time.time()

                    if '"type": "done"' in raw_data or '"type": "fatal"' in raw_data:
                        break

        finally:
            pubsub.unsubscribe(channel_name)
            pubsub.close()

    return Response(generate(), mimetype='text/event-stream')


@task_bp.route('/history', methods=['GET'])
def get_history():
    """获取用户任务历史"""
    username = request.args.get('username', '').strip()

    try:
        user = user_service.authenticate_user(username)
    except ValueError:
        return jsonify({"error": "无权访问"}), 401

    tasks = task_service.get_user_tasks(user.id, limit=50)
    return jsonify(tasks), 200


@task_bp.route('/<int:task_id>/cancel', methods=['POST'])
def cancel_task(task_id):
    """取消任务"""
    data = request.json
    username = data.get('username')

    try:
        user = user_service.authenticate_user(username)
    except ValueError:
        return jsonify({"error": "无权操作"}), 403

    try:
        result = task_service.cancel_task(task_id, user.id)
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
        user = user_service.authenticate_user(username)
    except ValueError:
        return jsonify({"error": "无权操作"}), 403

    try:
        result = task_service.resume_task(task_id, user.id)
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
        download_name=f"Polished_{task.title}.docx"
    )


@task_bp.route('/strategies', methods=['GET'])
def get_strategies():
    """获取可用策略列表"""
    from backend.prompts_config import STRATEGIES

    result = []
    for key, value in STRATEGIES.items():
        result.append({
            "id": key,
            "name": value.get("name", key),
            "color": value.get("color", "#334155")
        })

    # 为了保证界面显示的稳定性，强制让 standard 排在第一位
    result.sort(key=lambda x: 0 if x['id'] == 'standard' else 1)

    return jsonify(result), 200
