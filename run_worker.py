# run_worker.py
import sys
import os

# ==========================================
# 终极杀招：强行把当前 V2.0 目录设为系统最高优先级！
# 任何代码的导入，都必须从这里找，彻底切断与 V1.0 的联系
# ==========================================
current_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, current_dir)

# 强行剔除可能存在的旧路径
# sys.path = [p for p in sys.path if p != '/home/aipolish']

import backend.worker_engine as w

print("\n" + "="*60)
print(f"🔥 [安全检查] Worker 真正加载的核心引擎路径是:\n{w.__file__}")
if "V2.0" not in w.__file__:
    print("❌ 警告：依然加载了旧代码！幽灵未散！")
else:
    print("✅ 路径正确！幽灵已被彻底隔离，引擎已就绪！")
print("="*60 + "\n")

# 🟢 修复点：直接导入 Worker 和 Redis 即可
from redis import Redis
from rq import Worker
from backend.config import Config

if __name__ == '__main__':
    # 连接 Redis
    redis_conn = Redis.from_url(Config.REDIS_URL)
    
    print("🤖 AI Worker 已启动，正在监听 ai_tasks 队列...")
    
    # 🟢 修复点：直接把连接作为参数传给 Worker，去掉 Connection 上下文
    worker = Worker(['ai_tasks'], connection=redis_conn)
    worker.work()