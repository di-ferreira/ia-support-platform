"""Auditoria via API: trilha de transições com ator tipado (spec 04)."""

import pytest

from app.core.config import settings


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _whook() -> dict:
    return {"X-Webhook-Secret": settings.webhook_secret}


async def _cenario(fake_repos):
    await fake_repos.clientes.create({"nome": "C", "documento": "1"})
    cliente = (await fake_repos.clientes.list_all())[0]
    chat = await fake_repos.chats.create(
        {"cliente_id": cliente["id"], "status": "NOVO"}
    )
    return cliente, chat


def _registro(registros: list[dict], acao: str) -> dict:
    achados = [r for r in registros if r["acao"] == acao]
    assert achados, f"nenhum registro de auditoria com acao={acao}"
    return achados[0]


@pytest.mark.asyncio
async def test_pegar_registra_atribuicao_humana(client, atendente_token, fake_repos):
    _, chat = await _cenario(fake_repos)
    atendente = await fake_repos.atendentes.get_by_email("atendente@test.com")

    resp = await client.patch(
        f"/chats/{chat['id']}/pegar", headers=_auth(atendente_token)
    )
    assert resp.status_code == 200

    resp = await client.get(f"/chats/{chat['id']}/auditoria", headers=_auth(atendente_token))
    assert resp.status_code == 200
    reg = _registro(resp.json(), "ATRIBUICAO")
    assert reg["ator_tipo"] == "HUMANO"
    assert reg["ator_id"] == atendente["id"]
    assert reg["atendente_novo_id"] == atendente["id"]


@pytest.mark.asyncio
async def test_auditoria_ordem_decrescente(client, admin_token, fake_repos):
    _, chat = await _cenario(fake_repos)
    await fake_repos.auditoria.create(
        {
            "chat_id": chat["id"],
            "acao": "STATUS",
            "ator_tipo": "SISTEMA",
            "created_at": "2026-01-01T12:00:00+00:00",
        }
    )
    await fake_repos.auditoria.create(
        {
            "chat_id": chat["id"],
            "acao": "STATUS",
            "ator_tipo": "SISTEMA",
            "created_at": "2026-01-02T12:00:00+00:00",
        }
    )

    resp = await client.get(f"/chats/{chat['id']}/auditoria", headers=_auth(admin_token))
    assert resp.status_code == 200
    registros = resp.json()
    assert len(registros) == 2
    assert registros[0]["created_at"] >= registros[1]["created_at"]


@pytest.mark.asyncio
async def test_auditoria_fora_do_escopo_403(client, atendente_token, fake_repos):
    depto_a = await fake_repos.departamentos.create(
        {"codigo": "sup", "nome": "Sup", "ativo": True}
    )
    depto_b = await fake_repos.departamentos.create(
        {"codigo": "fin", "nome": "Fin", "ativo": True}
    )
    await fake_repos.clientes.create({"nome": "C", "documento": "1"})
    cliente = (await fake_repos.clientes.list_all())[0]
    chat = await fake_repos.chats.create(
        {"cliente_id": cliente["id"], "status": "NOVO", "departamento_id": depto_b["id"]}
    )
    atendente = await fake_repos.atendentes.get_by_email("atendente@test.com")
    await fake_repos.atendentes.update(atendente["id"], {"departamento_id": depto_a["id"]})

    resp = await client.get(
        f"/chats/{chat['id']}/auditoria", headers=_auth(atendente_token)
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_auditoria_chat_inexistente_404(client, admin_token, fake_repos):
    resp = await client.get("/chats/nao-existe/auditoria", headers=_auth(admin_token))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_webhook_status_registra_ator_servico(client, admin_token, fake_repos):
    await fake_repos.clientes.create({"nome": "C", "documento": "1"})
    cliente = (await fake_repos.clientes.list_all())[0]
    # AGUARDANDO_CLIENTE é a única origem que aceita transição para EM_ATENDIMENTO
    # na máquina de estados (spec 01) — NOVO → EM_ATENDIMENTO é 400.
    chat = await fake_repos.chats.create(
        {"cliente_id": cliente["id"], "status": "AGUARDANDO_CLIENTE"}
    )

    resp = await client.patch(
        "/webhooks/chat/status",
        json={"chat_id": chat["id"], "status": "EM_ATENDIMENTO"},
        headers=_whook(),
    )
    assert resp.status_code == 200

    resp = await client.get(f"/chats/{chat['id']}/auditoria", headers=_auth(admin_token))
    assert resp.status_code == 200
    reg = _registro(resp.json(), "STATUS")
    assert reg["ator_tipo"] == "SERVICO"
    assert reg["ator_id"] is None


@pytest.mark.asyncio
async def test_auditoria_lista_completa(client, admin_token, atendente_token, fake_repos):
    _, chat = await _cenario(fake_repos)
    atendente = await fake_repos.atendentes.get_by_email("atendente@test.com")

    assert (
        await client.patch(
            f"/chats/{chat['id']}/pegar", headers=_auth(atendente_token)
        )
    ).status_code == 200
    assert (
        await client.patch(
            f"/chats/{chat['id']}/prioridade",
            json={"prioridade": "alta"},
            headers=_auth(admin_token),
        )
    ).status_code == 200

    resp = await client.get(f"/chats/{chat['id']}/auditoria", headers=_auth(admin_token))
    assert resp.status_code == 200
    registros = resp.json()
    assert len(registros) == 2
    acoes = {r["acao"] for r in registros}
    assert acoes == {"ATRIBUICAO", "PRIORIDADE"}
    atribuicao = _registro(registros, "ATRIBUICAO")
    assert atribuicao["atendente_novo_id"] == atendente["id"]
    assert atribuicao["ator_tipo"] == "HUMANO"
