"""Resolucao deterministica de regras de roteamento (spec 10)."""

import pytest

from app.schemas.ai import ClassificacaoIntencao
from app.services.departamento_seed import semear
from app.services.routing_service import RoutingService


def _classificacao(**kwargs) -> ClassificacaoIntencao:
    base = {
        "intencao": "problema_tecnico",
        "categoria_erp": "fiscal",
        "subintencao": "emissao_nfe",
        "confianca": 0.95,
    }
    return ClassificacaoIntencao.model_validate({**base, **kwargs})


async def _depto(fake_repos, codigo):
    return await fake_repos.departamentos.get_by_codigo(codigo)


@pytest.mark.asyncio
async def test_regra_especifica_vence_generica(fake_repos):
    await semear(fake_repos)
    suporte = await _depto(fake_repos, "suporte_tecnico")
    financeiro = await _depto(fake_repos, "financeiro")
    # generica: problema_tecnico -> financeiro (prioridade 1)
    await fake_repos.regras_roteamento.create(
        {"intencao": "problema_tecnico", "departamento_id": financeiro["id"],
         "prioridade_regra": 1, "ativo": True}
    )
    # especifica: problema_tecnico + fiscal -> suporte (prioridade 99)
    await fake_repos.regras_roteamento.create(
        {"intencao": "problema_tecnico", "categoria_erp": "fiscal",
         "departamento_id": suporte["id"], "prioridade_regra": 99, "ativo": True}
    )
    r = await RoutingService(fake_repos).resolver(_classificacao())
    assert r.departamento_codigo == "suporte_tecnico"
    assert r.origem == "regra"


@pytest.mark.asyncio
async def test_prioridade_desempata_mesma_especificidade(fake_repos):
    await semear(fake_repos)
    suporte = await _depto(fake_repos, "suporte_tecnico")
    financeiro = await _depto(fake_repos, "financeiro")
    await fake_repos.regras_roteamento.create(
        {"intencao": "problema_tecnico", "departamento_id": suporte["id"],
         "prioridade_regra": 20, "ativo": True}
    )
    await fake_repos.regras_roteamento.create(
        {"intencao": "problema_tecnico", "departamento_id": financeiro["id"],
         "prioridade_regra": 10, "ativo": True}
    )
    sem_detalhe = _classificacao(categoria_erp=None, subintencao=None)
    r = await RoutingService(fake_repos).resolver(sem_detalhe)
    assert r.departamento_codigo == "financeiro"


@pytest.mark.asyncio
async def test_empate_com_destinos_diferentes_vira_conflito_e_fallback(fake_repos):
    await semear(fake_repos)
    suporte = await _depto(fake_repos, "suporte_tecnico")
    financeiro = await _depto(fake_repos, "financeiro")
    for depto in (suporte, financeiro):
        await fake_repos.regras_roteamento.create(
            {"intencao": "problema_tecnico", "departamento_id": depto["id"],
             "prioridade_regra": 10, "ativo": True}
        )
    sem_detalhe = _classificacao(categoria_erp=None, subintencao=None)
    r = await RoutingService(fake_repos).resolver(sem_detalhe)
    assert r.conflito is True
    assert r.origem == "conflito"
    assert r.departamento_codigo == "atendimento_geral"


@pytest.mark.asyncio
async def test_sem_regra_cai_no_fallback(fake_repos):
    await semear(fake_repos)
    r = await RoutingService(fake_repos).resolver(
        _classificacao(intencao="solicitacao_administrativa")
    )
    assert r.origem == "fallback"
    assert r.departamento_codigo == "atendimento_geral"


@pytest.mark.asyncio
async def test_destino_inativo_nao_e_aceito(fake_repos):
    await semear(fake_repos)
    financeiro = await _depto(fake_repos, "financeiro")
    await fake_repos.departamentos.update(financeiro["id"], {"ativo": False})
    await fake_repos.regras_roteamento.create(
        {"intencao": "problema_tecnico", "departamento_id": financeiro["id"],
         "prioridade_regra": 1, "ativo": True}
    )
    sem_detalhe = _classificacao(categoria_erp=None, subintencao=None)
    r = await RoutingService(fake_repos).resolver(sem_detalhe)
    assert r.departamento_codigo == "atendimento_geral"


@pytest.mark.asyncio
async def test_destino_sem_recebe_transferencias_nao_e_aceito(fake_repos):
    await semear(fake_repos)
    financeiro = await _depto(fake_repos, "financeiro")
    await fake_repos.departamentos.update(
        financeiro["id"], {"recebe_transferencias": False}
    )
    await fake_repos.regras_roteamento.create(
        {"intencao": "problema_tecnico", "departamento_id": financeiro["id"],
         "prioridade_regra": 1, "ativo": True}
    )
    sem_detalhe = _classificacao(categoria_erp=None, subintencao=None)
    r = await RoutingService(fake_repos).resolver(sem_detalhe)
    assert r.departamento_codigo == "atendimento_geral"


@pytest.mark.asyncio
async def test_baixa_confianca_pede_esclarecimento(fake_repos):
    await semear(fake_repos)
    r = await RoutingService(fake_repos).resolver(_classificacao(confianca=0.4))
    assert r.precisa_esclarecimento is True
    assert r.origem == "esclarecimento"
    assert r.departamento_id is None


@pytest.mark.asyncio
async def test_limite_de_tentativas_leva_ao_fallback(fake_repos):
    await semear(fake_repos)
    r = await RoutingService(fake_repos).resolver(
        _classificacao(confianca=0.4), tentativas_esclarecimento=2
    )
    assert r.precisa_esclarecimento is False
    assert r.departamento_codigo == "atendimento_geral"


@pytest.mark.asyncio
async def test_pedido_explicito_tem_precedencia(fake_repos):
    await semear(fake_repos)
    comercial = await _depto(fake_repos, "comercial")
    r = await RoutingService(fake_repos).resolver(
        _classificacao(confianca=0.1), departamento_explicito_id=comercial["id"]
    )
    assert r.origem == "pedido_explicito"
    assert r.departamento_codigo == "comercial"


@pytest.mark.asyncio
async def test_pedido_explicito_inativo_e_ignorado(fake_repos):
    await semear(fake_repos)
    comercial = await _depto(fake_repos, "comercial")
    await fake_repos.departamentos.update(comercial["id"], {"ativo": False})
    r = await RoutingService(fake_repos).resolver(
        _classificacao(confianca=0.1), departamento_explicito_id=comercial["id"]
    )
    assert r.origem != "pedido_explicito"


@pytest.mark.asyncio
async def test_pedido_de_humano_mantem_departamento_do_contexto(fake_repos):
    await semear(fake_repos)
    suporte = await _depto(fake_repos, "suporte_tecnico")
    r = await RoutingService(fake_repos).resolver(
        _classificacao(intencao="solicitacao_humano", categoria_erp=None, confianca=0.99),
        departamento_atual_id=suporte["id"],
    )
    assert r.origem == "contexto"
    assert r.departamento_codigo == "suporte_tecnico"


@pytest.mark.asyncio
async def test_fallback_indisponivel_pede_esclarecimento(fake_repos):
    r = await RoutingService(fake_repos).resolver(_classificacao())
    assert r.precisa_esclarecimento is True
    assert r.departamento_id is None
    assert r.conflito is True
