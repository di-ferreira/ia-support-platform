"""Escopo por departamento em listagem de chats e dashboard."""

import pytest

from app.services.chat_service import ChatService
from app.services.dashboard_service import DashboardService


async def _cenario(fake_repos):
    suporte = await fake_repos.departamentos.create(
        {"codigo": "suporte_tecnico", "nome": "Suporte", "ativo": True}
    )
    financeiro = await fake_repos.departamentos.create(
        {"codigo": "financeiro", "nome": "Financeiro", "ativo": True}
    )
    await fake_repos.clientes.create({"nome": "C1", "documento": "1"})
    cliente = (await fake_repos.clientes.list_all())[0]
    chat_suporte = await fake_repos.chats.create(
        {"cliente_id": cliente["id"], "status": "AGUARDANDO_HUMANO_SEM_SOLUCAO",
         "departamento_id": suporte["id"]}
    )
    chat_financeiro = await fake_repos.chats.create(
        {"cliente_id": cliente["id"], "status": "NOVO",
         "departamento_id": financeiro["id"]}
    )
    return suporte, financeiro, chat_suporte, chat_financeiro


@pytest.mark.asyncio
async def test_atendente_ve_apenas_seu_departamento(fake_repos):
    suporte, _, chat_suporte, chat_financeiro = await _cenario(fake_repos)
    user = {"id": "a1", "perfil": "atendente", "departamento_id": suporte["id"]}
    chats, total = await ChatService(fake_repos).listar(user=user)
    assert total == 1
    assert chats[0]["id"] == chat_suporte["id"]


@pytest.mark.asyncio
async def test_atendente_sem_departamento_nao_ve_fila_global(fake_repos):
    await _cenario(fake_repos)
    user = {"id": "a1", "perfil": "atendente", "departamento_id": None}
    chats, total = await ChatService(fake_repos).listar(user=user)
    assert total == 0
    assert chats == []


@pytest.mark.asyncio
async def test_admin_ve_todos(fake_repos):
    await _cenario(fake_repos)
    user = {"id": "admin", "perfil": "admin", "departamento_id": None}
    _, total = await ChatService(fake_repos).listar(user=user)
    assert total == 2


@pytest.mark.asyncio
async def test_atendente_continua_vendo_chat_que_e_dele(fake_repos):
    suporte, financeiro, chat_suporte, chat_financeiro = await _cenario(fake_repos)
    await fake_repos.chats.update(chat_financeiro["id"], {"atendente_id": "a1"})
    user = {"id": "a1", "perfil": "atendente", "departamento_id": suporte["id"]}
    chats, total = await ChatService(fake_repos).listar(user=user)
    ids = {c["id"] for c in chats}
    # Regra de união: fila do próprio departamento + chats que já são dele,
    # mesmo que de outro departamento.
    assert total == 2
    assert chat_financeiro["id"] in ids
    assert chat_suporte["id"] in ids


@pytest.mark.asyncio
async def test_dashboard_aplica_escopo_do_atendente(fake_repos):
    suporte, _, chat_suporte, _ = await _cenario(fake_repos)
    await fake_repos.mensagens.create(
        {"chat_id": chat_suporte["id"], "remetente": "cliente", "conteudo": "oi"}
    )
    user = {"id": "a1", "perfil": "atendente", "departamento_id": suporte["id"]}
    dados = await DashboardService(fake_repos).obter_dashboard(user=user)
    assert dados["kpis"]["total"] == 1
    assert [c["id"] for c in dados["recentes"]] == [chat_suporte["id"]]


@pytest.mark.asyncio
async def test_dashboard_nao_chama_clientes_get_no_loop(fake_repos, monkeypatch):
    suporte, _, chat_suporte, _ = await _cenario(fake_repos)
    chamadas = {"n": 0}
    original = fake_repos.clientes.get

    async def contando(cliente_id):
        chamadas["n"] += 1
        return await original(cliente_id)

    monkeypatch.setattr(fake_repos.clientes, "get", contando)
    user = {"id": "admin", "perfil": "admin", "departamento_id": None}
    await DashboardService(fake_repos).obter_dashboard(user=user)
    assert chamadas["n"] == 0


@pytest.mark.asyncio
async def test_rota_de_chats_filtra_por_departamento(
    client, atendente_token, fake_repos
):
    suporte, financeiro, chat_suporte, chat_financeiro = await _cenario(fake_repos)
    atendente = await fake_repos.atendentes.get_by_email("atendente@test.com")
    await fake_repos.atendentes.update(
        atendente["id"], {"departamento_id": suporte["id"]}
    )

    resp = await client.get(
        "/chats", params={"departamento_id": suporte["id"]},
        headers={"Authorization": f"Bearer {atendente_token}"},
    )

    assert resp.status_code == 200
    assert [c["id"] for c in resp.json()] == [chat_suporte["id"]]


@pytest.mark.asyncio
async def test_rota_de_chats_nao_amplia_escopo_com_filtro(
    client, atendente_token, fake_repos
):
    suporte, financeiro, _, chat_financeiro = await _cenario(fake_repos)
    atendente = await fake_repos.atendentes.get_by_email("atendente@test.com")
    await fake_repos.atendentes.update(
        atendente["id"], {"departamento_id": suporte["id"]}
    )

    resp = await client.get(
        "/chats", params={"departamento_id": financeiro["id"]},
        headers={"Authorization": f"Bearer {atendente_token}"},
    )

    assert resp.status_code == 200
    assert resp.json() == []
