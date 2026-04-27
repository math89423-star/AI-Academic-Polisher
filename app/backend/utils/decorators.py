"""
装饰器工具

提供权限检查、日志记录等装饰器
"""
from __future__ import annotations

from typing import Any, Callable

from functools import wraps
from flask import request, jsonify
from backend.services.user_service import UserService


def require_admin(f: Callable[..., Any]) -> Callable[..., Any]:
    """
    管理员权限装饰器

    用法:
        @admin_bp.route('/users', methods=['GET'])
        @require_admin
        def list_users():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 从请求中获取管理员用户名
        admin_username = request.args.get('admin_username') or \
                        (request.form.get('admin_username') if request.form else None) or \
                        (request.json.get('admin_username') if request.is_json and request.json else None)

        user_service = UserService()
        if not user_service.check_admin(admin_username):
            return jsonify({"error": "无权访问"}), 403

        return f(*args, **kwargs)

    return decorated_function


def require_user(f: Callable[..., Any]) -> Callable[..., Any]:
    """
    用户认证装饰器

    用法:
        @task_bp.route('/create', methods=['POST'])
        @require_user
        def create_task(current_user):
            # current_user 会自动注入
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 从请求中获取用户名
        username = None
        if request.json:
            username = request.json.get('username')
        elif request.form:
            username = request.form.get('username')
        elif request.args:
            username = request.args.get('username')

        if not username:
            return jsonify({"error": "缺少用户名参数"}), 400

        user_service = UserService()
        try:
            user = user_service.authenticate_user(username.strip())
            # 将用户对象注入到函数参数中
            return f(current_user=user, *args, **kwargs)
        except ValueError as e:
            return jsonify({"error": str(e)}), 401

    return decorated_function
