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

def create_database_if_not_exists() -> None:
    """在初始化 SQLAlchemy 前，先通过原生驱动强制创建数据库 (带智能重试与防乱码机制)"""
    print(f"⏳ 正在检查并创建数据库: {Config.DB_NAME}...")

    max_retries = 20     # 总共尝试 20 次
    retry_interval = 3   # 每次失败后等待 3 秒，总共最多等待 60 秒
    
    for attempt in range(1, max_retries + 1):
        try:
            # 🟢 包含防乱码配置与连接重试
            conn = mysql.connector.connect(
                host=Config.DB_HOST,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
                port=Config.DB_PORT,
                charset='utf8mb4',
                collation='utf8mb4_unicode_ci',
                connect_timeout=10
            )
            cursor = conn.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {Config.DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            cursor.close()
            conn.close()
            print(f"✅ 数据库 {Config.DB_NAME} 准备就绪！")
            return  # 连接成功，直接退出重试循环

        except Exception as e:
            if attempt < max_retries:
                print(f"⚠️ MySQL 尚未完全启动，正在重试 ({attempt}/{max_retries})...")
                time.sleep(retry_interval)
            else:
                print(f"❌ 创建数据库失败，MySQL 启动超时或配置有误。")
                print(f"错误详情: {str(e)}")
                sys.exit(1)

def init_database() -> None:
    """初始化数据库表并插入默认数据"""
    print("=" * 50)
    print("🚀 开始数据库初始化流程")
    print("=" * 50)

    # 步骤1: 创建数据库
    create_database_if_not_exists()

    # 步骤2: 创建表结构
    from backend import create_app
    from backend.extensions import db
    from backend.model import User, ApiConfig, Task, SystemSetting

    app = create_app()
    with app.app_context():
        print("⏳ 正在创建/更新表结构...")
        try:
            db.create_all()
            # 增量迁移：为已有表添加新列
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            if 'users' in inspector.get_table_names():
                columns = [c['name'] for c in inspector.get_columns('users')]
                if 'can_use_strict' not in columns:
                    db.session.execute(text('ALTER TABLE users ADD COLUMN can_use_strict BOOLEAN DEFAULT FALSE'))
                    db.session.commit()
                    print("  ✅ 已添加 can_use_strict 列")
            print("✅ 表结构创建完成")
        except Exception as e:
            print(f"❌ 表结构创建失败: {str(e)}")
            sys.exit(1)

        # 步骤3: 初始化管理员账号
        print("⏳ 正在初始化管理员账号...")
        admin_username = Config.ADMIN_USERNAME
        admin_password = Config.ADMIN_PASSWORD

        try:
            admin = User.query.filter_by(role='admin').first()
            if not admin:
                admin = User(username=admin_username, role='admin', is_active=True)
                admin.set_password(admin_password)
                db.session.add(admin)
                db.session.commit()
                print(f"✅ 成功创建超级管理员: {admin_username}")
            else:
                # 同步最新配置
                admin.username = admin_username
                admin.set_password(admin_password)
                admin.is_active = True
                db.session.commit()
                print(f"✅ 管理员账号已存在，已同步最新配置: {admin_username}")
        except Exception as e:
            print(f"❌ 管理员账号初始化失败: {str(e)}")
            db.session.rollback()
            sys.exit(1)

        print("=" * 50)
        print("🎉 数据库初始化完成！")
        print("=" * 50)

if __name__ == '__main__':
    init_database()