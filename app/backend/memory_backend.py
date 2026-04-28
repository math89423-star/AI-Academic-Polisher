"""
内存 Redis 替代 — desktop 模式下替代真实 Redis
线程安全，支持 KV / Hash / Set / PubSub / TTL
"""
import time
import json
import threading
import queue
from typing import Any, Optional


class MemoryPubSub:
    """内存 Pub/Sub 订阅端，模拟 redis.client.PubSub 接口"""

    def __init__(self, broker: 'MemoryRedis') -> None:
        self._broker = broker
        self._queue: queue.Queue = queue.Queue()
        self._channels: list[str] = []

    def subscribe(self, *channels: str) -> None:
        for ch in channels:
            self._channels.append(ch)
            self._broker._add_subscriber(ch, self._queue)

    def get_message(self, timeout: float = 1.0) -> Optional[dict]:
        try:
            msg = self._queue.get(timeout=timeout)
            return msg
        except queue.Empty:
            return None

    def unsubscribe(self, *channels: str) -> None:
        targets = channels if channels else list(self._channels)
        for ch in targets:
            self._broker._remove_subscriber(ch, self._queue)
            if ch in self._channels:
                self._channels.remove(ch)

    def close(self) -> None:
        self.unsubscribe()


class MemoryRedis:
    """
    线程安全的内存 Redis 替代。
    只实现项目实际用到的 API 表面，不追求完整 Redis 兼容。
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data: dict[str, Any] = {}
        self._expiry: dict[str, float] = {}
        # PubSub: channel -> list[queue.Queue]
        self._subscribers: dict[str, list[queue.Queue]] = {}
        self._sub_lock = threading.Lock()

    # ── 内部 TTL 检查 ──

    def _is_expired(self, key: str) -> bool:
        if key in self._expiry and time.time() > self._expiry[key]:
            self._data.pop(key, None)
            self._expiry.pop(key, None)
            return True
        return False

    # ── KV 操作 ──

    def get(self, key: str) -> Optional[str]:
        with self._lock:
            if self._is_expired(key):
                return None
            return self._data.get(key)

    def set(self, key: str, value: str) -> None:
        with self._lock:
            self._data[key] = value

    def setex(self, key: str, ttl: int, value: str) -> None:
        with self._lock:
            self._data[key] = value
            self._expiry[key] = time.time() + ttl

    def exists(self, key: str) -> bool:
        with self._lock:
            if self._is_expired(key):
                return False
            return key in self._data

    def delete(self, *keys: str) -> int:
        count = 0
        with self._lock:
            for key in keys:
                if self._data.pop(key, None) is not None:
                    count += 1
                self._expiry.pop(key, None)
        return count

    # ── Hash 操作 ──

    def hgetall(self, key: str) -> dict:
        with self._lock:
            self._is_expired(key)
            val = self._data.get(key)
            if isinstance(val, dict):
                return dict(val)
            return {}

    def hset(self, key: str, field: str, value: str) -> None:
        with self._lock:
            if key not in self._data or not isinstance(self._data[key], dict):
                self._data[key] = {}
            self._data[key][field] = value

    def hlen(self, key: str) -> int:
        with self._lock:
            self._is_expired(key)
            val = self._data.get(key)
            if isinstance(val, dict):
                return len(val)
            return 0

    # ── Set 操作 ──

    def smembers(self, key: str) -> set:
        with self._lock:
            self._is_expired(key)
            val = self._data.get(key)
            if isinstance(val, set):
                return set(val)
            return set()

    def sadd(self, key: str, *values: Any) -> int:
        with self._lock:
            if key not in self._data or not isinstance(self._data[key], set):
                self._data[key] = set()
            before = len(self._data[key])
            self._data[key].update(values)
            return len(self._data[key]) - before

    # ── Pub/Sub ──

    def _add_subscriber(self, channel: str, q: queue.Queue) -> None:
        with self._sub_lock:
            if channel not in self._subscribers:
                self._subscribers[channel] = []
            self._subscribers[channel].append(q)

    def _remove_subscriber(self, channel: str, q: queue.Queue) -> None:
        with self._sub_lock:
            if channel in self._subscribers:
                try:
                    self._subscribers[channel].remove(q)
                except ValueError:
                    pass

    def publish(self, channel: str, message: str) -> int:
        with self._sub_lock:
            subs = list(self._subscribers.get(channel, []))
        for q in subs:
            q.put({"type": "message", "channel": channel, "data": message})
        return len(subs)

    def pubsub(self) -> MemoryPubSub:
        return MemoryPubSub(self)
