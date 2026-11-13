"""08-11 — resiliência HTTP: timeout explícito e retry com backoff + jitter.

Usa ``httpx.MockTransport`` e monkeypatch de ``asyncio.sleep`` (os atrasos
são registrados, nunca dormidos de verdade).
"""

import asyncio

import httpx
import pytest

from app.core.config import settings
from app.core.resiliencia import requisitar
from app.services.evolution_service import EvolutionService


class AtrasosRegistrados:
    """Substituto de asyncio.sleep que registra os valores sem dormir."""

    def __init__(self) -> None:
        self.valores: list[float] = []

    async def __call__(self, segundos: float) -> None:
        self.valores.append(segundos)


def _client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _sem_dormir(monkeypatch: pytest.MonkeyPatch) -> AtrasosRegistrados:
    atrasos = AtrasosRegistrados()
    monkeypatch.setattr(asyncio, "sleep", atrasos)
    return atrasos


# ------------------------------------------------------------- status transitórios


async def test_503_na_primeira_e_200_na_segunda_repete_uma_vez(monkeypatch):
    atrasos = _sem_dormir(monkeypatch)
    chamadas = 0

    def handler(request):
        nonlocal chamadas
        chamadas += 1
        if chamadas == 1:
            return httpx.Response(503)
        return httpx.Response(200, json={"ok": True})

    async with _client(handler) as client:
        resposta = await requisitar(client, "GET", "http://teste/ok")

    assert resposta.status_code == 200
    assert resposta.json() == {"ok": True}
    assert chamadas == 2
    assert len(atrasos.valores) == 1


async def test_429_com_retry_after_uso_valor_como_piso(monkeypatch):
    atrasos = _sem_dormir(monkeypatch)
    chamadas = 0

    def handler(request):
        nonlocal chamadas
        chamadas += 1
        if chamadas == 1:
            return httpx.Response(429, headers={"Retry-After": "2"})
        return httpx.Response(200)

    async with _client(handler) as client:
        resposta = await requisitar(client, "GET", "http://teste/429")

    assert resposta.status_code == 200
    assert len(atrasos.valores) == 1
    assert atrasos.valores[0] >= 2.0


# ------------------------------------------------------------- sem retry indevido


async def test_404_nao_repete(monkeypatch):
    atrasos = _sem_dormir(monkeypatch)
    chamadas = 0

    def handler(request):
        nonlocal chamadas
        chamadas += 1
        return httpx.Response(404, json={"error": "not found"})

    async with _client(handler) as client:
        resposta = await requisitar(client, "GET", "http://teste/404")

    assert resposta.status_code == 404
    assert chamadas == 1
    assert atrasos.valores == []


async def test_erro_de_programacao_propaga_sem_retry(monkeypatch):
    _sem_dormir(monkeypatch)
    chamadas = 0

    def handler(request):
        nonlocal chamadas
        chamadas += 1
        raise KeyError("falha de programação")

    async with _client(handler) as client:
        with pytest.raises(KeyError):
            await requisitar(client, "GET", "http://teste/boom")

    assert chamadas == 1


# ------------------------------------------------------------- esgotamento e backoff


async def test_connect_error_persistente_esgota_tentativas_e_relevanta(
    monkeypatch,
):
    atrasos = _sem_dormir(monkeypatch)
    chamadas = 0

    def handler(request):
        nonlocal chamadas
        chamadas += 1
        raise httpx.ConnectError("conexão recusada")

    async with _client(handler) as client:
        with pytest.raises(httpx.ConnectError):
            await requisitar(client, "GET", "http://teste/falha")

    assert chamadas == settings.http_max_tentativas
    assert len(atrasos.valores) == settings.http_max_tentativas - 1


async def test_atrasos_crescem_entre_tentativas(monkeypatch):
    atrasos = _sem_dormir(monkeypatch)
    chamadas = 0

    def handler(request):
        nonlocal chamadas
        chamadas += 1
        if chamadas < settings.http_max_tentativas:
            return httpx.Response(500)
        return httpx.Response(200)

    async with _client(handler) as client:
        resposta = await requisitar(
            client,
            "GET",
            "http://teste/crescimento",
            tentativas=3,
            base_s=0.5,
            maximo_s=8.0,
        )

    assert resposta.status_code == 200
    assert len(atrasos.valores) == 2
    assert atrasos.valores[1] > atrasos.valores[0]


async def test_atrasos_nunca_passam_do_maximo(monkeypatch):
    atrasos = _sem_dormir(monkeypatch)
    chamadas = 0

    def handler(request):
        nonlocal chamadas
        chamadas += 1
        if chamadas < 5:
            return httpx.Response(502)
        return httpx.Response(200)

    async with _client(handler) as client:
        await requisitar(
            client, "GET", "http://teste/maximo", tentativas=5, base_s=0.5, maximo_s=1.0
        )

    assert len(atrasos.valores) == 4
    assert all(atraso <= 1.0 for atraso in atrasos.valores)


# ------------------------------------------------------------- EvolutionService


async def test_evolution_service_502_502_e_200_sai_sucesso(monkeypatch):
    atrasos = _sem_dormir(monkeypatch)
    chamadas = 0
    corpo_ok = {"instance": {"instanceName": "emsoft-support"}, "hash": "qr"}

    def handler(request):
        nonlocal chamadas
        chamadas += 1
        if chamadas < 3:
            return httpx.Response(502)
        return httpx.Response(201, json=corpo_ok)

    service = EvolutionService(transport=httpx.MockTransport(handler))
    resultado = await service.criar_instancia("emsoft-support")

    assert resultado == corpo_ok
    assert chamadas == 3
    assert len(atrasos.valores) == 2
