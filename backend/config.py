import os
from dotenv import load_dotenv

# 加载 .env 环境变量
load_dotenv()

class Config:
    # --- 服务运行配置 ---
    APP_HOST = os.environ.get('APP_HOST', '0.0.0.0')
    APP_PORT = int(os.environ.get('APP_PORT', 5000))

    # --- 数据库配置 ---
    DB_USER = os.environ.get('DB_USER', 'root')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', '123456')
    DB_HOST = os.environ.get('DB_HOST', '127.0.0.1')
    DB_PORT = os.environ.get('DB_PORT', '3306')
    DB_NAME = os.environ.get('DB_NAME', 'ai_polisher')
    
    SQLALCHEMY_DATABASE_URI = f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 高并发数据库连接池配置（优化：避免连接池过大）
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 16,           # 降低基础连接池（4 gunicorn workers + 余量）
        "max_overflow": 24,        # 降低溢出连接数
        "pool_recycle": 1800,
        "pool_pre_ping": True,
        "pool_timeout": 30,
        "connect_args": {"charset": "utf8mb4", "collation": "utf8mb4_unicode_ci"}
    }
    # --- AI 全局默认配置 ---
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', 'your-api-key')
    OPENAI_BASE_URL = os.environ.get('OPENAI_BASE_URL', 'https://api.openai.com/v1')
    MODEL_NAME = os.environ.get('MODEL_NAME', 'gemini-2.5-pro')

    # --- Redis 与并发配置 ---
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0')
    MAX_AI_WORKERS = int(os.environ.get('MAX_AI_WORKERS',32))

    # [新增] --- 管理员配置 ---
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', '123456')
