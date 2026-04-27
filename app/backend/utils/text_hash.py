from __future__ import annotations

from typing import Any

import hashlib
import json
from datetime import datetime, timedelta

def compute_text_hash(text: str) -> str:
    """计算文本的 SHA-256 哈希值"""
    if not text:
        return ""
    # 标准化文本：去除首尾空白，统一换行符
    normalized = text.strip().replace('\r\n', '\n').replace('\r', '\n')
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

def check_duplicate_text(redis_client: Any, text: str, user_id: int, hours: int = 24) -> dict[str, Any]:
    """
    检查文本是否在指定时间内已处理过

    Args:
        redis_client: Redis 客户端实例
        text: 待检查的文本
        user_id: 用户 ID
        hours: 检查时间范围（小时）

    Returns:
        dict: {
            'is_duplicate': bool,  # 是否重复
            'last_processed': str,  # 上次处理时间（ISO格式）
            'task_id': int  # 上次任务ID
        }
    """
    text_hash = compute_text_hash(text)
    if not text_hash:
        return {'is_duplicate': False}

    # Redis key: text_hash:{user_id}:{hash}
    cache_key = f"text_hash:{user_id}:{text_hash}"

    cached_data = redis_client.get(cache_key)
    if cached_data:
        try:
            data = json.loads(cached_data)
            return {
                'is_duplicate': True,
                'last_processed': data.get('timestamp'),
                'task_id': data.get('task_id')
            }
        except:
            pass

    return {'is_duplicate': False}

def store_text_hash(redis_client: Any, text: str, user_id: int, task_id: int, hours: int = 24) -> None:
    """
    存储文本哈希记录

    Args:
        redis_client: Redis 客户端实例
        text: 文本内容
        user_id: 用户 ID
        task_id: 任务 ID
        hours: 缓存时长（小时）
    """
    text_hash = compute_text_hash(text)
    if not text_hash:
        return

    cache_key = f"text_hash:{user_id}:{text_hash}"
    cache_data = json.dumps({
        'task_id': task_id,
        'timestamp': datetime.utcnow().isoformat(),
        'user_id': user_id
    })

    # 设置过期时间
    redis_client.setex(cache_key, hours * 3600, cache_data)
