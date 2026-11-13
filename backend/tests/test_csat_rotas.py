"""Rotas CSAT: GET/POST /chats/{id}/avaliacao, /solicitar-avaliacao e resumo no dashboard."""

import pytest

from app.models.chat import StatusChat
from app.services.evolution_service import EvolutionService


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _criar_chat(fake_repos, status: str, whatsapp: str = "551188877766", **extra) -> dict:
    cliente = await fake_repos.clientes.create(
        {"nome": "Cliente", "telefone": whatsapp, "documento": "1"}
    )
    return await fake_repos.chats.create(
        {
            "cliente_id": cliente["id"],
            "whatsapp_number": whatsapp,
            "status": status,
            **extra,
        }
    )


async def _atendente_no_departamento(fake_repos, codigo: str) -> dict:
    await fake_repos.departamentos.create(
        {"codigo": codigo, "nome": codigo, "ativo": True}
    )
    depto = await fake_repos.departamentos.get_by_codigo(codigo)
    atendente = await fake_repos.atendentes.get_by_email("atendente@test.com")
    await fake_repos.atendentes.update(atendente["id"], {"departamento_id": depto["id"]})
    return depto


def _fake_enviar_texto(monkeypatch, envios: list) -> None:
    async def _fake(self, instance_name: str, number: str, text: str, delay: int = 1200) -> dict:
        envios.append((instance_name, number, text))
        return {}

    monkeypatch.setattr(EvolutionService, "enviar_texto", _fake)


# --- GET /chats/{id}/avaliacao ---


@pytest.mark.asyncio
async def test_get_avaliacao_sem_avaliacao_devolve_null(client, admin_token, fake_repos):
    """Sem avaliação registrada a resposta é 200 com corpo `null` (não 404)."""
    chat = await _criar_chat(fake_repos, StatusChat.resolvido.value)
    resp = await client.get(f"/chats/{chat['id']}/avaliacao", headers=_auth(admin_token))
    assert resp.status_code == 200
    assert resp.json() is None


@pytest.mark.asyncio
async def test_get_avaliacao_com_nota(client, admin_token, fake_repos):
    chat = await _criar_chat(fake_repos, StatusChat.resolvido.value)
    await fake_repos.avaliacoes.create(
        {"chat_id": chat["id"], "nota": 5, "canal": "interno"}
    )
    resp = await client.get(f"/chats/{chat['id']}/avaliacao", headers=_auth(admin_token))
    assert resp.status_code == 200
    assert resp.json()["nota"] == 5


@pytest.mark.asyncio
async def test_get_avaliacao_fora_do_escopo_403(client, atendente_token, fake_repos):
    await fake_repos.departamentos.create(
        {"codigo": "financeiro", "nome": "Financeiro", "ativo": True}
    )
    financeiro = await fake_repos.departamentos.get_by_codigo("financeiro")
    chat = await _criar_chat(
        fake_repos, StatusChat.resolvido.value, departamento_id=financeiro["id"]
    )
    resp = await client.get(f"/chats/{chat['id']}/avaliacao", headers=_auth(atendente_token))
    assert resp.status_code == 403


# --- POST /chats/{id}/avaliacao ---


@pytest.mark.asyncio
async def test_post_avaliacao_pelo_dono_de_chat_finalizado(client, atendente_token, fake_repos):
    depto = await _atendente_no_departamento(fake_repos, "suporte")
    chat = await _criar_chat(
        fake_repos, StatusChat.resolvido.value, departamento_id=depto["id"]
    )
    resp = await client.post(
        f"/chats/{chat['id']}/avaliacao",
        json={"nota": 4, "comentario": "bom atendimento"},
        headers=_auth(atendente_token),
    )
    assert resp.status_code == 201
    assert resp.json()["nota"] == 4

    leitura = await client.get(f"/chats/{chat['id']}/avaliacao", headers=_auth(atendente_token))
    assert leitura.status_code == 200
    assert leitura.json()["nota"] == 4


@pytest.mark.asyncio
async def test_post_avaliacao_duplicada_409(client, atendente_token, fake_repos):
    depto = await _atendente_no_departamento(fake_repos, "suporte")
    chat = await _criar_chat(
        fake_repos, StatusChat.resolvido.value, departamento_id=depto["id"]
    )
    headers = _auth(atendente_token)
    assert (
        await client.post(
            f"/chats/{chat['id']}/avaliacao", json={"nota": 5}, headers=headers
        )
    ).status_code == 201
    assert (
        await client.post(
            f"/chats/{chat['id']}/avaliacao", json={"nota": 3}, headers=headers
        )
    ).status_code == 409


@pytest.mark.asyncio
async def test_post_avaliacao_nota_fora_da_faixa_422(client, atendente_token, fake_repos):
    depto = await _atendente_no_departamento(fake_repos, "suporte")
    chat = await _criar_chat(
        fake_repos, StatusChat.resolvido.value, departamento_id=depto["id"]
    )
    resp = await client.post(
        f"/chats/{chat['id']}/avaliacao", json={"nota": 6}, headers=_auth(atendente_token)
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_post_avaliacao_sem_posse_403(client, atendente_token, fake_repos):
    await fake_repos.departamentos.create(
        {"codigo": "financeiro", "nome": "Financeiro", "ativo": True}
    )
    financeiro = await fake_repos.departamentos.get_by_codigo("financeiro")
    chat = await _criar_chat(
        fake_repos, StatusChat.resolvido.value, departamento_id=financeiro["id"]
    )
    resp = await client.post(
        f"/chats/{chat['id']}/avaliacao", json={"nota": 5}, headers=_auth(atendente_token)
    )
    assert resp.status_code == 403


# --- POST /chats/{id}/solicitar-avaliacao ---


@pytest.mark.asyncio
async def test_solicitar_avaliacao_em_chat_resolvido(
    client, atendente_token, fake_repos, monkeypatch
):
    envios: list = []
    _fake_enviar_texto(monkeypatch, envios)
    depto = await _atendente_no_departamento(fake_repos, "suporte")
    chat = await _criar_chat(
        fake_repos, StatusChat.resolvido.value, departamento_id=depto["id"]
    )
    resp = await client.post(
        f"/chats/{chat['id']}/solicitar-avaliacao", headers=_auth(atendente_token)
    )
    assert resp.status_code == 200
    assert resp.json() == {"enviada": True}
    assert len(envios) == 1
    assert (await fake_repos.chats.get(chat["id"]))["avaliacao_pendente"] is True


@pytest.mark.asyncio
async def test_solicitar_avaliacao_em_chat_novo_409(
    client, atendente_token, fake_repos, monkeypatch
):
    envios: list = []
    _fake_enviar_texto(monkeypatch, envios)
    depto = await _atendente_no_departamento(fake_repos, "suporte")
    chat = await _criar_chat(
        fake_repos, StatusChat.novo.value, departamento_id=depto["id"]
    )
    resp = await client.post(
        f"/chats/{chat['id']}/solicitar-avaliacao", headers=_auth(atendente_token)
    )
    assert resp.status_code == 409
    assert envios == []


# --- Dashboard ---


@pytest.mark.asyncio
async def test_dashboard_inclui_resumo_csat(client, admin_token, fake_repos):
    chat = await _criar_chat(fake_repos, StatusChat.resolvido.value)
    resp = await client.post(
        f"/chats/{chat['id']}/avaliacao", json={"nota": 4}, headers=_auth(admin_token)
    )
    assert resp.status_code == 201

    dados = (await client.get("/dashboard", headers=_auth(admin_token))).json()
    assert dados["csat"]["total"] == 1
    assert dados["csat"]["media"] == 4.0
    assert dados["csat"]["satisfeitos_pct"] == 1.0
