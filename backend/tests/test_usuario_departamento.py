"""Associação de departamento no formulário de usuário (spec 07, 07-9)."""

import pytest


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _departamento(fake_repos, codigo: str, ativo: bool = True) -> dict:
    return await fake_repos.departamentos.create(
        {
            "codigo": codigo,
            "nome": codigo.title(),
            "ativo": ativo,
            "recebe_transferencias": True,
        }
    )


@pytest.mark.asyncio
async def test_cria_usuario_com_departamento_e_lista(client, admin_token, fake_repos):
    suporte = await _departamento(fake_repos, "suporte_tecnico")

    resp = await client.post(
        "/auth/usuarios",
        json={
            "nome": "Ana",
            "email": "ana@test.com",
            "senha": "segredo",
            "perfil": "atendente",
            "departamento_id": suporte["id"],
        },
        headers=_auth(admin_token),
    )
    assert resp.status_code == 201
    criado = resp.json()
    assert criado["departamento_id"] == suporte["id"]

    lista = await client.get("/auth/usuarios", headers=_auth(admin_token))
    assert lista.status_code == 200
    assert any(
        u["id"] == criado["id"] and u["departamento_id"] == suporte["id"]
        for u in lista.json()
    )


@pytest.mark.asyncio
async def test_atualiza_e_limpa_departamento_do_usuario(client, admin_token, fake_repos):
    suporte = await _departamento(fake_repos, "suporte_tecnico")
    financeiro = await _departamento(fake_repos, "financeiro")
    alvo = await fake_repos.atendentes.create(
        {
            "nome": "Bia",
            "email": "bia@test.com",
            "hash_senha": "x",
            "perfil": "atendente",
            "departamento_id": suporte["id"],
        }
    )

    resp = await client.patch(
        f"/auth/usuarios/{alvo['id']}",
        json={"departamento_id": financeiro["id"]},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["departamento_id"] == financeiro["id"]

    resp = await client.patch(
        f"/auth/usuarios/{alvo['id']}",
        json={"departamento_id": None},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["departamento_id"] is None


@pytest.mark.asyncio
async def test_departamento_inativo_nao_aceita_associacao(client, admin_token, fake_repos):
    inativo = await _departamento(fake_repos, "antigo", ativo=False)

    resp = await client.post(
        "/auth/usuarios",
        json={
            "nome": "Caio",
            "email": "caio@test.com",
            "senha": "segredo",
            "perfil": "atendente",
            "departamento_id": inativo["id"],
        },
        headers=_auth(admin_token),
    )
    assert resp.status_code == 400
    assert "inativo" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_departamento_inexistente_retorna_404(client, admin_token):
    resp = await client.post(
        "/auth/usuarios",
        json={
            "nome": "Duda",
            "email": "duda@test.com",
            "senha": "segredo",
            "perfil": "atendente",
            "departamento_id": "nao-existe",
        },
        headers=_auth(admin_token),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_atendentes_ativos_expoem_departamento(client, atendente_token, fake_repos):
    financeiro = await _departamento(fake_repos, "financeiro")
    # O escopo de /ativos é por departamento (spec 04, regra 6): o atendente
    # precisa estar no mesmo departamento para ver a Eva.
    atendente = await fake_repos.atendentes.get_by_email("atendente@test.com")
    await fake_repos.atendentes.update(
        atendente["id"], {"departamento_id": financeiro["id"]}
    )
    await fake_repos.atendentes.create(
        {
            "nome": "Eva",
            "email": "eva@test.com",
            "hash_senha": "x",
            "perfil": "atendente",
            "ativo": True,
            "departamento_id": financeiro["id"],
        }
    )

    resp = await client.get("/atendentes/ativos", headers=_auth(atendente_token))
    assert resp.status_code == 200
    assert any(a["departamento_id"] == financeiro["id"] for a in resp.json())
