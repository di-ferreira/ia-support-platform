"""Contrato HTTP dos endpoints de departamento."""

import pytest


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_admin_cria_e_lista_departamento(client, admin_token):
    resp = await client.post(
        "/departamentos",
        json={"codigo": "suporte_tecnico", "nome": "Suporte Técnico"},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 201
    corpo = resp.json()
    assert corpo["codigo"] == "suporte_tecnico"
    assert corpo["ativo"] is True

    lista = await client.get("/departamentos", headers=_auth(admin_token))
    assert lista.status_code == 200
    assert [d["codigo"] for d in lista.json()] == ["suporte_tecnico"]


@pytest.mark.asyncio
async def test_atendente_pode_listar_mas_nao_criar(client, atendente_token):
    lista = await client.get("/departamentos", headers=_auth(atendente_token))
    assert lista.status_code == 200

    resp = await client.post(
        "/departamentos",
        json={"codigo": "x", "nome": "X"},
        headers=_auth(atendente_token),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_listar_inativos_exige_admin_ou_supervisor(client, atendente_token):
    resp = await client.get(
        "/departamentos?incluir_inativos=true", headers=_auth(atendente_token)
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_codigo_duplicado_retorna_409(client, admin_token):
    await client.post(
        "/departamentos",
        json={"codigo": "financeiro", "nome": "Financeiro"},
        headers=_auth(admin_token),
    )
    resp = await client.post(
        "/departamentos",
        json={"codigo": "financeiro", "nome": "Financeiro 2"},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_detalhe_inexistente_retorna_404(client, admin_token):
    resp = await client.get("/departamentos/nao-existe", headers=_auth(admin_token))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_atualiza_nome(client, admin_token):
    criado = await client.post(
        "/departamentos",
        json={"codigo": "comercial", "nome": "Comercial"},
        headers=_auth(admin_token),
    )
    depto_id = criado.json()["id"]
    resp = await client.patch(
        f"/departamentos/{depto_id}",
        json={"nome": "Comercial e Novos Negócios"},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["nome"] == "Comercial e Novos Negócios"


@pytest.mark.asyncio
async def test_delete_desativa(client, admin_token):
    criado = await client.post(
        "/departamentos",
        json={"codigo": "administrativo", "nome": "Administrativo"},
        headers=_auth(admin_token),
    )
    depto_id = criado.json()["id"]
    resp = await client.delete(f"/departamentos/{depto_id}", headers=_auth(admin_token))
    assert resp.status_code == 200
    assert resp.json()["ativo"] is False


@pytest.mark.asyncio
async def test_atendentes_do_departamento(client, admin_token, fake_repos):
    criado = await client.post(
        "/departamentos",
        json={"codigo": "implantacao", "nome": "Implantação"},
        headers=_auth(admin_token),
    )
    depto_id = criado.json()["id"]
    await fake_repos.atendentes.create(
        {
            "nome": "Implantador",
            "email": "imp@test.com",
            "departamento_id": depto_id,
            "ativo": True,
        }
    )
    resp = await client.get(
        f"/departamentos/{depto_id}/atendentes", headers=_auth(admin_token)
    )
    assert resp.status_code == 200
    assert [a["nome"] for a in resp.json()] == ["Implantador"]
