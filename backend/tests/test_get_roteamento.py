"""GET /chats/{id}/roteamento le o snapshot mais recente do diagnostico."""

import json

import pytest


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _chat(fake_repos):
    suporte = await fake_repos.departamentos.create(
        {"codigo": "suporte_tecnico", "nome": "Suporte", "ativo": True,
         "recebe_transferencias": True}
    )
    await fake_repos.clientes.create({"nome": "C", "documento": "1"})
    cliente = (await fake_repos.clientes.list_all())[0]
    chat = await fake_repos.chats.create(
        {"cliente_id": cliente["id"], "status": "AGUARDANDO_HUMANO_COM_SOLUCAO",
         "departamento_id": suporte["id"]}
    )
    return suporte, chat


@pytest.mark.asyncio
async def test_sem_diagnostico_marca_tem_diagnostico_false(
    client, admin_token, fake_repos
):
    _, chat = await _chat(fake_repos)
    resp = await client.get(
        f"/chats/{chat['id']}/roteamento", headers=_auth(admin_token)
    )
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["tem_diagnostico"] is False
    assert corpo["departamento_codigo"] == "suporte_tecnico"
    assert corpo["intencao"] is None


@pytest.mark.asyncio
async def test_le_o_diagnostico_mais_recente(client, admin_token, fake_repos):
    suporte, chat = await _chat(fake_repos)
    await fake_repos.ia_diagnosticos.create(
        {"chat_id": chat["id"], "status_ia": "TRANSFERIR_SEM_SOLUCAO",
         "intencao": "problema_tecnico", "categoria_erp": "fiscal",
         "motivo": "execução antiga", "confianca": 0.5}
    )
    await fake_repos.ia_diagnosticos.create(
        {"chat_id": chat["id"], "status_ia": "TRANSFERIR_COM_SOLUCAO",
         "intencao": "problema_tecnico", "categoria_erp": "fiscal",
         "motivo": "execução nova", "confianca": 0.93}
    )

    resp = await client.get(
        f"/chats/{chat['id']}/roteamento", headers=_auth(admin_token)
    )
    corpo = resp.json()
    assert corpo["tem_diagnostico"] is True
    assert corpo["motivo"] == "execução nova"
    assert corpo["confianca"] == 0.93
    assert corpo["intencao"] == "problema_tecnico"
    assert corpo["categoria_erp"] == "fiscal"


@pytest.mark.asyncio
async def test_artigos_consultados_serializados_viram_lista(
    client, admin_token, fake_repos
):
    _, chat = await _chat(fake_repos)
    await fake_repos.ia_diagnosticos.create(
        {
            "chat_id": chat["id"],
            "status_ia": "TRANSFERIR_COM_SOLUCAO",
            "intencao": "problema_tecnico",
            "artigos_consultados": json.dumps(
                [{"id": "kb1", "titulo": "NF-e", "score": 0.9}],
                ensure_ascii=False,
            ),
        }
    )

    resp = await client.get(
        f"/chats/{chat['id']}/roteamento", headers=_auth(admin_token)
    )
    assert resp.status_code == 200
    assert resp.json()["artigos_consultados"] == [
        {"id": "kb1", "titulo": "NF-e", "score": 0.9}
    ]


@pytest.mark.asyncio
async def test_respeita_escopo_do_atendente(client, atendente_token, fake_repos):
    await fake_repos.departamentos.create(
        {"codigo": "financeiro", "nome": "Financeiro", "ativo": True,
         "recebe_transferencias": True}
    )
    financeiro = await fake_repos.departamentos.get_by_codigo("financeiro")
    await fake_repos.clientes.create({"nome": "C", "documento": "1"})
    cliente = (await fake_repos.clientes.list_all())[0]
    chat = await fake_repos.chats.create(
        {"cliente_id": cliente["id"], "status": "NOVO",
         "departamento_id": financeiro["id"]}
    )
    resp = await client.get(
        f"/chats/{chat['id']}/roteamento", headers=_auth(atendente_token)
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_chat_inexistente_retorna_404(client, admin_token):
    resp = await client.get("/chats/nao-existe/roteamento", headers=_auth(admin_token))
    assert resp.status_code == 404
