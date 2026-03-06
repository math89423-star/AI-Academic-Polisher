from flask import Blueprint, request, jsonify
from backend.extensions import db
from backend.model import User, ApiConfig, Task

admin_bp = Blueprint('admin', __name__)

def check_admin(username):
    user = User.query.filter_by(username=username).first()
    return user and user.role == 'admin'


# === 用户管理 ===
@admin_bp.route('/users', methods=['GET'])
def list_users():
    # 🟢 修复：统一鉴权参数为 admin_username
    if not check_admin(request.args.get('admin_username')): return jsonify({"error": "无权访问"}), 403
    users = User.query.all()
    return jsonify([{
        "id": u.id, "username": u.username, "role": u.role,
        "usage_count": u.usage_count, "api_config_id": u.api_config_id
    } for u in users])

@admin_bp.route('/users', methods=['POST'])
def add_user():
    data = request.json
    if not check_admin(data.get('admin_username')): return jsonify({"error": "无权访问"}), 403
    
    if User.query.filter_by(username=data['new_username']).first():
        return jsonify({"error": "该用户名已存在"}), 400
        
    # 防止前端传来的 "" 空字符串撑爆 Integer 字段
    api_config_id = data.get('api_config_id')
    api_config_id = api_config_id if api_config_id else None

    new_user = User(
        username=data['new_username'],
        role=data.get('role', 'user'),
        api_config_id=api_config_id 
    )
    if new_user.role == 'admin' and data.get('password'):
        new_user.set_password(data.get('password'))
        
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": "账号创建成功"})

@admin_bp.route('/users/update_config', methods=['POST'])
def update_user_api_config():
    data = request.json
    if not check_admin(data.get('admin_username')): return jsonify({"error": "无权访问"}), 403
    
    user = User.query.filter_by(username=data['target_username']).first()
    if not user: return jsonify({"error": "用户不存在"}), 404
    
    # 安全处理线路置空
    api_config_id = data.get('api_config_id')
    user.api_config_id = api_config_id if api_config_id else None
    
    db.session.commit()
    return jsonify({"message": "配置更新成功"})

@admin_bp.route('/users/<string:target_username>', methods=['DELETE'])
def delete_user(target_username):
    admin_username = request.args.get('admin_username')
    if not check_admin(admin_username): return jsonify({"error": "无权访问"}), 403
    
    user = User.query.filter_by(username=target_username).first()
    if not user: return jsonify({"error": "用户不存在"}), 404
    
    Task.query.filter_by(user_id=user.id).delete()
    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": f"用户 {target_username} 及其所有记录已彻底清除"})


# === API 渠道管理 ===
@admin_bp.route('/api_configs', methods=['GET'])
def list_api_configs():
    if not check_admin(request.args.get('admin_username')): return jsonify({"error": "无权访问"}), 403
    configs = ApiConfig.query.all()
    return jsonify([{
        "id": c.id, "name": c.name, "api_key": c.api_key, 
        "base_url": c.base_url, "model_name": c.model_name
    } for c in configs])

# 创建大模型 API 线路
@admin_bp.route('/api_configs', methods=['POST'])
def add_api_config():
    data = request.json
    if not check_admin(data.get('admin_username')): return jsonify({"error": "无权访问"}), 403
    
    try:
        new_conf = ApiConfig(
            name=data.get('name', '').strip(), 
            api_key=data.get('api_key', '').strip(), 
            base_url=data.get('base_url', '').strip(), 
            model_name=data.get('model_name', 'gpt-3.5-turbo').strip()
        )
        db.session.add(new_conf)
        db.session.commit()
        return jsonify({"message": "API线路创建成功"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "创建失败，请检查线路名称是否重复"}), 400

# 删除大模型 API 线路
@admin_bp.route('/api_configs/<int:config_id>', methods=['DELETE'])
def delete_api_config(config_id):
    if not check_admin(request.args.get('admin_username')): return jsonify({"error": "无权访问"}), 403
    
    conf = ApiConfig.query.get(config_id)
    if not conf: return jsonify({"error": "线路不存在"}), 404
    
    # 如果删除了线路，把正在使用该线路的用户回退到系统默认线路 (None)
    User.query.filter_by(api_config_id=config_id).update({'api_config_id': None})
    
    db.session.delete(conf)
    db.session.commit()
    return jsonify({"message": "线路已彻底销毁"})