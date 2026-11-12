"""Mutacoes de chat emitem eventos WebSocket depois do commit (gap 03-8)."""

import pytest

from app.api.websocket_manager import manager


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def eventos(monkeypatch):
    capturados: list[tuple] = []

    async def fake_send(chat_id, evento, dados):
        capturados.append((chat_id, evento, dados))

    monkeypatch.setattr(manager, "send_event", fake_send)
    return capturados


async def _chat(fake_repos, status: str = "NOVO", **extra) -> dict:
    await fake_repos.clientes.create({"nome": "C", "documento": "1"})
    cliente = (await fake_repos.clientes.list_all())[0]
    return await fake_repos.chats.create(
        {"cliente_id": cliente["id"], "status": status, **extra}
    )


def _payload(chat, **alterados) -> dict:
    return {
        "chat_id": chat["id"],
        "status": chat["status"],
        "prioridade": "media",
        "departamento_id": chat.get("departamento_id"),
        "atendente_id": chat.get("atendente_id"),
        **alterados,
    }


@pytest.mark.asyncio
async def test_status_emite_chat_atualizado_e_status_update(
    client, admin_token, fake_repos, eventos
):
    chat = await _chat(fake_repos)

    resp = await client.patch(
        f"/chats/{chat['id']}/status",
        json={"status": "IA_ANALISANDO"},
        headers=_auth(admin_token),
    )

    assert resp.status_code == 200
    assert [evento for _, evento, _ in eventos] == [
        "chat_atualizado",
        "status_update",
    ]
    for chat_id, _, dados in eventos:
        assert chat_id == chat["id"]
        assert dados == _payload(chat, status="IA_ANALISANDO")


@pytest.mark.asyncio
async def test_status_transicao_invalida_nao_emite_evento(
    client, admin_token, fake_repos, eventos
):
    chat = await _chat(fake_repos, status="ENCERRADO")

    resp = await client.patch(
        f"/chats/{chat['id']}/status",
        json={"status": "IA_ANALISANDO"},
        headers=_auth(admin_token),
    )

    assert resp.status_code == 400
    assert eventos == []


@pytest.mark.asyncio
async def test_pegar_emite_chat_atualizado(client, atendente_token, fake_repos, eventos):
    chat = await _chat(fake_repos)
    atendente = await fake_repos.atendentes.get_by_email("atendente@test.com")

    resp = await client.patch(f"/chats/{chat['id']}/pegar", headers=_auth(atendente_token))

    assert resp.status_code == 200
    assert [evento for _, evento, _ in eventos] == [
        "chat_atualizado",
        "status_update",
    ]
    for chat_id, _, dados in eventos:
        assert chat_id == chat["id"]
        assert dados == _payload(chat, status="EM_ATENDIMENTO", atendente_id=atendente["id"])


@pytest.mark.asyncio
async def test_assinar_emite_chat_atualizado(client, admin_token, fake_repos, eventos):
    chat = await _chat(fake_repos)
    atendente = await fake_repos.atendentes.create(
        {"nome": "B", "email": "b@test.com", "perfil": "atendente"}
    )

    resp = await client.patch(
        f"/chats/{chat['id']}/assinar",
        json={"atendente_id": atendente["id"]},
        headers=_auth(admin_token),
    )

    assert resp.status_code == 200
    assert [evento for _, evento, _ in eventos] == [
        "chat_atualizado",
        "status_update",
    ]
    assert eventos[0][2]["atendente_id"] == atendente["id"]


@pytest.mark.asyncio
async def test_prioridade_emite_so_chat_atualizado(client, admin_token, fake_repos, eventos):
    chat = await _chat(fake_repos)

    resp = await client.patch(
        f"/chats/{chat['id']}/prioridade",
        json={"prioridade": "alta"},
        headers=_auth(admin_token),
    )

    assert resp.status_code == 200
    assert [evento for _, evento, _ in eventos] == ["chat_atualizado"]
    assert eventos[0][2] == _payload(chat, prioridade="alta")


@pytest.mark.asyncio
async def test_transferir_emite_chat_atualizado(client, admin_token, fake_repos, eventos):
    chat = await _chat(fake_repos, status="AGUARDANDO_HUMANO_SEM_SOLUCAO")
    destino = await fake_repos.atendentes.create(
        {"nome": "B", "email": "b@test.com", "perfil": "atendente"}
    )

    resp = await client.patch(
        f"/chats/{chat['id']}/transferir",
        json={"atendente_id": destino["id"]},
        headers=_auth(admin_token),
    )

    assert resp.status_code == 200
    assert [evento for _, evento, _ in eventos] == [
        "chat_atualizado",
        "status_update",
    ]
    assert eventos[0][2]["atendente_id"] == destino["id"]


@pytest.mark.asyncio
async def test_transferir_atendente_inexistente_nao_emite(
    client, admin_token, fake_repos, eventos
):
    chat = await _chat(fake_repos)

    resp = await client.patch(
        f"/chats/{chat['id']}/transferir",
        json={"atendente_id": "nao-existe"},
        headers=_auth(admin_token),
    )

    assert resp.status_code == 404
    assert eventos == []


@pytest.mark.asyncio
async def test_transferir_departamento_emite_chat_atualizado(
    client, admin_token, fake_repos, eventos
):
    suporte = await fake_repos.departamentos.create(
        {"codigo": "suporte_tecnico", "ativo": True, "recebe_transferencias": True}
    )
    financeiro = await fake_repos.departamentos.create(
        {"codigo": "financeiro", "ativo": True, "recebe_transferencias": True}
    )
    chat = await _chat(
        fake_repos, status="EM_ATENDIMENTO",
        departamento_id=suporte["id"], atendente_id="atendente-1",
    )

    resp = await client.patch(
        f"/chats/{chat['id']}/transferir-departamento",
        json={"departamento_id": financeiro["id"]},
        headers=_auth(admin_token),
    )

    assert resp.status_code == 200
    assert [evento for _, evento, _ in eventos] == [
        "chat_atualizado",
        "status_update",
    ]
    for _, _, dados in eventos:
        assert dados == _payload(
            chat, status="NOVO",
            departamento_id=financeiro["id"], atendente_id=None,
        )


@pytest.mark.asyncio
async def test_transferir_departamento_erro_nao_emite(
    client, admin_token, fake_repos, eventos
):
    chat = await _chat(fake_repos)

    resp = await client.patch(
        f"/chats/{chat['id']}/transferir-departamento",
        json={"departamento_id": "nao-existe"},
        headers=_auth(admin_token),
    )

    assert resp.status_code == 404
    assert eventos == []


@pytest.mark.asyncio
async def test_kanban_mover_emite_chat_atualizado(client, admin_token, fake_repos, eventos):
    chat = await _chat(fake_repos)

    resp = await client.patch(
        "/kanban/mover",
        json={"chat_id": chat["id"], "novo_status": "IA_ANALISANDO"},
        headers=_auth(admin_token),
    )

    assert resp.status_code == 204
    assert [evento for _, evento, _ in eventos] == [
        "chat_atualizado",
        "status_update",
    ]
    assert eventos[0][2]["status"] == "IA_ANALISANDO"


@pytest.mark.asyncio
async def test_kanban_mover_transicao_invalida_nao_emite(
    client, admin_token, fake_repos, eventos
):
    chat = await _chat(fake_repos, status="ENCERRADO")

    resp = await client.patch(
        "/kanban/mover",
        json={"chat_id": chat["id"], "novo_status": "IA_ANALISANDO"},
        headers=_auth(admin_token),
    )

    assert resp.status_code == 400
    assert eventos == []
