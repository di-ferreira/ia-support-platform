"""Transferencia entre departamentos por ID (spec 10, regras 10-12)."""

import pytest


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _cenario(fake_repos):
    suporte = await fake_repos.departamentos.create(
        {"codigo": "suporte_tecnico", "nome": "Suporte", "ativo": True,
         "recebe_transferencias": True}
    )
    financeiro = await fake_repos.departamentos.create(
        {"codigo": "financeiro", "nome": "Financeiro", "ativo": True,
         "recebe_transferencias": True}
    )
    await fake_repos.clientes.create({"nome": "C", "documento": "1"})
    cliente = (await fake_repos.clientes.list_all())[0]
    chat = await fake_repos.chats.create(
        {"cliente_id": cliente["id"], "status": "EM_ATENDIMENTO",
         "departamento_id": suporte["id"], "atendente_id": "atendente-1"}
    )
    return suporte, financeiro, chat


@pytest.mark.asyncio
async def test_transfere_e_limpa_atendente(client, admin_token, fake_repos):
    _, financeiro, chat = await _cenario(fake_repos)
    resp = await client.patch(
        f"/chats/{chat['id']}/transferir-departamento",
        json={"departamento_id": financeiro["id"], "motivo": "triagem financeira"},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["departamento_id"] == financeiro["id"]
    assert corpo["atendente_id"] is None
    assert corpo["status"] == "NOVO"


@pytest.mark.asyncio
async def test_preserva_atendente_quando_compativel(client, admin_token, fake_repos):
    suporte, _, chat = await _cenario(fake_repos)
    await fake_repos.atendentes.create(
        {"nome": "A", "email": "a@x.com", "departamento_id": suporte["id"], "ativo": True}
    )
    atendente = await fake_repos.atendentes.get_by_email("a@x.com")
    await fake_repos.chats.update(chat["id"], {"atendente_id": atendente["id"]})

    resp = await client.patch(
        f"/chats/{chat['id']}/transferir-departamento",
        json={
            "departamento_id": suporte["id"],
            "preservar_atendente_se_compativel": True,
        },
        headers=_auth(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["atendente_id"] == atendente["id"]


@pytest.mark.asyncio
async def test_departamento_inexistente_retorna_404(client, admin_token, fake_repos):
    _, _, chat = await _cenario(fake_repos)
    resp = await client.patch(
        f"/chats/{chat['id']}/transferir-departamento",
        json={"departamento_id": "nao-existe"},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_departamento_inativo_retorna_400(client, admin_token, fake_repos):
    _, financeiro, chat = await _cenario(fake_repos)
    await fake_repos.departamentos.update(financeiro["id"], {"ativo": False})
    resp = await client.patch(
        f"/chats/{chat['id']}/transferir-departamento",
        json={"departamento_id": financeiro["id"]},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_departamento_sem_recebe_transferencias_retorna_400(
    client, admin_token, fake_repos
):
    _, financeiro, chat = await _cenario(fake_repos)
    await fake_repos.departamentos.update(
        financeiro["id"], {"recebe_transferencias": False}
    )
    resp = await client.patch(
        f"/chats/{chat['id']}/transferir-departamento",
        json={"departamento_id": financeiro["id"]},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_atendente_so_transfere_chat_proprio(client, atendente_token, fake_repos):
    _, financeiro, chat = await _cenario(fake_repos)
    resp = await client.patch(
        f"/chats/{chat['id']}/transferir-departamento",
        json={"departamento_id": financeiro["id"]},
        headers=_auth(atendente_token),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_chat_inexistente_retorna_404(client, admin_token, fake_repos):
    _, financeiro, _ = await _cenario(fake_repos)
    resp = await client.patch(
        "/chats/nao-existe/transferir-departamento",
        json={"departamento_id": financeiro["id"]},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 404
