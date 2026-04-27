# backend/routes/auth.py
"""
认证路由（重构版）

使用UserService处理业务逻辑
"""
from __future__ import annotations

from typing import Any

from flask import Blueprint, request, jsonify
from backend.services.user_service import UserService
from backend.utils.logging_config import get_logger
import json

auth_bp = Blueprint('auth', __name__)
logger = get_logger(__name__)

def _user_service() -> UserService:
    return UserService()


@auth_bp.route('/login/user', methods=['POST'])
def user_login():
    """普通用户登录（仅需用户名）"""
    data = request.json
    username = data.get('username', '').strip()

    if not username:
        return jsonify({"error": "用户名不能为空"}), 400

    try:
        user = _user_service().authenticate_user(username)
        logger.info(f"用户登录成功: {username}")
        return jsonify({"message": "登录成功", "username": user.username, "role": user.role}), 200

    except ValueError as e:
        logger.warning(f"用户登录失败: {username}, 原因: {str(e)}")
        return jsonify({"error": str(e)}), 401


@auth_bp.route('/login/admin', methods=['POST'])
def admin_login():
    """管理员登录（需用户名和密码）"""
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({"error": "用户名和密码不能为空"}), 400

    try:
        admin = _user_service().authenticate_admin(username, password)
        logger.info(f"管理员登录成功: {username}")
        return jsonify({"message": "管理员登录成功", "username": admin.username, "role": admin.role}), 200

    except ValueError as e:
        logger.warning(f"管理员登录失败: {username}")
        return jsonify({"error": str(e)}), 401


@auth_bp.route('/theme', methods=['GET'])
def get_public_theme():
    """公开接口：获取当前主题配置"""
    from backend.model.models import SystemSetting
    setting = SystemSetting.query.filter_by(key='theme').first()
    if setting and setting.value:
        return jsonify(json.loads(setting.value)), 200
    return jsonify({"primary_color": "#3b82f6", "bg_type": "color", "bg_value": "#f1f5f9"}), 200
