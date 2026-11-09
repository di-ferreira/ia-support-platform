"""Repositorios de departamento e regras de roteamento (fakes em memoria)."""

import pytest


@pytest.mark.asyncio
async def test_get_by_codigo(fake_repos):
    await fake_repos.departamentos.create(
        {"codigo": "financeiro", "nome": "Financeiro"}
    )
    doc = await fake_repos.departamentos.get_by_codigo("financeiro")
    assert doc is not None
    assert doc["nome"] == "Financeiro"


@pytest.mark.asyncio
async def test_get_by_codigo_inexistente_retorna_none(fake_repos):
    assert await fake_repos.departamentos.get_by_codigo("nao_existe") is None


@pytest.mark.asyncio
async def test_list_ativos_ignora_inativos(fake_repos):
    await fake_repos.departamentos.create(
        {"codigo": "ativo", "nome": "Ativo", "ativo": True}
    )
    await fake_repos.departamentos.create(
        {"codigo": "inativo", "nome": "Inativo", "ativo": False}
    )
    ativos = await fake_repos.departamentos.list_ativos()
    assert [d["codigo"] for d in ativos] == ["ativo"]


@pytest.mark.asyncio
async def test_list_ativas_ordenadas_por_prioridade(fake_repos):
    await fake_repos.regras_roteamento.create(
        {"intencao": "duvida_geral", "prioridade_regra": 50, "ativo": True}
    )
    await fake_repos.regras_roteamento.create(
        {"intencao": "problema_tecnico", "prioridade_regra": 10, "ativo": True}
    )
    await fake_repos.regras_roteamento.create(
        {"intencao": "solicitacao_humano", "prioridade_regra": 1, "ativo": False}
    )
    regras = await fake_repos.regras_roteamento.list_ativas_ordenadas()
    assert [r["intencao"] for r in regras] == ["problema_tecnico", "duvida_geral"]
