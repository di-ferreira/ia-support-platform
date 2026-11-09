"""Confirmacao de resolucao e reabertura do cenario A (spec 05/01)."""

import pytest

from app.core.config import settings


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _chat(fake_repos, status: str, atendente_id: str | None = None):
    await fake_repos.clientes.create({"nome": "C", "documento": "1"})
    cliente = (await fake_repos.clientes.list_all())[0]
    return await fake_repos.chats.create(
        {
            "cliente_id": cliente["id"],
            "status": status,
            "atendente_id": atendente_id,
        }
    )


@pytest.mark.asyncio
async def test_admin_confirma_resolucao(client, admin_token, fake_repos):
    chat = await _chat(fake_repos, "AGUARDANDO_CLIENTE")
    resp = await client.patch(
        f"/chats/{chat['id']}/confirmar-resolucao", headers=_auth(admin_token)
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "RESOLVIDO"


@pytest.mark.asyncio
async def test_confirmar_fora_de_aguardando_cliente_retorna_409(
    client, admin_token, fake_repos
):
    chat = await _chat(fake_repos, "NOVO")
    resp = await client.patch(
        f"/chats/{chat['id']}/confirmar-resolucao", headers=_auth(admin_token)
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_atendente_so_confirma_chat_proprio(client, atendente_token, fake_repos):
    chat = await _chat(fake_repos, "AGUARDANDO_CLIENTE", atendente_id="outro")
    resp = await client.patch(
        f"/chats/{chat['id']}/confirmar-resolucao", headers=_auth(atendente_token)
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_atendente_confirma_chat_proprio(
    client, atendente_token, fake_repos
):
    atendente = await fake_repos.atendentes.get_by_email("atendente@test.com")
    chat = await _chat(fake_repos, "AGUARDANDO_CLIENTE", atendente_id=atendente["id"])
    resp = await client.patch(
        f"/chats/{chat['id']}/confirmar-resolucao", headers=_auth(atendente_token)
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "RESOLVIDO"


@pytest.mark.asyncio
async def test_reabrir_chat_resolvido_volta_para_ia(client, admin_token, fake_repos):
    chat = await _chat(fake_repos, "RESOLVIDO")
    resp = await client.patch(
        f"/chats/{chat['id']}/reabrir",
        json={"motivo": "cliente disse que não resolveu"},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "IA_ANALISANDO"


@pytest.mark.asyncio
async def test_reabrir_chat_novo_retorna_409(client, admin_token, fake_repos):
    chat = await _chat(fake_repos, "NOVO")
    resp = await client.patch(
        f"/chats/{chat['id']}/reabrir", headers=_auth(admin_token)
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_mensagem_do_cliente_reabre_chat_resolvido(client, fake_repos):
    chat = await _chat(fake_repos, "RESOLVIDO")
    resp = await client.post(
        "/webhooks/mensagem",
        json={
            "chat_id": chat["id"],
            "whatsapp_number": "5511999990000",
            "remetente": "cliente",
            "conteudo": "Na verdade não resolveu",
        },
        headers={"X-Webhook-Secret": settings.webhook_secret},
    )
    assert resp.status_code == 201
    assert (await fake_repos.chats.get(chat["id"]))["status"] == "IA_ANALISANDO"


@pytest.mark.asyncio
async def test_mensagem_do_atendente_nao_reabre(client, fake_repos):
    chat = await _chat(fake_repos, "RESOLVIDO")
    await client.post(
        "/webhooks/mensagem",
        json={
            "chat_id": chat["id"],
            "whatsapp_number": "5511999990000",
            "remetente": "atendente",
            "conteudo": "fechando o chamado",
        },
        headers={"X-Webhook-Secret": settings.webhook_secret},
    )
    assert (await fake_repos.chats.get(chat["id"]))["status"] == "RESOLVIDO"
