"""Enum TipoMensagem espelha sticker/local da Evolution (gap 02-3)."""
import pytest

import app.api.routes.webhooks as webhooks_mod
from app.api.routes.webhooks import TIPOS_VALIDOS, _normalizar_payload
from app.appwrite import schema as appwrite_schema
from app.core.config import settings
from app.models.enums import TipoMensagem


def _auth_headers() -> dict:
    return {"X-Webhook-Secret": settings.webhook_secret}


# --- Grupo 1: enum, lista de tipos válidos e schema -----------------------


def test_enum_tipo_mensagem_contem_sticker_e_local():
    valores = {e.value for e in TipoMensagem}
    assert "sticker" in valores
    assert "local" in valores


def test_tipos_validos_derivados_do_enum():
    assert set(TIPOS_VALIDOS) == {e.value for e in TipoMensagem}
    assert "sticker" in TIPOS_VALIDOS
    assert "local" in TIPOS_VALIDOS


def test_schema_tipo_mensagem_derivado_do_enum():
    assert appwrite_schema.TIPO_MENSAGEM == [t.value for t in TipoMensagem]


# --- Grupo 2: _normalizar_payload com stickerMessage/locationMessage ------


def test_normalizar_payload_sticker_message():
    payload = _normalizar_payload(
        {
            "data": {
                "key": {"remoteJid": "5511@s.whatsapp.net", "id": "STK1"},
                "message": {"stickerMessage": {"mimetype": "image/webp"}},
            }
        }
    )

    assert payload["tipo"] == "sticker"
    assert payload["conteudo"] == ""
    assert payload["midia"] is not None


def test_normalizar_payload_location_message():
    payload = _normalizar_payload(
        {
            "data": {
                "key": {"remoteJid": "5511@s.whatsapp.net", "id": "LOC1"},
                "message": {"locationMessage": {"latitude": -23.55, "longitude": -46.63}},
            }
        }
    )

    assert payload["tipo"] == "local"
    assert payload["conteudo"] == "[localização]"
    assert payload["midia"] is not None


# --- Grupo 3: webhook aceita os novos tipos sem recair para "texto" -------


class FakeMidiaService:
    """Duplo de MidiaService para a rota: registra chamadas e devolve resultado."""

    def __init__(self, resultado):
        self.resultado = resultado
        self.chamadas = []

    async def armazenar(self, midia, tipo, whatsapp_message_id=None, conteudo=None):
        self.chamadas.append((midia, tipo))
        return self.resultado


@pytest.mark.asyncio
async def test_webhook_sticker_nao_recai_para_texto(client, fake_repos, monkeypatch):
    fake = FakeMidiaService(None)
    monkeypatch.setattr(webhooks_mod, "MidiaService", lambda: fake)

    resp = await client.post(
        "/webhooks/mensagem",
        json={
            "data": {
                "key": {"remoteJid": "5511@s.whatsapp.net", "id": "STK2"},
                "message": {"stickerMessage": {"mimetype": "image/webp"}},
            }
        },
        headers={"content-type": "application/json", **_auth_headers()},
    )
    assert resp.status_code == 201

    msg = (await fake_repos.mensagens.list_all())[0]
    assert msg["tipo"] == "sticker"
    esperado = (
        {"key": {"remoteJid": "5511@s.whatsapp.net", "id": "STK2"},
         "message": {"stickerMessage": {"mimetype": "image/webp"}}},
        "sticker",
    )
    assert fake.chamadas == [esperado]


@pytest.mark.asyncio
async def test_webhook_local_persiste_rotulo(client, fake_repos, monkeypatch):
    fake = FakeMidiaService(None)
    monkeypatch.setattr(webhooks_mod, "MidiaService", lambda: fake)

    resp = await client.post(
        "/webhooks/mensagem",
        json={
            "data": {
                "key": {"remoteJid": "5511@s.whatsapp.net", "id": "LOC2"},
                "message": {"locationMessage": {"latitude": -23.55, "longitude": -46.63}},
            }
        },
        headers={"content-type": "application/json", **_auth_headers()},
    )
    assert resp.status_code == 201

    msg = (await fake_repos.mensagens.list_all())[0]
    assert msg["tipo"] == "local"
    assert msg["conteudo"] == "[localização]"
