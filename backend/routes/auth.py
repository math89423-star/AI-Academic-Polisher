# backend/routes/auth.py
from flask import Blueprint, request, jsonify
from backend.extensions import db
from backend.model.models import User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login/user', methods=['POST'])
def user_login():
    """普通用户登录（仅需用户名）"""
    data = request.json
    username = data.get('username', '').strip()
    
    if not username: return jsonify({"error": "用户名不能为空"}), 400

    user = User.query.filter_by(username=username, role='user').first()
    
    # 如果系统设计为公开使用，可以保留自动注册逻辑；如果是封闭系统，这里可以改为直接返回 401 报错
    if not user:
        user = User(username=username, role='user')
        db.session.add(user)
        db.session.commit()

    if not user.is_active:
        return jsonify({"error": "该账户已被管理员封禁"}), 403

    return jsonify({"message": "登录成功", "username": user.username}), 200

@auth_bp.route('/login/admin', methods=['POST'])
def admin_login():
    """管理员登录（需用户名和密码）"""
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    if not username or not password:
        return jsonify({"error": "用户名和密码不能为空"}), 400

    user = User.query.filter_by(username=username, role='admin').first()
    
    if not user or not user.check_password(password):
        return jsonify({"error": "管理员账号或密码错误"}), 401

    if not user.is_active:
        return jsonify({"error": "该管理员账户已被停用"}), 403

    return jsonify({"message": "管理员登录成功", "username": user.username}), 200