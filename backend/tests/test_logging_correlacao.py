"""Log JSON e correlacao de requisicao."""

import json
import logging

import pytest

from app.core.correlacao import CorrelacaoMiddleware
from app.core.logging import JsonFormatter, configurar_logging
from app.main import app


def _registro(msg: str = "oi", **extra) -> logging.LogRecord:
    registro = logging.LogRecord("app.teste", logging.INFO, __file__, 1, msg, None, None)
    for chave, valor in extra.items():
        setattr(registro, chave, valor)
    return registro


def test_formatter_serializa_campos_obrigatorios():
    saida = json.loads(JsonFormatter().format(_registro("mensagem", request_id="abc")))

    assert saida["level"] == "INFO"
    assert saida["logger"] == "app.teste"
    assert saida["msg"] == "mensagem"
    assert saida["request_id"] == "abc"
    assert saida["chat_id"] is None
    assert saida["ts"].endswith("+00:00")


def test_formatter_nao_quebra_com_excecao():
    try:
        raise ValueError("boom")
    except ValueError:
        registro = logging.LogRecord(
            "app.teste", logging.ERROR, __file__, 1, "falhou", None, __import__("sys").exc_info()
        )

    saida = json.loads(JsonFormatter().format(registro))

    assert "ValueError: boom" in saida["exc"]


def test_configurar_logging_e_idempotente():
    configurar_logging("DEBUG")
    configurar_logging("DEBUG")

    handlers = [h for h in logging.getLogger().handlers if getattr(h, "_emsoft_json", False)]

    assert len(handlers) == 1


@pytest.mark.asyncio
async def test_middleware_reaproveita_request_id_valido(client, caplog):
    caplog.set_level(logging.INFO)

    resp = await client.get("/health", headers={"X-Request-Id": "abc-123"})

    assert resp.headers["X-Request-Id"] == "abc-123"
    registro = next(r for r in caplog.records if getattr(r, "event", None) == "requisicao")
    assert registro.request_id == "abc-123"
    assert registro.rota == "/health"
    assert registro.status == 200


@pytest.mark.asyncio
async def test_middleware_descarta_request_id_invalido(client):
    resp = await client.get("/health", headers={"X-Request-Id": "x" * 200})

    assert resp.headers["X-Request-Id"] != "x" * 200
    assert 0 < len(resp.headers["X-Request-Id"]) <= 64


@pytest.mark.asyncio
async def test_middleware_gera_id_quando_ausente(client):
    resp = await client.get("/health")

    assert len(resp.headers["X-Request-Id"]) == 32


def test_middleware_esta_registrado():
    nomes = [m.cls.__name__ for m in app.user_middleware]

    assert "CorrelacaoMiddleware" in nomes
    assert CorrelacaoMiddleware is not None


@pytest.mark.asyncio
async def test_requisicoes_distintas_tem_request_ids_distintos(client):
    """Prova de correlacao: duas requisicoes geram ids distintos e o header ecoa."""
    r1 = await client.get("/health")
    r2 = await client.get("/health")

    assert r1.headers["X-Request-Id"]
    assert r2.headers["X-Request-Id"]
    assert r1.headers["X-Request-Id"] != r2.headers["X-Request-Id"]
