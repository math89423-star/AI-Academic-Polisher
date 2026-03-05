from flask import Blueprint, request, jsonify
from backend.extensions import db
from backend.model import User, ApiConfig, Task # 🟢 引入 Task 以便清理数据

admin_bp = Blueprint('admin', __name__)

def check_admin(username):
    user = User.query.filter_by(username=username).first()
    return user and user.role == 'admin'

# === API 渠道管理 ===
@admin_bp.route('/api_configs', methods=['GET'])
def list_api_configs():
    if not check_admin(request.args.get('username')): return jsonify({"error": "无权访问"}), 403
    configs = ApiConfig.query.all()
    return jsonify([{
        "id": c.id, "name": c.name, "api_key": c.api_key, 
        "base_url": c.base_url, "model_name": c.model_name
    } for c in configs])

@admin_bp.route('/api_configs', methods=['POST'])
def add_api_config():
    data = request.json
    if not check_admin(data.get('admin_username')): return jsonify({"error": "无权访问"}), 403
    
    new_conf = ApiConfig(
        name=data['name'], api_key=data['api_key'], 
        base_url=data['base_url'], model_name=data.get('model_name', 'gpt-3.5-turbo')
    )
    db.session.add(new_conf)
    db.session.commit()
    return jsonify({"message": "API渠道添加成功"})

@admin_bp.route('/api_configs/<int:config_id>', methods=['DELETE'])
def delete_api_config(config_id):
    """【新功能】安全删除 API 线路"""
    admin_username = request.args.get('admin_username')
    if not check_admin(admin_username): 
        return jsonify({"error": "无权访问"}), 403
    
    config = ApiConfig.query.get(config_id)
    if not config: 
        return jsonify({"error": "该线路不存在"}), 404

    # 安全保护：防止管理员手滑把所有线路删光，导致系统彻底瘫痪
    if ApiConfig.query.count() <= 1:
        return jsonify({"error": "系统必须至少保留一条可用线路！"}), 400

    # 🟢 级联保护：找出所有绑定了这条线路的用户，将其退回“未分配”状态
    users_using_this = User.query.filter_by(api_config_id=config_id).all()
    for u in users_using_this:
        u.api_config_id = None
        
    db.session.delete(config)
    db.session.commit()
    return jsonify({"message": "线路已安全删除"})

# === 用户管理 (修改为支持绑定渠道) ===
@admin_bp.route('/users', methods=['GET'])
def list_users():
    if not check_admin(request.args.get('username')): return jsonify({"error": "无权访问"}), 403
    users = User.query.order_by(User.id.desc()).all()
    return jsonify([{
        "id": u.id, "username": u.username, "usage_count": u.usage_count, 
        "is_active": u.is_active, "role": u.role,
        "api_config_id": u.api_config_id, # 🟢 返回当前绑定的线路ID
        "api_config_name": u.api_config.name if u.api_config else "未分配"
    } for u in users])

@admin_bp.route('/users', methods=['POST'])
def add_user():
    data = request.json
    if not check_admin(data.get('admin_username')): return jsonify({"error": "无权访问"}), 403
    
    new_username = data.get('new_username')
    if User.query.filter_by(username=new_username).first():
        return jsonify({"error": "用户名已存在"}), 400

    new_user = User(
        username=new_username, 
        role=data.get('role', 'user'),
        api_config_id=data.get('api_config_id') # [核心] 分配指定的 API 渠道
    )
    if new_user.role == 'admin' and data.get('password'):
        new_user.set_password(data.get('password'))
        
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": "账号创建成功"})

@admin_bp.route('/users/<string:target_username>', methods=['DELETE'])
def delete_user(target_username):
    """【新功能】物理删除用户及其关联的任务记录"""
    admin_username = request.args.get('admin_username')
    if not check_admin(admin_username): return jsonify({"error": "无权访问"}), 403
    
    user = User.query.filter_by(username=target_username).first()
    if not user: return jsonify({"error": "用户不存在"}), 404
    
    # 级联删除：先清理该用户的所有任务记录，再删除用户
    Task.query.filter_by(user_id=user.id).delete()
    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": f"用户 {target_username} 及其所有记录已彻底清除"})

@admin_bp.route('/users/update_config', methods=['POST'])
def update_user_api_config():
    """【新功能】在线修改用户的 API 线路组"""
    data = request.json
    if not check_admin(data.get('admin_username')): return jsonify({"error": "无权访问"}), 403
    
    user = User.query.filter_by(username=data.get('target_username')).first()
    if not user: return jsonify({"error": "用户不存在"}), 404
    
    # 更新绑定的 API 线路 ID
    user.api_config_id = data.get('api_config_id')
    db.session.commit()
    return jsonify({"message": "用户线路配置更新成功，下次任务即刻生效！"})