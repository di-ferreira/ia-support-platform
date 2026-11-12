"""Readiness separa liveness de dependencias reais (gaps 08-3/08-12)."""

import asyncio

import pytest

from app.main import app
from app.services.health_service import HealthService, build_health_service


async def _ok() -> None:
    return None


async def _falha() -> None:
    raise RuntimeError("appwrite fora do ar")


async def _lenta() -> None:
    await asyncio.sleep(5)


class _DatabasesOk:
    def list(self):
        return None


class _DatabasesFora:
    def list(self):
        raise RuntimeError("appwrite fora do ar")


@pytest.mark.asyncio
async def test_tudo_ok_retorna_status_ok():
    saude = HealthService({"appwrite": _ok, "schema": _ok}, timeout=0.5)

    resultado = await saude.pronto()

    assert resultado["status"] == "ok"
    assert resultado["checks"]["appwrite"] == {"ok": True, "erro": None}


@pytest.mark.asyncio
async def test_uma_falha_degrada_sem_esconder_as_outras():
    saude = HealthService({"appwrite": _ok, "schema": _falha}, timeout=0.5)

    resultado = await saude.pronto()

    assert resultado["status"] == "degradado"
    assert resultado["checks"]["appwrite"]["ok"] is True
    assert resultado["checks"]["schema"]["ok"] is False
    assert "appwrite fora do ar" in resultado["checks"]["schema"]["erro"]


@pytest.mark.asyncio
async def test_sonda_lenta_estoura_no_timeout_sem_barrar_as_outras():
    saude = HealthService({"appwrite": _ok, "ollama": _lenta}, timeout=0.05)

    resultado = await saude.pronto()

    assert resultado["status"] == "degradado"
    assert resultado["checks"]["appwrite"]["ok"] is True
    assert resultado["checks"]["ollama"]["ok"] is False
    assert "timeout" in resultado["checks"]["ollama"]["erro"].lower()


@pytest.mark.asyncio
async def test_bootstrap_ok_mantem_readiness_verde():
    saude = build_health_service(_DatabasesOk(), {"ok": True, "erro": None})

    resultado = await saude.pronto()

    assert resultado["status"] == "ok"
    assert resultado["checks"]["schema"] == {"ok": True, "erro": None}


@pytest.mark.asyncio
async def test_bootstrap_degradado_degrada_readiness():
    saude = build_health_service(
        _DatabasesOk(), {"ok": False, "erro": "appwrite fora do ar"}
    )

    resultado = await saude.pronto()

    assert resultado["status"] == "degradado"
    assert resultado["checks"]["schema"] == {
        "ok": False,
        "erro": "RuntimeError: appwrite fora do ar",
    }


@pytest.mark.asyncio
async def test_rota_ready_responde_200_quando_pronto(client):
    app.state.saude = HealthService({"appwrite": _ok}, timeout=0.5)
    try:
        resp = await client.get("/health/ready")

        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
    finally:
        del app.state.saude


@pytest.mark.asyncio
async def test_rota_ready_responde_503_nomina_dependencia(client):
    app.state.saude = build_health_service(
        _DatabasesFora(), {"ok": True, "erro": None}
    )
    try:
        resp = await client.get("/health/ready")

        assert resp.status_code == 503
        body = resp.json()
        assert body["status"] == "degradado"
        assert body["checks"]["appwrite"]["ok"] is False
        assert "appwrite fora do ar" in body["checks"]["appwrite"]["erro"]
        assert body["checks"]["schema"]["ok"] is True
    finally:
        del app.state.saude


@pytest.mark.asyncio
async def test_rota_ready_sem_saude_responde_503_degradado(client):
    app.state.__dict__.pop("saude", None)

    resp = await client.get("/health/ready")

    assert resp.status_code == 503
    assert resp.json() == {
        "status": "degradado",
        "checks": {"servico": {"ok": False, "erro": "nao inicializado"}},
    }


@pytest.mark.asyncio
async def test_health_simples_mantem_contrato_de_liveness(client):
    # Liveness não consulta dependência nenhuma: 200 sempre que a API sobe.
    resp = await client.get("/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
