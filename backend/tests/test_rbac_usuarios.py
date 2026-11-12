"""Regras de RBAC de usuários (spec 04, itens 04-4 e 04-5)."""

import pytest


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
@pytest.mark.parametrize("perfil", ["admin", "supervisor"])
async def test_supervisor_nao_cria_usuario_com_outro_perfil(
    client, supervisor_token, perfil
):
    resp = await client.post(
        "/auth/usuarios",
        json={
            "nome": "Novo",
            "email": f"novo-{perfil}@test.com",
            "senha": "segredo",
            "perfil": perfil,
        },
        headers=_auth(supervisor_token),
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Supervisor só pode criar usuários com perfil 'atendente'"


@pytest.mark.asyncio
async def test_supervisor_cria_usuario_atendente(client, supervisor_token):
    resp = await client.post(
        "/auth/usuarios",
        json={
            "nome": "Novo Atendente",
            "email": "novo-atendente@test.com",
            "senha": "segredo",
            "perfil": "atendente",
        },
        headers=_auth(supervisor_token),
    )
    assert resp.status_code == 201
    assert resp.json()["perfil"] == "atendente"


@pytest.mark.asyncio
async def test_supervisor_nao_altera_perfil(client, supervisor_token, fake_repos):
    alvo = await fake_repos.atendentes.create(
        {
            "nome": "Alvo",
            "email": "alvo@test.com",
            "hash_senha": "x",
            "perfil": "atendente",
        }
    )

    resp = await client.patch(
        f"/auth/usuarios/{alvo['id']}",
        json={"perfil": "admin"},
        headers=_auth(supervisor_token),
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Apenas admin pode alterar perfil de usuário"
    assert (await fake_repos.atendentes.get(alvo["id"]))["perfil"] == "atendente"


@pytest.mark.asyncio
async def test_admin_altera_perfil(client, admin_token, fake_repos):
    alvo = await fake_repos.atendentes.create(
        {
            "nome": "Alvo",
            "email": "alvo@test.com",
            "hash_senha": "x",
            "perfil": "atendente",
        }
    )

    resp = await client.patch(
        f"/auth/usuarios/{alvo['id']}",
        json={"perfil": "supervisor"},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["perfil"] == "supervisor"
    assert (await fake_repos.atendentes.get(alvo["id"]))["perfil"] == "supervisor"


@pytest.mark.asyncio
async def test_supervisor_altera_outros_campos_sem_perfil(client, supervisor_token, fake_repos):
    alvo = await fake_repos.atendentes.create(
        {
            "nome": "Alvo",
            "email": "alvo@test.com",
            "hash_senha": "x",
            "perfil": "atendente",
            "ativo": True,
        }
    )

    resp = await client.patch(
        f"/auth/usuarios/{alvo['id']}",
        json={"nome": "Alvo Renomeado", "ativo": False},
        headers=_auth(supervisor_token),
    )
    assert resp.status_code == 200
    atualizado = await fake_repos.atendentes.get(alvo["id"])
    assert atualizado["nome"] == "Alvo Renomeado"
    assert atualizado["ativo"] is False
    assert atualizado["perfil"] == "atendente"
