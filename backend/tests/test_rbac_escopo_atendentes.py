"""RBAC escopo: GET /atendentes/ativos (gap 04-9) e posse nas mutações de
status/prioridade (gap 04-14)."""

import pytest

from app.core.config import settings
from app.core.security import hash_password


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _auth_webhook() -> dict:
    return {
        "content-type": "application/json",
        "X-Webhook-Secret": settings.webhook_secret,
    }


async def _departamento(fake_repos, codigo: str) -> dict:
    return await fake_repos.departamentos.create(
        {"codigo": codigo, "nome": codigo, "ativo": True}
    )


async def _criar_chat(
    fake_repos,
    status: str = "NOVO",
    departamento_id: str | None = None,
    atendente_id: str | None = None,
) -> dict:
    cliente = await fake_repos.clientes.create({"nome": "C", "documento": "123"})
    return await fake_repos.chats.create(
        {
            "cliente_id": cliente["id"],
            "status": status,
            "departamento_id": departamento_id,
            "atendente_id": atendente_id,
        }
    )


async def _novo_atendente(
    client,
    fake_repos,
    nome: str,
    email: str,
    senha: str,
    perfil: str = "atendente",
    departamento_id: str | None = None,
) -> str:
    """Cria um atendente com hash de senha e devolve o token via /auth/login."""
    await fake_repos.atendentes.create(
        {
            "nome": nome,
            "email": email,
            "hash_senha": hash_password(senha),
            "perfil": perfil,
            "departamento_id": departamento_id,
        }
    )
    resp = await client.post("/auth/login", json={"email": email, "senha": senha})
    assert resp.status_code == 200
    return resp.json()["access_token"]


# --- 04-9: escopo por departamento em GET /atendentes/ativos ---


@pytest.mark.asyncio
async def test_ativos_admin_e_supervisor_veem_todos(
    client, admin_token, supervisor_token, atendente_token, fake_repos
):
    depto_a = await _departamento(fake_repos, "suporte")
    depto_b = await _departamento(fake_repos, "financeiro")
    atendente = await fake_repos.atendentes.get_by_email("atendente@test.com")
    await fake_repos.atendentes.update(
        atendente["id"], {"departamento_id": depto_a["id"]}
    )
    await _novo_atendente(client, fake_repos, "Segundo", "segundo@test.com", "seg123",
                          departamento_id=depto_a["id"])
    await _novo_atendente(client, fake_repos, "Terceiro", "terceiro@test.com", "ter123",
                          departamento_id=depto_b["id"])

    for token in (admin_token, supervisor_token):
        resp = await client.get("/atendentes/ativos", headers=_auth(token))
        assert resp.status_code == 200
        # admin + supervisor + atendente + segundo + terceiro = todos os ativos
        assert len(resp.json()) == 5


@pytest.mark.asyncio
async def test_ativos_atendente_ve_apenas_seu_departamento_e_sim(
    client, atendente_token, fake_repos
):
    depto_a = await _departamento(fake_repos, "suporte")
    depto_b = await _departamento(fake_repos, "financeiro")
    atendente = await fake_repos.atendentes.get_by_email("atendente@test.com")
    await fake_repos.atendentes.update(
        atendente["id"], {"departamento_id": depto_a["id"]}
    )
    segundo_token = await _novo_atendente(
        client, fake_repos, "Segundo", "segundo@test.com", "seg123",
        departamento_id=depto_a["id"],
    )
    terceiro_token = await _novo_atendente(
        client, fake_repos, "Terceiro", "terceiro@test.com", "ter123",
        departamento_id=depto_b["id"],
    )
    segundo = await fake_repos.atendentes.get_by_email("segundo@test.com")
    terceiro = await fake_repos.atendentes.get_by_email("terceiro@test.com")

    resp = await client.get("/atendentes/ativos", headers=_auth(atendente_token))
    assert resp.status_code == 200
    # só os do próprio departamento + ele mesmo (não vê admin/supervisor/depto B)
    assert {a["id"] for a in resp.json()} == {atendente["id"], segundo["id"]}

    # espelho: o 2º atendente do mesmo departamento vê os mesmos dois
    resp = await client.get("/atendentes/ativos", headers=_auth(segundo_token))
    assert {a["id"] for a in resp.json()} == {atendente["id"], segundo["id"]}

    # e o do outro departamento só a si
    resp = await client.get("/atendentes/ativos", headers=_auth(terceiro_token))
    assert {a["id"] for a in resp.json()} == {terceiro["id"]}


@pytest.mark.asyncio
async def test_ativos_atendente_sem_departamento_ve_apenas_sim(
    client, atendente_token, fake_repos
):
    depto_a = await _departamento(fake_repos, "suporte")
    await _novo_atendente(client, fake_repos, "Segundo", "segundo@test.com", "seg123",
                          departamento_id=depto_a["id"])

    resp = await client.get("/atendentes/ativos", headers=_auth(atendente_token))
    assert resp.status_code == 200
    atendente = await fake_repos.atendentes.get_by_email("atendente@test.com")
    assert {a["id"] for a in resp.json()} == {atendente["id"]}


# --- 04-14: posse exigida nas mutações de status e prioridade ---


@pytest.mark.asyncio
async def test_status_atendente_de_outro_departamento_receb_403_e_nao_muda(
    client, atendente_token, fake_repos
):
    depto_a = await _departamento(fake_repos, "suporte")
    depto_b = await _departamento(fake_repos, "financeiro")
    atendente = await fake_repos.atendentes.get_by_email("atendente@test.com")
    await fake_repos.atendentes.update(
        atendente["id"], {"departamento_id": depto_a["id"]}
    )
    chat = await _criar_chat(fake_repos, "AGUARDANDO_CLIENTE", depto_b["id"])

    resp = await client.patch(
        f"/chats/{chat['id']}/status",
        json={"status": "ENCERRADO"},
        headers=_auth(atendente_token),
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Sem acesso a este chamado"
    assert (await fake_repos.chats.get(chat["id"]))["status"] == "AGUARDANDO_CLIENTE"


@pytest.mark.asyncio
async def test_prioridade_atendente_de_outro_departamento_receb_403_e_nao_muda(
    client, atendente_token, fake_repos
):
    depto_a = await _departamento(fake_repos, "suporte")
    depto_b = await _departamento(fake_repos, "financeiro")
    atendente = await fake_repos.atendentes.get_by_email("atendente@test.com")
    await fake_repos.atendentes.update(
        atendente["id"], {"departamento_id": depto_a["id"]}
    )
    chat = await _criar_chat(fake_repos, "AGUARDANDO_CLIENTE", depto_b["id"])

    resp = await client.patch(
        f"/chats/{chat['id']}/prioridade",
        json={"prioridade": "urgente"},
        headers=_auth(atendente_token),
    )
    assert resp.status_code == 403
    assert (await fake_repos.chats.get(chat["id"]))["prioridade"] == "media"


@pytest.mark.asyncio
async def test_status_dono_do_chat_pode_mudar(client, atendente_token, fake_repos):
    depto_a = await _departamento(fake_repos, "suporte")
    atendente = await fake_repos.atendentes.get_by_email("atendente@test.com")
    await fake_repos.atendentes.update(
        atendente["id"], {"departamento_id": depto_a["id"]}
    )
    chat = await _criar_chat(
        fake_repos, "AGUARDANDO_CLIENTE", depto_a["id"], atendente["id"]
    )

    resp = await client.patch(
        f"/chats/{chat['id']}/status",
        json={"status": "ENCERRADO"},
        headers=_auth(atendente_token),
    )
    assert resp.status_code == 200
    assert (await fake_repos.chats.get(chat["id"]))["status"] == "ENCERRADO"


@pytest.mark.asyncio
async def test_status_admin_pode_mudar_quaisquer(client, admin_token, fake_repos):
    depto_b = await _departamento(fake_repos, "financeiro")
    chat = await _criar_chat(fake_repos, "AGUARDANDO_CLIENTE", depto_b["id"])

    resp = await client.patch(
        f"/chats/{chat['id']}/status",
        json={"status": "ENCERRADO"},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 200
    assert (await fake_repos.chats.get(chat["id"]))["status"] == "ENCERRADO"


@pytest.mark.asyncio
async def test_status_webhook_sobrevive_sem_user(client, fake_repos):
    depto_b = await _departamento(fake_repos, "financeiro")
    chat = await _criar_chat(fake_repos, "AGUARDANDO_CLIENTE", depto_b["id"])

    resp = await client.patch(
        "/webhooks/chat/status",
        json={"chat_id": chat["id"], "status": "ENCERRADO"},
        headers=_auth_webhook(),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ENCERRADO"
