"""Regras de negocio de departamento: unicidade, desativacao e ordenacao."""

import pytest
from fastapi import HTTPException

from app.services.departamento_service import DepartamentoService


@pytest.mark.asyncio
async def test_criar_normaliza_codigo_minusculo(fake_repos):
    service = DepartamentoService(fake_repos)
    doc = await service.criar({"codigo": "Suporte_Tecnico", "nome": "Suporte Técnico"})
    assert doc["codigo"] == "suporte_tecnico"
    assert doc["ativo"] is True


@pytest.mark.asyncio
async def test_criar_codigo_duplicado_retorna_409(fake_repos):
    service = DepartamentoService(fake_repos)
    await service.criar({"codigo": "financeiro", "nome": "Financeiro"})
    with pytest.raises(HTTPException) as exc:
        await service.criar({"codigo": "financeiro", "nome": "Outro nome"})
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_obter_inexistente_retorna_404(fake_repos):
    service = DepartamentoService(fake_repos)
    with pytest.raises(HTTPException) as exc:
        await service.obter("nao-existe")
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_listar_ordena_por_ordem_e_nome(fake_repos):
    service = DepartamentoService(fake_repos)
    await service.criar({"codigo": "b", "nome": "Beta", "ordem": 2})
    await service.criar({"codigo": "a", "nome": "Alfa", "ordem": 1})
    await service.criar({"codigo": "c", "nome": "Gama", "ordem": None})
    codigos = [d["codigo"] for d in await service.listar()]
    assert codigos == ["a", "b", "c"]


@pytest.mark.asyncio
async def test_listar_sem_inativos_por_padrao(fake_repos):
    service = DepartamentoService(fake_repos)
    a = await service.criar({"codigo": "a", "nome": "Alfa"})
    await service.atualizar(a["id"], {"ativo": False})
    assert await service.listar() == []
    assert len(await service.listar(incluir_inativos=True)) == 1


@pytest.mark.asyncio
async def test_desativar_bloqueia_quando_ha_regra_vinculada(fake_repos):
    service = DepartamentoService(fake_repos)
    depto = await service.criar({"codigo": "fiscal", "nome": "Fiscal"})
    await fake_repos.regras_roteamento.create(
        {
            "intencao": "problema_tecnico",
            "departamento_id": depto["id"],
            "prioridade_regra": 10,
            "ativo": True,
        }
    )
    with pytest.raises(HTTPException) as exc:
        await service.desativar(depto["id"])
    assert exc.value.status_code == 409
    assert "regras_roteamento" in exc.value.detail


@pytest.mark.asyncio
async def test_desativar_sem_vinculos_marca_inativo(fake_repos):
    service = DepartamentoService(fake_repos)
    depto = await service.criar({"codigo": "comercial", "nome": "Comercial"})
    atualizado = await service.desativar(depto["id"])
    assert atualizado["ativo"] is False


@pytest.mark.asyncio
async def test_listar_atendentes_so_ativos_do_departamento(fake_repos):
    service = DepartamentoService(fake_repos)
    depto = await service.criar({"codigo": "financeiro", "nome": "Financeiro"})
    await fake_repos.atendentes.create(
        {"nome": "A1", "email": "a1@x.com", "departamento_id": depto["id"], "ativo": True}
    )
    await fake_repos.atendentes.create(
        {"nome": "A2", "email": "a2@x.com", "departamento_id": depto["id"], "ativo": False}
    )
    await fake_repos.atendentes.create(
        {"nome": "A3", "email": "a3@x.com", "departamento_id": "outro", "ativo": True}
    )
    atendentes = await service.listar_atendentes(depto["id"])
    assert [a["nome"] for a in atendentes] == ["A1"]


@pytest.mark.asyncio
async def test_codigo_nao_pode_ser_alterado(fake_repos):
    """Codigo e slug estavel: a atualizacao ignora a chave se enviada."""
    service = DepartamentoService(fake_repos)
    depto = await service.criar({"codigo": "suporte_tecnico", "nome": "Suporte"})
    atualizado = await service.atualizar(
        depto["id"], {"codigo": "renomeado", "nome": "Suporte Técnico"}
    )
    assert atualizado["codigo"] == "suporte_tecnico"
    assert atualizado["nome"] == "Suporte Técnico"
