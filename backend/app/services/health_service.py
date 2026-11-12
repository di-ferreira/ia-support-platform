"""Sondas de prontidao (readiness) separadas do liveness."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

Sonda = Callable[[], Awaitable[None]]


class HealthService:
    def __init__(self, sondas: dict[str, Sonda], timeout: float = 2.0) -> None:
        self._sondas = sondas
        self._timeout = timeout

    async def _executar(self, sonda: Sonda) -> dict:
        try:
            await asyncio.wait_for(sonda(), timeout=self._timeout)
            return {"ok": True, "erro": None}
        except TimeoutError:
            return {"ok": False, "erro": f"timeout de {self._timeout}s"}
        except Exception as exc:  # noqa: BLE001 - readiness nunca derruba a rota
            return {"ok": False, "erro": f"{type(exc).__name__}: {exc}"[:200]}

    async def pronto(self) -> dict:
        nomes = list(self._sondas)
        resultados = await asyncio.gather(
            *(self._executar(self._sondas[nome]) for nome in nomes)
        )
        checks = dict(zip(nomes, resultados, strict=True))
        status = "ok" if all(c["ok"] for c in checks.values()) else "degradado"
        return {"status": status, "checks": checks}


def build_health_service(databases, schema_status: dict) -> HealthService:
    """Monta as sondas de readiness.

    `appwrite` toca o serviço real (`databases.list()`); `schema` reflete o
    resultado do bootstrap feito no boot (`app.state.bootstrap`) — com
    bootstrap degradado, o readiness responde 503 sem depender de Appwrite
    estar no ar agora.
    """

    async def appwrite_ok() -> None:
        databases.list()

    async def schema_ok() -> None:
        if not schema_status.get("ok"):
            raise RuntimeError(schema_status.get("erro") or "schema indisponivel")

    return HealthService({"appwrite": appwrite_ok, "schema": schema_ok})
