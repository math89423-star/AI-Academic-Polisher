import os
from pprint import pp
from flask import Flask
from flask_cors import CORS

from backend.config import Config
from backend.extensions import db

def create_app(config_class=Config):
    """
    Flask 应用工厂函数
    """
    # 获取项目根目录 (backend 的上一级)
    base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    frontend_dir = os.path.join(base_dir, 'frontend')

    # 将 Flask 的 static_folder 指向外部的 frontend 目录
    app = Flask(__name__, static_folder=frontend_dir)
    
    # 导入配置
    app.config.from_object(config_class)
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
    # 启用跨域支持
    CORS(app)

    # 绑定扩展到 app
    db.init_app(app)

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
        return {"status": "ok", "message": "AI Polisher API is running!"}

    # 上传文件静态服务
    upload_dir = os.path.join(base_dir, 'uploads')
    os.makedirs(upload_dir, exist_ok=True)

    @app.route('/uploads/<path:filename>')
    def serve_upload(filename):
        from flask import send_from_directory
        return send_from_directory(upload_dir, filename)

    return app