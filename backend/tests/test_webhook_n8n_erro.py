"""06-18: rota de registro estruturado de falhas do workflow n8n."""

import pytest

from app.core.config import settings


def _auth_headers() -> dict:
    return {"X-Webhook-Secret": settings.webhook_secret}


@pytest.mark.asyncio
async def test_erro_registrado_com_log_estruturado(client, caplog):
    headers = {"content-type": "application/json", **_auth_headers()}
    with caplog.at_level("ERROR"):
        resp = await client.post(
            "/webhooks/n8n/erro",
            json={
                "workflow": "ChatAIBot",
                "node": "Salvar mensagem",
                "mensagem": "timeout de conexão",
                "chat_id": "chat-123",
                "execution_id": "exec-abc",
            },
            headers=headers,
        )
    assert resp.status_code == 202
    assert resp.json() == {"ok": True}
    logs = [r.getMessage() for r in caplog.records]
    assert any(
        "event=n8n_falha" in m and "Salvar mensagem" in m for m in logs
    ), f"log estruturado ausente: {logs}"


@pytest.mark.asyncio
async def test_sem_header_401(client):
    resp = await client.post(
        "/webhooks/n8n/erro",
        json={"workflow": "ChatAIBot"},
        headers={"content-type": "application/json"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_corpo_vazio_202_com_log_de_payload_invalido(client, caplog):
    headers = {"content-type": "application/json", **_auth_headers()}
    with caplog.at_level("ERROR"):
        resp = await client.post(
            "/webhooks/n8n/erro", json={}, headers=headers
        )
    assert resp.status_code == 202
    assert resp.json() == {"ok": True}
    logs = [r.getMessage() for r in caplog.records]
    assert any("payload inválido" in m for m in logs), (
        f"log de payload inválido ausente: {logs}"
    )
