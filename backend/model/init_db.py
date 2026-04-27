# backend/model/init_db.py
import sys
import os
import time  # 🟢 引入时间库用于延迟等待
import mysql.connector

# 将项目根目录加入系统路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../../'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.config import Config

def create_database_if_not_exists():
    """在初始化 SQLAlchemy 前，先通过原生驱动强制创建数据库 (带智能重试与防乱码机制)"""
    print(f"⏳ 正在检查并创建数据库: {Config.DB_NAME}...")
    
    max_retries = 15     # 总共尝试 15 次
    retry_interval = 4   # 每次失败后等待 4 秒，总共最多等待 60 秒
    
    for attempt in range(1, max_retries + 1):
        try:
            # 🟢 包含防乱码配置与连接重试
            conn = mysql.connector.connect(
                host=Config.DB_HOST,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
                port=Config.DB_PORT,
                charset='utf8mb4',                 
                collation='utf8mb4_unicode_ci'     
            )
            cursor = conn.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {Config.DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            cursor.close()
            conn.close()
            print(f"✅ 数据库 {Config.DB_NAME} 准备就绪！")
            return  # 连接成功，直接退出重试循环
            
        except Exception as e:
            print(f"⚠️ MySQL 尚未完全启动，正在重试 ({attempt}/{max_retries})...")
            time.sleep(retry_interval)
            
    # 如果 15 次全失败了，才抛出错误
    print(f"❌ 创建数据库失败，MySQL 启动超时或配置有误。")
    sys.exit(1)

def init_database():
    """初始化数据库表并插入默认数据"""
    create_database_if_not_exists()
    
    from backend import create_app
    from backend.extensions import db
    from backend.model import User
    
    app = create_app()
    with app.app_context():
        print("⏳ 正在检查表结构...")
        db.create_all()

        # 仅保留：检查并同步超级管理员 (从 .env 读取)
        admin_username = Config.ADMIN_USERNAME
        admin_password = Config.ADMIN_PASSWORD

        admin = User.query.filter_by(role='admin').first()
        if not admin:
            admin = User(username=admin_username, role='admin')
            admin.set_password(admin_password) 
            db.session.add(admin)
            print(f"✅ 成功创建超级管理员: {admin_username}")
        else:
            admin.username = admin_username
            admin.set_password(admin_password)
            print(f"ℹ️ 管理员账号已存在，已强制同步 .env 最新配置: {admin_username}")

        db.session.commit()
        print("🎉 数据库动态初始化(管理员部分)完成！")

if __name__ == '__main__':
    init_database()