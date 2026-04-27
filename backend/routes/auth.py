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
    
    if not username: 
        return jsonify({"error": "用户名不能为空"}), 400

    user = User.query.filter_by(username=username, role='user').first()
    
    # 如果数据库里没有这个用户，直接返回 401 未授权错误，不再自动创建。
    if not user:
        return jsonify({"error": "该账号未注册，请联系管理员分配"}), 401

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
        
    admin = User.query.filter_by(username=username, role='admin').first()
    if not admin or not admin.check_password(password):
        return jsonify({"error": "管理员账号或密码错误"}), 401
        
    return jsonify({"message": "管理员登录成功", "username": admin.username}), 200