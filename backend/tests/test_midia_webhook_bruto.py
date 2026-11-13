"""Mídia em payload bruto da Evolution (webhook direto, sem n8n)."""
import pytest

import app.api.routes.webhooks as webhooks_mod
from app.api.routes.webhooks import _normalizar_payload
from app.core.config import settings


def _auth_headers() -> dict:
    return {"X-Webhook-Secret": settings.webhook_secret}


def _payload_imagem_bruto() -> dict:
    return {
        "data": {
            "key": {"remoteJid": "5511@s.whatsapp.net", "id": "ABC"},
            "message": {
                "imageMessage": {"mimetype": "image/png", "caption": "print"}
            },
        }
    }


def test_payload_bruto_imagem_inclui_midia():
    payload = _normalizar_payload(_payload_imagem_bruto())

    assert payload["tipo"] == "imagem"
    assert payload["midia"] == {
        "key": {"remoteJid": "5511@s.whatsapp.net", "id": "ABC"},
        "message": {"imageMessage": {"mimetype": "image/png", "caption": "print"}},
    }
    assert "url_arquivo" not in payload


def test_payload_bruto_texto_sem_midia():
    payload = _normalizar_payload(
        {
            "data": {
                "key": {"remoteJid": "5511@s.whatsapp.net", "id": "TXT1"},
                "message": {"conversation": "oi"},
            }
        }
    )

    assert payload["tipo"] == "texto"
    assert "midia" not in payload
    assert "url_arquivo" not in payload


class FakeMidiaService:
    """Duplo de MidiaService para a rota: registra chamadas e devolve resultado."""

    def __init__(self, resultado):
        self.resultado = resultado
        self.chamadas = []

    async def armazenar(self, midia, tipo, whatsapp_message_id=None, conteudo=None):
        self.chamadas.append(midia)
        return self.resultado


@pytest.mark.asyncio
async def test_webhook_bruto_persiste_midia(client, fake_repos, monkeypatch):
    fake = FakeMidiaService(("appwrite://midias/abc", "print"))
    monkeypatch.setattr(webhooks_mod, "MidiaService", lambda: fake)

    resp = await client.post(
        "/webhooks/mensagem",
        json=_payload_imagem_bruto(),
        headers={"content-type": "application/json", **_auth_headers()},
    )
    assert resp.status_code == 201

    msg = (await fake_repos.mensagens.list_all())[0]
    assert msg["whatsapp_message_id"] == "ABC"
    assert msg["tipo"] == "imagem"
    assert msg["url_arquivo"] == "appwrite://midias/abc"
    assert msg["conteudo"] == "print"
    assert len(fake.chamadas) == 1
    assert fake.chamadas[0]["key"] == {"remoteJid": "5511@s.whatsapp.net", "id": "ABC"}
