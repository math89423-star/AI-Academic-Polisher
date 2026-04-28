from __future__ import annotations

from typing import Any, Type

import os
from pprint import pp
from flask import Flask
from flask_cors import CORS

from backend.config import Config
from backend.extensions import db
from backend.paths import get_frontend_dist, get_upload_dir

def create_app(config_class: Type[Any] = Config) -> Flask:
    """
    Flask 应用工厂函数
    """
    # 获取项目根目录 (backend 的上一级)
    base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

    if Config.DEPLOY_MODE == 'desktop':
        static_folder = get_frontend_dist()
    else:
        static_folder = os.path.join(base_dir, 'frontend')

    # 将 Flask 的 static_folder 指向外部的 frontend 目录
    app = Flask(__name__, static_folder=static_folder)
    
    # 导入配置
    app.config.from_object(config_class)
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
    # 启用跨域支持
    CORS(app)

    # 绑定扩展到 app
    db.init_app(app)

    # Desktop 模式：自动创建 SQLite 表结构和管理员账号
    if Config.DEPLOY_MODE == 'desktop':
        with app.app_context():
            from backend.model.models import User, Task, ApiConfig, SystemSetting
            db.create_all()
            if not User.query.filter_by(role='admin').first():
                admin = User(username=Config.ADMIN_USERNAME, role='admin', is_active=True)
                admin.set_password(Config.ADMIN_PASSWORD)
                db.session.add(admin)
                db.session.commit()

    # 在上下文中注册路由蓝图，避免循环导入
    with app.app_context():
        # 按需导入蓝图和模型
        from backend.routes.auth import auth_bp
        from backend.routes.task import task_bp
        from backend.routes.admin import admin_bp
        
        # 🟢 修复：剔除了已废弃的 SystemConfig，补上了 Task
        from backend.model.models import User, Task, ApiConfig, SystemSetting

        # 注册路由前缀
        app.register_blueprint(auth_bp, url_prefix='/api/auth')
        app.register_blueprint(task_bp, url_prefix='/api/tasks')
        app.register_blueprint(admin_bp, url_prefix='/api/admin')


    # 健康检查接口
    @app.route('/api/health')
    def health_check():
        return {"status": "ok", "message": "AI Academic Polisher API is running!"}

    # 上传文件静态服务
    upload_dir = get_upload_dir()

    @app.route('/uploads/<path:filename>')
    def serve_upload(filename):
        from flask import send_from_directory
        return send_from_directory(upload_dir, filename)

    # Desktop 模式：Flask 直接服务前端（无 nginx）
    if Config.DEPLOY_MODE == 'desktop':
        dist_dir = get_frontend_dist()

        @app.route('/')
        def serve_index():
            from flask import send_from_directory
            return send_from_directory(dist_dir, 'index.html')

        @app.route('/admin')
        @app.route('/admin/')
        def serve_admin():
            from flask import send_from_directory
            return send_from_directory(os.path.join(dist_dir, 'admin'), 'index.html')

        @app.route('/assets/<path:filename>')
        def serve_assets(filename):
            from flask import send_from_directory
            return send_from_directory(os.path.join(dist_dir, 'assets'), filename)

    return app