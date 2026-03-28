from __future__ import annotations

import json
import threading
import time
from typing import Any, Optional

from .config import REDIS_URL


class _BaseLiveStateStore:
    def mark_host_live(
        self,
        *,
        user_id: str,
        username: str,
        room_name: str,
        region: str,
        transport: str,
        ttl_seconds: int = 120,
    ) -> None:
        raise NotImplementedError

    def touch_host_live(self, *, user_id: str, ttl_seconds: int = 120) -> None:
        raise NotImplementedError

    def clear_host_live(self, *, user_id: str) -> None:
        raise NotImplementedError

    def host_recent(self, *, user_id: str, ttl_seconds: int = 120) -> bool:
        raise NotImplementedError


class MemoryLiveStateStore(_BaseLiveStateStore):
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._rows: dict[str, dict[str, Any]] = {}

    def mark_host_live(
        self,
        *,
        user_id: str,
        username: str,
        room_name: str,
        region: str,
        transport: str,
        ttl_seconds: int = 120,
    ) -> None:
        now = time.time()
        with self._lock:
            self._rows[user_id] = {
                "user_id": user_id,
                "username": username,
                "room_name": room_name,
                "region": region,
                "transport": transport,
                "updated_at": now,
                "expire_at": now + max(30, ttl_seconds),
            }

    def touch_host_live(self, *, user_id: str, ttl_seconds: int = 120) -> None:
        now = time.time()
        with self._lock:
            row = self._rows.get(user_id)
            if not row:
                return
            row["updated_at"] = now
            row["expire_at"] = now + max(30, ttl_seconds)

    def clear_host_live(self, *, user_id: str) -> None:
        with self._lock:
            self._rows.pop(user_id, None)

    def host_recent(self, *, user_id: str, ttl_seconds: int = 120) -> bool:
        now = time.time()
        with self._lock:
            row = self._rows.get(user_id)
            if not row:
                return False
            expire_at = float(row.get("expire_at") or 0)
            if expire_at < now:
                self._rows.pop(user_id, None)
                return False
            updated_at = float(row.get("updated_at") or 0)
            return now - updated_at <= max(30, ttl_seconds)


class RedisLiveStateStore(_BaseLiveStateStore):
    def __init__(self, redis_url: str) -> None:
        import redis

        self._ttl = 120
        self._redis = redis.Redis.from_url(redis_url, decode_responses=True)

    def _key(self, user_id: str) -> str:
        return f"usking:live:host:{user_id}"

    def mark_host_live(
        self,
        *,
        user_id: str,
        username: str,
        room_name: str,
        region: str,
        transport: str,
        ttl_seconds: int = 120,
    ) -> None:
        ttl = max(30, ttl_seconds)
        payload = {
            "user_id": user_id,
            "username": username,
            "room_name": room_name,
            "region": region,
            "transport": transport,
            "updated_at": time.time(),
        }
        self._redis.set(self._key(user_id), json.dumps(payload), ex=ttl)

    def touch_host_live(self, *, user_id: str, ttl_seconds: int = 120) -> None:
        ttl = max(30, ttl_seconds)
        key = self._key(user_id)
        raw = self._redis.get(key)
        if not raw:
            return
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {}
        payload["updated_at"] = time.time()
        self._redis.set(key, json.dumps(payload), ex=ttl)

    def clear_host_live(self, *, user_id: str) -> None:
        self._redis.delete(self._key(user_id))

    def host_recent(self, *, user_id: str, ttl_seconds: int = 120) -> bool:
        raw = self._redis.get(self._key(user_id))
        if not raw:
            return False
        try:
            payload = json.loads(raw)
        except Exception:
            return True
        updated_at = float(payload.get("updated_at") or 0)
        return time.time() - updated_at <= max(30, ttl_seconds)


def _build_live_state_store() -> _BaseLiveStateStore:
    if REDIS_URL:
        try:
            return RedisLiveStateStore(REDIS_URL)
        except Exception:
            pass
    return MemoryLiveStateStore()


live_state_store = _build_live_state_store()


def host_recent(user_id: Optional[str], ttl_seconds: int = 120) -> bool:
    if not user_id:
        return False
    return live_state_store.host_recent(user_id=user_id, ttl_seconds=ttl_seconds)
