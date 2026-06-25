import hashlib
import json

import redis.asyncio as redis

from app.core.config import settings


class AICache:
    def __init__(self):
        self.redis: redis.Redis | None = None
        self.ttl = 3600  # 1 hour

    async def _get_redis(self) -> redis.Redis:
        if self.redis is None:
            self.redis = redis.from_url(settings.redis_url, decode_responses=True)
        return self.redis

    def _make_key(self, prompt: str, model: str) -> str:
        raw = f"{model}:{prompt}"
        return f"ai:cache:{hashlib.sha256(raw.encode()).hexdigest()}"

    async def get(self, prompt: str, model: str) -> dict | None:
        try:
            r = await self._get_redis()
            key = self._make_key(prompt, model)
            data = await r.get(key)
            return json.loads(data) if data else None
        except Exception:
            return None

    async def set(self, prompt: str, model: str, result: dict) -> None:
        try:
            r = await self._get_redis()
            key = self._make_key(prompt, model)
            await r.setex(key, self.ttl, json.dumps(result))
        except Exception:
            pass

    async def clear(self) -> None:
        try:
            r = await self._get_redis()
            keys = await r.keys("ai:cache:*")
            if keys:
                await r.delete(*keys)
        except Exception:
            pass


ai_cache = AICache()
