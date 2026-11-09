"""ChatService passa a persistir departamento_id sem quebrar o legado."""

import pytest
from fastapi import HTTPException

from app.services.chat_service import ChatService


async def _depto(fake_repos, codigo="suporte_tecnico"):
    return await fake_repos.departamentos.create(
        {"codigo": codigo, "nome": codigo, "ativo": True}
    )


@pytest.mark.asyncio
async def test_criar_persiste_departamento_id(fake_repos):
    depto = await _depto(fake_repos)
    await fake_repos.clientes.create({"nome": "C", "documento": "1"})
    cliente = (await fake_repos.clientes.list_all())[0]
    chat = await ChatService(fake_repos).criar(
        {"cliente_id": cliente["id"], "departamento_id": depto["id"]}
    )
    assert chat["departamento_id"] == depto["id"]


@pytest.mark.asyncio
async def test_criar_com_departamento_inexistente_retorna_404(fake_repos):
    await fake_repos.clientes.create({"nome": "C", "documento": "1"})
    cliente = (await fake_repos.clientes.list_all())[0]
    with pytest.raises(HTTPException) as exc:
        await ChatService(fake_repos).criar(
            {"cliente_id": cliente["id"], "departamento_id": "nao-existe"}
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_criar_com_departamento_inativo_retorna_400(fake_repos):
    depto = await _depto(fake_repos)
    await fake_repos.departamentos.update(depto["id"], {"ativo": False})
    await fake_repos.clientes.create({"nome": "C", "documento": "1"})
    cliente = (await fake_repos.clientes.list_all())[0]
    with pytest.raises(HTTPException) as exc:
        await ChatService(fake_repos).criar(
            {"cliente_id": cliente["id"], "departamento_id": depto["id"]}
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_pegar_preserva_departamento_e_limpa_setor_legado(fake_repos):
    depto = await _depto(fake_repos)
    chat = await fake_repos.chats.create(
        {
            "cliente_id": "c1",
            "status": "NOVO",
            "departamento_id": depto["id"],
            "setor_alvo": "atendimento",
        }
    )
    atualizado = await ChatService(fake_repos).pegar(chat["id"], "atendente-1")
    assert atualizado["departamento_id"] == depto["id"]
    assert atualizado["setor_alvo"] is None


@pytest.mark.asyncio
async def test_transferir_preserva_departamento(fake_repos):
    depto = await _depto(fake_repos)
    await fake_repos.atendentes.create(
        {"nome": "Destino", "email": "d@x.com", "ativo": True}
    )
    destino = (await fake_repos.atendentes.list_all())[0]
    chat = await fake_repos.chats.create(
        {"cliente_id": "c1", "status": "EM_ATENDIMENTO", "departamento_id": depto["id"]}
    )
    atualizado = await ChatService(fake_repos).transferir(
        chat["id"], destino["id"], {"id": "admin", "perfil": "admin"}
    )
    assert atualizado["departamento_id"] == depto["id"]
    assert atualizado["atendente_id"] == destino["id"]


@pytest.mark.asyncio
async def test_listar_devolve_departamento_id(fake_repos):
    depto = await _depto(fake_repos)
    await fake_repos.clientes.create({"nome": "C", "documento": "1"})
    cliente = (await fake_repos.clientes.list_all())[0]
    await fake_repos.chats.create(
        {"cliente_id": cliente["id"], "status": "NOVO", "departamento_id": depto["id"]}
    )
    chats, total = await ChatService(fake_repos).listar()
    assert total == 1
    assert chats[0]["departamento_id"] == depto["id"]
