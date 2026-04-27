"""
RQ Worker 启动脚本
"""
import os
from redis import Redis
from rq import Worker

# 从环境变量读取 Redis 配置
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
redis_conn = Redis.from_url(redis_url)

# 启动 Worker 监听 ai_tasks 队列
if __name__ == '__main__':
    worker = Worker(['ai_tasks'], connection=redis_conn)
    worker.work()
