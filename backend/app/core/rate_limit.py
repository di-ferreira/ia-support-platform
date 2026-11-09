"""Rate limiting simples em memória para proteção de endpoints sensíveis.

Observação: o estado é por processo. Para múltiplas instâncias, migrar para Redis.
"""

from collections import defaultdict, deque
from time import time

from fastapi import HTTPException, Request, status


class _InMemoryLimiter:
    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> None:
        now = time()
        bucket = self._hits[key]
        while bucket and bucket[0] < now - self.window:
            bucket.popleft()
        if len(bucket) >= self.limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Muitas requisições; tente novamente em instantes",
            )
        bucket.append(now)


_LIMITERS: list[_InMemoryLimiter] = []


def reset_all() -> None:
    """Zera o estado de todos os limitadores (útil para isolar testes)."""
    for limiter in _LIMITERS:
        limiter._hits.clear()


def rate_limit(limit: int, window_seconds: int):
    limiter = _InMemoryLimiter(limit, window_seconds)
    _LIMITERS.append(limiter)

    async def dependency(request: Request) -> None:
        client = request.client.host if request.client else "unknown"
        key = f"{request.url.path}:{client}"
        limiter.check(key)

    return dependency
