# backend/routes/task.py
import json
from flask import Blueprint, request, jsonify, Response
from backend.extensions import db, task_queue, redis_client
from backend.model.models import User, Task
from backend.utils.helpers import extract_title, split_text_into_chunks
import os
from werkzeug.utils import secure_filename
from flask import send_file

task_bp = Blueprint('task', __name__)

@task_bp.route('/create', methods=['POST'])
def create_task():
    data = request.json
    username = data.get('username', '').strip() 
    original_text = data.get('text', '').strip()
    mode = data.get('mode', 'zh').strip()

    user = User.query.filter_by(username=username).first()
    if not user: return jsonify({"error": "无效的卡密"}), 401
    if not user.is_active: return jsonify({"error": "此卡密已被停用"}), 403
    if not original_text: return jsonify({"error": "文本不能为空"}), 400

    # 创建任务并扣除次数
    task = Task(
        user_id=user.id, 
        title=extract_title(original_text), 
        original_text=original_text, 
        mode=mode,  # 保存模式
        status='queued'
    )
    user.usage_count += 1
    db.session.add(task)
    db.session.commit()
    
    # 将任务丢给后台 RQ Worker 进程
    task_queue.enqueue('backend.worker_engine.process_task', task.id)
    return jsonify({"task_id": task.id, "title": task.title}), 201


@task_bp.route('/stream/<int:task_id>', methods=['GET'])
def stream_results(task_id):
    def generate():
        pubsub = redis_client.pubsub()
        channel_name = f"stream:task:{task_id}"
        pubsub.subscribe(channel_name)
        
        try:
            # 🟢 修复 SyntaxError: 将 json.dumps 提取到变量中，避开 f-string 的反斜杠限制
            import json
            initial_payload = json.dumps({'type': 'block', 'content': '⏳ 已连接到推送通道，等待 AI 响应...\n\n'})
            yield f"data: {initial_payload}\n\n"
            
            for message in pubsub.listen():
                if message['type'] == 'message':
                    raw_data = message['data']
                    yield raw_data
                    
                    if '"type": "done"' in raw_data or '"type": "fatal"' in raw_data:
                        break
        finally:
            pubsub.unsubscribe(channel_name)
            pubsub.close()
            
    return Response(generate(), mimetype='text/event-stream')

@task_bp.route('/history', methods=['GET'])
def get_history():
    username = request.args.get('username', '').strip()
    user = User.query.filter_by(username=username).first()
    if not user: return jsonify({"error": "无权访问"}), 401

    tasks = Task.query.filter_by(user_id=user.id).order_by(Task.id.desc()).limit(50).all()
    result = []
    for t in tasks:
        result.append({
            "id": t.id,
            "title": t.title or "未命名任务",
            "original_text": t.original_text,
            "polished_text": t.polished_text or "",
            "status": t.status,
            "task_type": getattr(t, 'task_type', 'text'), # 告诉前端这是什么类型的任务
            "download_url": f"/api/tasks/download/{t.id}" if getattr(t, 'task_type', 'text') == 'docx' and t.status == 'completed' else "",
            "created_at": t.created_at.strftime("%Y-%m-%d %H:%M:%S") if t.created_at else ""
        })
    return jsonify(result), 200


@task_bp.route('/<int:task_id>/resume', methods=['POST'])
def resume_task(task_id):
    username = request.json.get('username')
    user = User.query.filter_by(username=username).first()
    task = Task.query.get(task_id)

    if not task or not user or task.user_id != user.id:
        return jsonify({"error": "无权操作"}), 403

    if task.status not in ['cancelled', 'failed']:
        return jsonify({"message": "当前状态无法或无需继续执行"}), 400

    # 重置状态，重新入队
    task.status = 'queued'
    db.session.commit()

    task_queue.enqueue('backend.worker_engine.process_task', task.id)
    return jsonify({"message": "任务已恢复"}), 200


@task_bp.route('/upload_docx', methods=['POST'])
def upload_docx():
    if 'file' not in request.files: 
        return jsonify({"error": "未找到文件"}), 400
    
    file = request.files['file']
    username = request.form.get('username')
    mode = request.form.get('mode', 'zh')
    
    user = User.query.filter_by(username=username).first()
    if not user: 
        return jsonify({"error": "用户不存在"}), 403

    # 保存文件到 uploads 目录
    filename = secure_filename(file.filename)
    # 确保项目根目录下有 uploads 文件夹
    save_path = os.path.join('uploads', f"{user.id}_{filename}")
    file.save(save_path)

    # 创建任务
    task = Task(
        user_id=user.id, 
        title=filename[:20], 
        original_text=f"[文档任务] {filename}", 
        mode=mode, 
        status='queued',
        task_type='docx', # 标记为文档任务
        file_path=save_path
    )
    db.session.add(task)
    db.session.commit()
    
    # 异步入队
    task_queue.enqueue('backend.worker_engine.process_task', task.id)
    return jsonify({"task_id": task.id, "title": task.title}), 201


# 🟢 新增：下载润色后的文档
@task_bp.route('/download/<int:task_id>', methods=['GET'])
def download_docx(task_id):
    task = Task.query.get(task_id)
    if not task or task.status != 'completed' or not task.result_file_path:
        return jsonify({"error": "文件不存在或尚未完成"}), 404
    
    # 获取项目绝对路径并拼接
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, '../../'))
    absolute_file_path = os.path.join(project_root, task.result_file_path)
    
    return send_file(absolute_file_path, as_attachment=True, download_name=f"Polished_{task.title}.docx")


@task_bp.route('/<int:task_id>/cancel', methods=['POST'])
def cancel_task(task_id):
    username = request.json.get('username')
    user = User.query.filter_by(username=username).first()
    task = Task.query.get(task_id)
    
    if not task or not user or task.user_id != user.id:
        return jsonify({"error": "无权操作"}), 403
        
    if task.status in ['completed', 'failed', 'cancelled']:
        return jsonify({"message": "任务已结束"}), 200
        
    task.status = 'cancelled'
    db.session.commit()
    
    # 给 Redis 写一个“封杀令”标记
    cancel_key = f"cancel:task:{task_id}"
    redis_client.setex(cancel_key, 3600, "1")
    
    # 广播中断信号
    channel_name = f"stream:task:{task_id}"
    payload = json.dumps({"type": "fatal", "content": "用户主动终止了任务"})
    redis_client.publish(channel_name, f"data: {payload}\n\n")
    
    return jsonify({"message": "指令已发送"}), 200


@task_bp.route('/strategies', methods=['GET'])
def get_strategies():
    from backend.prompts_config import STRATEGIES  # 引入配置
    
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