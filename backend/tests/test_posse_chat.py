"""Posse/escopo em GET /chats/{id}, /chats/{id}/mensagens e /clientes/{id}."""

import pytest


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_atendente_nao_le_chat_de_outro_departamento(
    client, atendente_token, fake_repos
):
    await fake_repos.departamentos.create(
        {"codigo": "financeiro", "nome": "Financeiro", "ativo": True}
    )
    financeiro = await fake_repos.departamentos.get_by_codigo("financeiro")
    await fake_repos.clientes.create({"nome": "C", "documento": "1"})
    cliente = (await fake_repos.clientes.list_all())[0]
    chat = await fake_repos.chats.create(
        {
            "cliente_id": cliente["id"],
            "status": "AGUARDANDO_HUMANO_SEM_SOLUCAO",
            "departamento_id": financeiro["id"],
        }
    )
    resp = await client.get(f"/chats/{chat['id']}", headers=_auth(atendente_token))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_atendente_le_chat_do_proprio_departamento(
    client, atendente_token, fake_repos
):
    suporte = await fake_repos.departamentos.create(
        {"codigo": "suporte_tecnico", "nome": "Suporte", "ativo": True}
    )
    atendente = await fake_repos.atendentes.get_by_email("atendente@test.com")
    await fake_repos.atendentes.update(
        atendente["id"], {"departamento_id": suporte["id"]}
    )
    await fake_repos.clientes.create({"nome": "C", "documento": "1"})
    cliente = (await fake_repos.clientes.list_all())[0]
    chat = await fake_repos.chats.create(
        {
            "cliente_id": cliente["id"],
            "status": "NOVO",
            "departamento_id": suporte["id"],
        }
    )
    resp = await client.get(f"/chats/{chat['id']}", headers=_auth(atendente_token))
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_admin_le_qualquer_chat(client, admin_token, fake_repos):
    await fake_repos.clientes.create({"nome": "C", "documento": "1"})
    cliente = (await fake_repos.clientes.list_all())[0]
    chat = await fake_repos.chats.create(
        {"cliente_id": cliente["id"], "status": "NOVO"}
    )
    resp = await client.get(f"/chats/{chat['id']}", headers=_auth(admin_token))
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_atendente_nao_lista_mensagens_fora_do_escopo(
    client, atendente_token, fake_repos
):
    await fake_repos.departamentos.create(
        {"codigo": "comercial", "nome": "Comercial", "ativo": True}
    )
    comercial = await fake_repos.departamentos.get_by_codigo("comercial")
    await fake_repos.clientes.create({"nome": "C", "documento": "1"})
    cliente = (await fake_repos.clientes.list_all())[0]
    chat = await fake_repos.chats.create(
        {"cliente_id": cliente["id"], "status": "NOVO", "departamento_id": comercial["id"]}
    )
    resp = await client.get(
        f"/chats/{chat['id']}/mensagens", headers=_auth(atendente_token)
    )
    assert resp.status_code == 403
