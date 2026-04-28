from flask_sqlalchemy import SQLAlchemy
from concurrent.futures import ThreadPoolExecutor
from backend.config import Config

db = SQLAlchemy()

# 内部协程池 (处理单篇文章的多段落并发)
executor = ThreadPoolExecutor(max_workers=Config.MAX_AI_WORKERS, thread_name_prefix="AI_Worker")

# ================= 根据部署模式初始化后端 =================

if Config.DEPLOY_MODE == 'desktop':
    from backend.memory_backend import MemoryRedis
    from backend.memory_queue import MemoryQueue

    redis_client = MemoryRedis()
    rq_redis = None
    task_queue = MemoryQueue()
else:
    import redis
    from rq import Queue

    # 1. 给 RQ 队列用的连接 (必须传输 bytes，绝对不能加 decode_responses=True)
    rq_redis = redis.from_url(Config.REDIS_URL)
    task_queue = Queue('ai_tasks', connection=rq_redis, default_timeout=3600)

    # 2. 给跨进程流式传输 (Pub/Sub) 用的连接 (解析 SSE 字符串)
    redis_client = redis.from_url(Config.REDIS_URL, decode_responses=True)