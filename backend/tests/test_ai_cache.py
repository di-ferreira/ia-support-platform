"""14-1 — testes diretos de app/ai/ai_cache.py (sem rede; fake do Redis)."""

from app.ai.ai_cache import AICache


class FakeRedis:
    """Substituto do redis.asyncio.Redis: armazena em dict e registra ttls."""

    def __init__(self, falha: bool = False) -> None:
        self.store: dict[str, str] = {}
        self.ttls: dict[str, int] = {}
        self.expirados: set[str] = set()
        self.deleted: list[str] = []
        self.falha = falha

    def _talar(self) -> None:
        if self.falha:
            raise ConnectionError("redis fora do ar")

    async def get(self, key: str):
        self._talar()
        if key in self.expirados:
            return None
        return self.store.get(key)

    async def setex(self, key: str, ttl: int, value: str) -> None:
        self._talar()
        self.store[key] = value
        self.ttls[key] = ttl

    async def keys(self, pattern: str) -> list[str]:
        self._talar()
        return [k for k in self.store if k not in self.expirados]

    async def delete(self, *keys: str) -> None:
        self._talar()
        self.deleted.extend(keys)
        for k in keys:
            self.store.pop(k, None)
            self.expirados.discard(k)


def _cache(fake: FakeRedis) -> AICache:
    cache = AICache()
    cache.redis = fake  # injeta sem tocar em settings.redis_url (sem rede)
    return cache


async def test_get_miss_retorna_none():
    cache = _cache(FakeRedis())
    assert await cache.get("prompt qualquer", "classify") is None


async def test_set_e_get_hit_retorna_o_mesmo_payload():
    fake = FakeRedis()
    cache = _cache(fake)
    result = {"intencao": "problema_tecnico", "confianca": 0.9}

    await cache.set("prompt qualquer", "classify", result)
    assert await cache.get("prompt qualquer", "classify") == result

    # O mesmo prompt com outro modelo usa outra chave (sem colisão).
    assert await cache.get("prompt qualquer", "outra-modelo") is None
    assert len(fake.store) == 1


async def test_set_grava_com_ttl_de_3600s():
    fake = FakeRedis()
    cache = _cache(fake)

    await cache.set("prompt qualquer", "classify", {"a": 1})

    assert list(fake.ttls.values()) == [3600]


async def test_key_expirada_por_ttl_vira_miss():
    fake = FakeRedis()
    cache = _cache(fake)
    await cache.set("prompt qualquer", "classify", {"a": 1})

    # Simula o Redis expirando a chave após o TTL: o get volta a ser miss.
    fake.expirados.add(list(fake.store)[0])
    assert await cache.get("prompt qualquer", "classify") is None


async def test_clear_remove_todas_as_keys_do_cache():
    fake = FakeRedis()
    cache = _cache(fake)
    await cache.set("prompt A", "classify", {"a": 1})
    await cache.set("prompt B", "diagnose", {"b": 2})

    await cache.clear()

    assert fake.store == {}
    assert await cache.get("prompt A", "classify") is None
    assert await cache.get("prompt B", "diagnose") is None


async def test_clear_sem_keys_nao_chama_delete():
    fake = FakeRedis()
    cache = _cache(fake)

    await cache.clear()

    assert fake.deleted == []


async def test_excecao_no_get_e_engolida_e_retorna_none():
    """Comportamento atual: falha no Redis não derruba o chamador (fail-safe).

    Este teste trava essa decisão para que uma mudança (propagar exceção ou
    silenciar o log) não regreda o endpoint silenciosamente.
    """
    cache = _cache(FakeRedis(falha=True))
    assert await cache.get("prompt qualquer", "classify") is None


async def test_excecao_no_set_e_engolida():
    cache = _cache(FakeRedis(falha=True))
    await cache.set("prompt qualquer", "classify", {"a": 1})  # não propaga


async def test_excecao_no_clear_e_engolida():
    cache = _cache(FakeRedis(falha=True))
    await cache.clear()  # não propaga
