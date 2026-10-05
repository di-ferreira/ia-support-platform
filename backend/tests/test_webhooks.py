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


@pytest.mark.asyncio
async def test_mensagem_duplicate_returns_200(client, fake_repos):
    headers = {"content-type": "application/json", **_auth_headers()}
    payload = {
        "whatsapp_number": "5511999999999",
        "conteudo": "olá",
        "whatsapp_message_id": "ABC123XYZ",
    }
    first = await client.post("/webhooks/mensagem", json=payload, headers=headers)
    assert first.status_code == 201
    assert first.json().get("duplicada") is not True

    second = await client.post("/webhooks/mensagem", json=payload, headers=headers)
    assert second.status_code == 200
    body = second.json()
    assert body["duplicada"] is True
    assert body["id"] == first.json()["id"]
    assert len(fake_repos.mensagens.rows) == 1


@pytest.mark.asyncio
async def test_payload_bruto_evolution_texto(client, fake_repos):
    headers = {"content-type": "application/json", **_auth_headers()}
    payload = {
        "data": {
            "key": {
                "remoteJid": "5511999999999@s.whatsapp.net",
                "id": "MSG999",
            },
            "message": {"conversation": "erro no estoque"},
        },
        "remetente": "cliente",
    }
    resp = await client.post("/webhooks/mensagem", json=payload, headers=headers)
    assert resp.status_code == 201

    chat = (await fake_repos.chats.list_all())[0]
    assert chat["whatsapp_number"] == "5511999999999"
    msg = (await fake_repos.mensagens.list_all())[0]
    assert msg["whatsapp_message_id"] == "MSG999"
    assert msg["conteudo"] == "erro no estoque"
    assert msg["tipo"] == "texto"


@pytest.mark.asyncio
async def test_payload_bruto_evolution_imagem_caption(client, fake_repos):
    headers = {"content-type": "application/json", **_auth_headers()}
    payload = {
        "data": {
            "key": {
                "remoteJid": "5511888888888@s.whatsapp.net",
                "id": "IMG1",
            },
            "message": {
                "imageMessage": {
                    "caption": "tela de erro",
                    "url": "https://exemplo/img.png",
                }
            },
        },
    }
    resp = await client.post("/webhooks/mensagem", json=payload, headers=headers)
    assert resp.status_code == 201

    msg = (await fake_repos.mensagens.list_all())[0]
    assert msg["whatsapp_message_id"] == "IMG1"
    assert msg["conteudo"] == "tela de erro"
    assert msg["tipo"] == "imagem"
    assert msg["url_arquivo"] == "https://exemplo/img.png"
