"""Migracao de setor/setor_alvo legado para departamento_id (spec 02)."""

import pytest

from app.services.departamento_seed import semear
from app.services.migracao_setor_service import mapa_legado, migrar


@pytest.mark.asyncio
async def test_migra_atendentes_e_chats_preservando_legado(fake_repos):
    await semear(fake_repos)
    atendente = await fake_repos.atendentes.create(
        {"nome": "A", "email": "a@x.com", "setor": "atendimento", "ativo": True}
    )
    chat = await fake_repos.chats.create(
        {"cliente_id": "c1", "status": "NOVO", "setor_alvo": "supervisao"}
    )

    relatorio = await migrar(fake_repos)

    atendente_db = await fake_repos.atendentes.get(atendente["id"])
    chat_db = await fake_repos.chats.get(chat["id"])
    assert atendente_db["departamento_id"] is not None
    assert chat_db["departamento_id"] is not None
    # C6: legado preservado
    assert atendente_db["setor"] == "atendimento"
    assert chat_db["setor_alvo"] == "supervisao"
    assert relatorio["orfaos"] == []
    assert relatorio["aplicado"] is True


@pytest.mark.asyncio
async def test_setor_desconhecido_vira_orfao_e_nao_recebe_departamento(fake_repos):
    await semear(fake_repos)
    atendente = await fake_repos.atendentes.create(
        {"nome": "A", "email": "a@x.com", "setor": "setor_inexistente", "ativo": True}
    )

    relatorio = await migrar(fake_repos)

    assert (await fake_repos.atendentes.get(atendente["id"]))["departamento_id"] is None
    assert relatorio["orfaos"] == [
        {"id": atendente["id"], "origem": "atendentes", "valor": "setor_inexistente"}
    ]


@pytest.mark.asyncio
async def test_dry_run_nao_escreve(fake_repos):
    await semear(fake_repos)
    atendente = await fake_repos.atendentes.create(
        {"nome": "A", "email": "a@x.com", "setor": "atendimento", "ativo": True}
    )

    relatorio = await migrar(fake_repos, aplicar=False)

    assert (await fake_repos.atendentes.get(atendente["id"]))["departamento_id"] is None
    assert relatorio["aplicado"] is False
    assert len(relatorio["atendentes"]) == 1


@pytest.mark.asyncio
async def test_migracao_e_idempotente(fake_repos):
    await semear(fake_repos)
    await fake_repos.atendentes.create(
        {"nome": "A", "email": "a@x.com", "setor": "atendimento", "ativo": True}
    )
    await migrar(fake_repos)
    segundo = await migrar(fake_repos)
    assert segundo["atendentes"] == []
    assert segundo["chats"] == []


def test_mapa_legado_cobre_os_setores_do_frontend():
    assert mapa_legado() == {
        "atendimento": "suporte_tecnico",
        "supervisao": "atendimento_geral",
        "programadores": "suporte_tecnico",
    }
