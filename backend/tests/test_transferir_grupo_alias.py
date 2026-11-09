"""transferir-grupo aceita departamento_id; 'setor' fica so por compatibilidade."""

import pytest
from pydantic import ValidationError

from app.schemas.chat import ChatTransferirGrupo


def test_aceita_departamento_id():
    body = ChatTransferirGrupo(departamento_id="d1")
    assert body.departamento_id == "d1"


def test_aceita_setor_legado():
    body = ChatTransferirGrupo(setor="financeiro")
    assert body.setor == "financeiro"


def test_rejeita_os_dois():
    with pytest.raises(ValidationError):
        ChatTransferirGrupo(departamento_id="d1", setor="financeiro")


def test_rejeita_nenhum():
    with pytest.raises(ValidationError):
        ChatTransferirGrupo()


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_transfere_por_id_e_responde_departamento(
    client, admin_token, fake_repos
):
    await fake_repos.departamentos.create(
        {"codigo": "financeiro", "nome": "Financeiro", "ativo": True,
         "recebe_transferencias": True}
    )
    financeiro = await fake_repos.departamentos.get_by_codigo("financeiro")
    await fake_repos.clientes.create({"nome": "C", "documento": "1"})
    cliente = (await fake_repos.clientes.list_all())[0]
    chat = await fake_repos.chats.create(
        {"cliente_id": cliente["id"], "status": "EM_ATENDIMENTO",
         "atendente_id": "a1"}
    )

    resp = await client.patch(
        f"/chats/{chat['id']}/transferir-grupo",
        json={"departamento_id": financeiro["id"]},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["departamento_id"] == financeiro["id"]
    assert corpo["atendente_id"] is None


@pytest.mark.asyncio
async def test_setor_legado_continua_funcionando(client, admin_token, fake_repos):
    await fake_repos.departamentos.create(
        {"codigo": "financeiro", "nome": "Financeiro", "ativo": True,
         "recebe_transferencias": True}
    )
    await fake_repos.clientes.create({"nome": "C", "documento": "1"})
    cliente = (await fake_repos.clientes.list_all())[0]
    chat = await fake_repos.chats.create(
        {"cliente_id": cliente["id"], "status": "NOVO"}
    )

    resp = await client.patch(
        f"/chats/{chat['id']}/transferir-grupo",
        json={"setor": "financeiro"},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["departamento_id"] is not None


@pytest.mark.asyncio
async def test_setor_desconhecido_retorna_400(client, admin_token, fake_repos):
    await fake_repos.clientes.create({"nome": "C", "documento": "1"})
    cliente = (await fake_repos.clientes.list_all())[0]
    chat = await fake_repos.chats.create(
        {"cliente_id": cliente["id"], "status": "NOVO"}
    )
    resp = await client.patch(
        f"/chats/{chat['id']}/transferir-grupo",
        json={"setor": "programadores_antigos"},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 400
