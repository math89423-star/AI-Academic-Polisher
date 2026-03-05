# backend/model/init_db.py
import sys
import os
import mysql.connector

# 将项目根目录加入系统路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../../'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.config import Config

def create_database_if_not_exists():
    """在初始化 SQLAlchemy 前，先通过原生驱动强制创建数据库"""
    print(f"⏳ 正在检查并创建数据库: {Config.DB_NAME}...")
    try:
        # 此时不要连接具体的 DB_NAME，而是直接连 MySQL 服务器
        conn = mysql.connector.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            port=Config.DB_PORT
        )
        cursor = conn.cursor()
        # 执行建库语句，并指定字符集支持完整的中文及表情符
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {Config.DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        cursor.close()
        conn.close()
        print(f"✅ 数据库 {Config.DB_NAME} 准备就绪！")
    except Exception as e:
        print(f"❌ 创建数据库失败，请检查 MySQL 账号密码或网络: {e}")
        sys.exit(1)

def init_database():
    """初始化数据库表并插入默认数据"""
    # 1. 强制建库
    create_database_if_not_exists()
    
    # 2. 导入 Flask 应用并建表
    from backend import create_app
    from backend.extensions import db
    from backend.model import User, ApiConfig
    
    app = create_app()
    with app.app_context():
        print("⏳ 正在创建表结构...")
        db.create_all()

        # 3. 检查并同步超级管理员 (从 .env 读取)
        admin_username = Config.ADMIN_USERNAME
        admin_password = Config.ADMIN_PASSWORD

        # 寻找系统中现有的管理员账号
        admin = User.query.filter_by(role='admin').first()
        
        if not admin:
            # 如果没有管理员，新建一个
            admin = User(username=admin_username, role='admin')
            admin.set_password(admin_password) 
            db.session.add(admin)
            print(f"✅ 成功创建超级管理员: {admin_username}")
        else:
            # 如果已经存在，直接覆写更新为 .env 中的最新账号和密码
            admin.username = admin_username
            admin.set_password(admin_password)
            print(f"ℹ️ 管理员账号已存在，已强制同步 .env 最新配置: {admin_username}")

        # 4. 生成默认 API 渠道
        default_api = ApiConfig.query.first()
        if not default_api:
            default_api = ApiConfig(
                name="全局默认线路",
                api_key="sk-your-api-key-here",
                base_url="https://api.openai.com/v1",
                model_name="gpt-3.5-turbo"
            )
            db.session.add(default_api)
            print("✅ 成功创建默认 API 渠道")
        else:
            print("ℹ️ API 渠道已存在，跳过创建。")

        db.session.commit()
        print("🎉 数据库初始化/更新完成！")

if __name__ == '__main__':
    init_database()