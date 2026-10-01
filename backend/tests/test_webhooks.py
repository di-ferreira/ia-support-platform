import pytest

from app.core.config import settings


def _auth_headers() -> dict:
    return {"X-Webhook-Secret": settings.webhook_secret}


@pytest.mark.asyncio
async def test_valid_secret_accepted(client):
    headers = {"content-type": "application/json", **_auth_headers()}
    resp = await client.post(
        "/webhooks/mensagem",
        json={"whatsapp_number": "5511999999999", "conteudo": "olá"},
        headers=headers,
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_missing_header_rejected(client):
    resp = await client.post(
        "/webhooks/mensagem",
        json={"whatsapp_number": "5511999999999", "conteudo": "olá"},
        headers={"content-type": "application/json"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_wrong_secret_rejected(client):
    headers = {
        "content-type": "application/json",
        "X-Webhook-Secret": "segredo-errado",
    }
    resp = await client.post(
        "/webhooks/mensagem",
        json={"whatsapp_number": "5511999999999", "conteudo": "olá"},
        headers=headers,
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_fail_closed_when_secret_not_configured(client, monkeypatch):
    monkeypatch.setattr(settings, "webhook_secret", None)
    resp = await client.post(
        "/webhooks/mensagem",
        json={"whatsapp_number": "5511999999999", "conteudo": "olá"},
        headers={"content-type": "application/json"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_contexto_get_rejected_without_headers(client):
    resp = await client.get("/webhooks/chat/1/contexto")
    assert resp.status_code == 401
