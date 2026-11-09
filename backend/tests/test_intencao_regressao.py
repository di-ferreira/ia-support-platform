"""Regressao de intencao e roteamento contra o dataset rotulado."""

import pytest

from app.models.departamento import CategoriaERP, Intencao
from app.schemas.ai import ClassificacaoIntencao
from app.services.departamento_seed import semear
from app.services.routing_service import RoutingService
from tests.data.intencao_rotulada import CASOS_ROTULADOS, REGRAS_ROTULADAS


async def _preparar(fake_repos):
    await semear(fake_repos)
    for regra in REGRAS_ROTULADAS:
        depto = await fake_repos.departamentos.get_by_codigo(regra["departamento"])
        await fake_repos.regras_roteamento.create(
            {
                "intencao": regra["intencao"],
                "subintencao": regra.get("subintencao"),
                "categoria_erp": regra.get("categoria_erp"),
                "departamento_id": depto["id"],
                "prioridade_regra": regra["prioridade_regra"],
                "ativo": True,
            }
        )


def _classificacao(caso) -> ClassificacaoIntencao:
    return ClassificacaoIntencao(
        intencao=Intencao(caso["intencao"]),
        subintencao=caso.get("subintencao"),
        categoria_erp=CategoriaERP(caso["categoria_erp"]) if caso.get("categoria_erp") else None,
        confianca=caso["confianca"],
        precisa_esclarecimento=caso.get("precisa_esclarecimento", False),
        pergunta_esclarecimento="Qual área?" if caso.get("precisa_esclarecimento") else None,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "caso", CASOS_ROTULADOS, ids=[c["texto"][:32] for c in CASOS_ROTULADOS]
)
async def test_roteamento_do_dataset(fake_repos, caso):
    await _preparar(fake_repos)
    resultado = await RoutingService(fake_repos).resolver(_classificacao(caso))
    if caso["departamento_esperado"] is None:
        assert resultado.precisa_esclarecimento is True
        assert resultado.departamento_id is None
    else:
        assert resultado.departamento_codigo == caso["departamento_esperado"]
        assert resultado.conflito is False


@pytest.mark.asyncio
async def test_nenhum_departamento_e_escolhido_por_texto_livre(fake_repos):
    """Regra 2 da spec 10: o LLM sugere, mas o destino vem da regra."""
    await semear(fake_repos)
    caso = {
        "intencao": "problema_tecnico",
        "categoria_erp": None,
        "confianca": 0.99,
        "departamento_esperado": "atendimento_geral",
    }
    resultado = await RoutingService(fake_repos).resolver(_classificacao(caso))
    assert resultado.departamento_codigo == "atendimento_geral"
    assert resultado.origem == "fallback"
