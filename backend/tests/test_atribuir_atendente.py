"""Atribuicao de atendente: escopo, compatibilidade e conflito 409."""

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
        {"cliente_id": cliente["id"], "status": "NOVO",
         "departamento_id": suporte["id"]}
    )
    return suporte, financeiro, chat


async def _atendente(fake_repos, email, departamento_id=None, ativo=True):
    return await fake_repos.atendentes.create(
        {"nome": email, "email": email, "departamento_id": departamento_id, "ativo": ativo}
    )


@pytest.mark.asyncio
async def test_admin_atribui_atendente_do_departamento(client, admin_token, fake_repos):
    suporte, _, chat = await _cenario(fake_repos)
    atendente = await _atendente(fake_repos, "a@x.com", suporte["id"])

    resp = await client.patch(
        f"/chats/{chat['id']}/atribuir-atendente",
        json={"atendente_id": atendente["id"], "motivo": "assumiu"},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["atendente_id"] == atendente["id"]
    assert corpo["departamento_id"] == suporte["id"]
    assert corpo["status"] == "EM_ATENDIMENTO"


@pytest.mark.asyncio
async def test_conflito_de_assuncao_retorna_409(client, admin_token, fake_repos):
    suporte, _, chat = await _cenario(fake_repos)
    primeiro = await _atendente(fake_repos, "a@x.com", suporte["id"])
    segundo = await _atendente(fake_repos, "b@x.com", suporte["id"])
    await fake_repos.chats.update(chat["id"], {"atendente_id": primeiro["id"]})

    resp = await client.patch(
        f"/chats/{chat['id']}/atribuir-atendente",
        json={"atendente_id": segundo["id"]},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_atendente_de_outro_departamento_retorna_400(
    client, atendente_token, fake_repos
):
    # Ajuste minimo do plano: admin sem motivo recebe 422 (override incompleto,
    # idem teste abaixo); o 400 cobre atendente sem poder de override tentando
    # assumir chat de outro departamento.
    _, financeiro, chat = await _cenario(fake_repos)
    proprio = await fake_repos.atendentes.get_by_email("atendente@test.com")
    await fake_repos.atendentes.update(
        proprio["id"], {"departamento_id": financeiro["id"]}
    )

    resp = await client.patch(
        f"/chats/{chat['id']}/atribuir-atendente",
        json={"atendente_id": proprio["id"]},
        headers=_auth(atendente_token),
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_override_de_admin_com_motivo_e_aceito(
    client, admin_token, fake_repos
):
    _, financeiro, chat = await _cenario(fake_repos)
    atendente = await _atendente(fake_repos, "fin@x.com", financeiro["id"])

    resp = await client.patch(
        f"/chats/{chat['id']}/atribuir-atendente",
        json={"atendente_id": atendente["id"], "motivo": "reforço temporário"},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_override_sem_motivo_retorna_422(client, admin_token, fake_repos):
    _, financeiro, chat = await _cenario(fake_repos)
    atendente = await _atendente(fake_repos, "fin@x.com", financeiro["id"])

    resp = await client.patch(
        f"/chats/{chat['id']}/atribuir-atendente",
        json={"atendente_id": atendente["id"]},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_atendente_inativo_retorna_400(client, admin_token, fake_repos):
    suporte, _, chat = await _cenario(fake_repos)
    atendente = await _atendente(fake_repos, "off@x.com", suporte["id"], ativo=False)

    resp = await client.patch(
        f"/chats/{chat['id']}/atribuir-atendente",
        json={"atendente_id": atendente["id"]},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_autoatribuicao_do_proprio_atendente(client, atendente_token, fake_repos):
    suporte, _, chat = await _cenario(fake_repos)
    atendente = await fake_repos.atendentes.get_by_email("atendente@test.com")
    await fake_repos.atendentes.update(
        atendente["id"], {"departamento_id": suporte["id"]}
    )

    resp = await client.patch(
        f"/chats/{chat['id']}/atribuir-atendente",
        json={"atendente_id": atendente["id"], "motivo": "assumindo"},
        headers=_auth(atendente_token),
    )
    assert resp.status_code == 200
    assert resp.json()["atendente_id"] == atendente["id"]


@pytest.mark.asyncio
async def test_atendente_nao_atribui_para_outra_pessoa(
    client, atendente_token, fake_repos
):
    suporte, _, chat = await _cenario(fake_repos)
    outro = await _atendente(fake_repos, "outro@x.com", suporte["id"])

    resp = await client.patch(
        f"/chats/{chat['id']}/atribuir-atendente",
        json={"atendente_id": outro["id"]},
        headers=_auth(atendente_token),
    )
    assert resp.status_code == 403
