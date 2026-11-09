"""Seed idempotente dos departamentos iniciais (spec 10)."""

import pytest

from app.services.departamento_seed import DEPARTAMENTOS_SEED, semear


@pytest.mark.asyncio
async def test_seed_cria_os_seis_departamentos(fake_repos):
    relatorio = await semear(fake_repos)
    assert relatorio == {"criados": 6, "atualizados": 0, "ignorados": 0}
    codigos = {d["codigo"] for d in await fake_repos.departamentos.list_all()}
    assert codigos == {
        "suporte_tecnico",
        "financeiro",
        "comercial",
        "administrativo",
        "implantacao",
        "atendimento_geral",
    }


@pytest.mark.asyncio
async def test_seed_e_idempotente(fake_repos):
    await semear(fake_repos)
    relatorio = await semear(fake_repos)
    assert relatorio["criados"] == 0
    assert relatorio["ignorados"] == 6
    assert len(await fake_repos.departamentos.list_all()) == 6


@pytest.mark.asyncio
async def test_seed_nao_reativa_departamento_desativado(fake_repos):
    await semear(fake_repos)
    depto = await fake_repos.departamentos.get_by_codigo("comercial")
    await fake_repos.departamentos.update(depto["id"], {"ativo": False})
    await semear(fake_repos)
    assert (await fake_repos.departamentos.get_by_codigo("comercial"))["ativo"] is False


@pytest.mark.asyncio
async def test_seed_atualiza_nome_quando_diferente(fake_repos):
    await fake_repos.departamentos.create(
        {"codigo": "financeiro", "nome": "Fin.", "ativo": True, "ordem": 1}
    )
    relatorio = await semear(fake_repos)
    assert relatorio["atualizados"] == 1
    assert (await fake_repos.departamentos.get_by_codigo("financeiro"))["nome"] == "Financeiro"


def test_atendimento_geral_existe_como_fallback():
    codigos = [d["codigo"] for d in DEPARTAMENTOS_SEED]
    assert "atendimento_geral" in codigos
