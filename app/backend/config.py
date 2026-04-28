import os
import sys
from dotenv import load_dotenv

# 加载 .env 环境变量
load_dotenv()


def _resolve_deploy_mode() -> str:
    """解析部署模式：server / desktop / auto（自动检测平台）"""
    mode = os.environ.get('DEPLOY_MODE', 'auto').lower()
    if mode == 'auto':
        return 'desktop' if sys.platform == 'win32' else 'server'
    return mode


class Config:
    # --- 部署模式 ---
    DEPLOY_MODE = _resolve_deploy_mode()

    # --- 服务运行配置 ---
    APP_HOST = os.environ.get('APP_HOST', '127.0.0.1' if DEPLOY_MODE == 'desktop' else '0.0.0.0')
    APP_PORT = int(os.environ.get('APP_PORT', 5000))

    # --- 数据库配置 ---
    if DEPLOY_MODE == 'desktop':
        _db_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
        os.makedirs(_db_dir, exist_ok=True)
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(_db_dir, 'ai_polisher.db')}"
        SQLALCHEMY_ENGINE_OPTIONS = {}
    else:
        DB_USER = os.environ.get('DB_USER', 'root')
        DB_PASSWORD = os.environ.get('DB_PASSWORD', '123456')
        DB_HOST = os.environ.get('DB_HOST', '127.0.0.1')
        DB_PORT = os.environ.get('DB_PORT', '3306')
        DB_NAME = os.environ.get('DB_NAME', 'ai_polisher')
        SQLALCHEMY_DATABASE_URI = f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
        SQLALCHEMY_ENGINE_OPTIONS = {
            "pool_size": 16,
            "max_overflow": 24,
            "pool_recycle": 1800,
            "pool_pre_ping": True,
            "pool_timeout": 30,
            "connect_args": {"charset": "utf8mb4", "collation": "utf8mb4_unicode_ci"}
        }

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # --- AI 全局默认配置 ---
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', 'your-api-key')
    OPENAI_BASE_URL = os.environ.get('OPENAI_BASE_URL', 'https://api.openai.com/v1')
    MODEL_NAME = os.environ.get('MODEL_NAME', 'gemini-2.5-pro')

    # --- Redis 与并发配置 ---
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0')
    MAX_AI_WORKERS = int(os.environ.get('MAX_AI_WORKERS', 32))

    # [新增] --- 管理员配置 ---
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', '123456')


class WorkerConfig:
    """Worker任务处理配置"""
    MAX_WORKERS = int(os.environ.get('MAX_AI_WORKERS', 32))
    TEXT_CHUNK_SIZE = int(os.environ.get('TEXT_CHUNK_SIZE', 1500))
    RETRY_TIMES = int(os.environ.get('RETRY_TIMES', 3))
    RETRY_DELAY_BASE = int(os.environ.get('RETRY_DELAY_BASE', 2))  # 指数退避基数

    @staticmethod
    def get_chunk_size() -> int:
        """从数据库读取分块大小，失败时回退到环境变量默认值"""
        try:
            from backend.model.models import SystemSetting
            setting = SystemSetting.query.filter_by(key='chunk_size').first()
            if setting and setting.value:
                return int(setting.value)
        except Exception:
            pass
        return WorkerConfig.TEXT_CHUNK_SIZE


class SSEConfig:
    """SSE流式推送配置"""
    TIMEOUT = int(os.environ.get('SSE_TIMEOUT', 600))  # 10分钟
    HEARTBEAT_INTERVAL = int(os.environ.get('SSE_HEARTBEAT', 5))  # 心跳间隔


class RedisConfig:
    """Redis缓存配置"""
    CANCEL_KEY_TTL = int(os.environ.get('CANCEL_KEY_TTL', 3600))
    TEXT_HASH_TTL = int(os.environ.get('TEXT_HASH_TTL', 24))


class RedisKeyManager:
    """统一管理所有 Redis key 的生成，避免硬编码散落各处"""

    @staticmethod
    def cancel_key(task_id: int) -> str:
        return f"cancel:task:{task_id}"

    @staticmethod
    def stream_channel(task_id: int) -> str:
        return f"stream:task:{task_id}"

    @staticmethod
    def progress_key(task_id: int) -> str:
        return f"text_progress:task:{task_id}"

    @staticmethod
    def docx_done_key(task_id: int) -> str:
        return f"docx_done_indices:task:{task_id}"

    @staticmethod
    def docx_progress_key(task_id: int) -> str:
        return f"docx_progress:task:{task_id}"
