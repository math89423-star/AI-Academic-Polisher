"""Redis 缓存清理工具 - 定期清理过期的任务缓存"""
import redis
from backend.config import Config

def cleanup_old_task_cache(redis_client, hours=24):
    """清理超过指定小时数的任务相关缓存"""
    patterns = [
        "text_progress:task:*",
        "docx_done_indices:task:*",
        "docx_progress:task:*",
        "cancel:task:*",
        "text_hash:*"
    ]

    cleaned_count = 0
    for pattern in patterns:
        cursor = 0
        while True:
            cursor, keys = redis_client.scan(cursor, match=pattern, count=100)
            for key in keys:
                # 检查 TTL，如果没有设置过期时间或已过期很久，删除
                ttl = redis_client.ttl(key)
                if ttl == -1:  # 没有设置过期时间
                    redis_client.delete(key)
                    cleaned_count += 1
            if cursor == 0:
                break

    return cleaned_count

def cleanup_orphaned_workers(redis_client):
    """清理孤儿 worker 注册信息"""
    # 获取所有 worker keys
    worker_keys = []
    cursor = 0
    while True:
        cursor, keys = redis_client.scan(cursor, match="rq:worker:*", count=100)
        worker_keys.extend(keys)
        if cursor == 0:
            break

    cleaned = 0
    for key in worker_keys:
        # 检查 worker 是否还活着（通过心跳时间判断）
        if redis_client.type(key) == b'hash':
            birth = redis_client.hget(key, 'birth')
            if not birth:
                redis_client.delete(key)
                cleaned += 1

    return cleaned

if __name__ == '__main__':
    redis_conn = redis.from_url(Config.REDIS_URL, decode_responses=True)

    print("🧹 开始清理 Redis 缓存...")
    task_cleaned = cleanup_old_task_cache(redis_conn)
    worker_cleaned = cleanup_orphaned_workers(redis_conn)

    print(f"✅ 清理完成：")
    print(f"   - 任务缓存: {task_cleaned} 个")
    print(f"   - 孤儿 Worker: {worker_cleaned} 个")
